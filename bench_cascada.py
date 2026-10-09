"""Mide como escala el coste al encadenar 1, 5, 10 y 15 preguntas sobre el mismo caso.

Compara los tres modos a cada nivel. Lo interesante no es solo quien gana, sino
**la forma de la curva**: si el tiempo crece plano, lineal o peor.

    python bench_cascada.py
"""

import argparse
import json
import os
import random as rnd
import re
import statistics as st
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_multi as bm  # noqa: E402
import casos_cascada as cc  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096")
MODOS = ("tipado", "natural", "llm")


def _post(path, payload, timeout=300):
    req = urllib.request.Request(
        SERVIDOR.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")), (time.perf_counter() - t0) * 1000.0


def modo_llm_largo(estado, preguntas):
    """El mismo modo chat, pero con presupuesto de sobra para 15 respuestas.

    Con 512 tokens se cortaba a la mitad en el nivel de 15 preguntas, y un corte no
    es un fallo del modelo: es del arnes. Se sube a 2048 para no medir eso.
    """
    lineas = [f"Caso: {estado}", "", "Responde a estas preguntas:"]
    for pid, p, c, _ in preguntas:
        if isinstance(c, list):
            ops = ", ".join(f"{i}={n}" for i, n in enumerate(c))
            lineas.append(f"- {pid}: {p} (responde el número: {ops})")
        elif isinstance(c, dict) and set(c) <= {"true", "false"}:
            lineas.append(f"- {pid}: {p} (responde true o false)")
        else:
            lineas.append(f"- {pid}: {p} (responde una de: {', '.join(c)})")
    lineas.append("")
    lineas.append("Responde SOLO con una línea por pregunta, con el formato "
                  "id=respuesta. Sin explicaciones.")

    cuerpo, ms = _post("/v1/chat/completions",
                       {"messages": [{"role": "user", "content": "\n".join(lineas)}],
                        "temperature": 0,
                        "max_tokens": 2048,
                        "chat_template_kwargs": {"enable_thinking": False}})
    texto = (cuerpo["choices"][0]["message"].get("content") or "").strip()
    tokens = cuerpo.get("usage", {}).get("completion_tokens", 0)
    corte = cuerpo["choices"][0].get("finish_reason") == "length"

    salida = {}
    for pid, p, c, _ in preguntas:
        m = re.search(rf"^\s*{re.escape(pid)}\s*[=:]\s*(.+?)\s*$", texto,
                      re.MULTILINE | re.IGNORECASE)
        if not m:
            salida[pid] = None
            continue
        v = m.group(1).strip().strip('."\'`')
        if isinstance(c, list):
            mm = re.search(r"\b([0-9])\b", v)
            salida[pid] = float(mm.group(1)) if mm else None
        elif isinstance(c, dict) and set(c) <= {"true", "false"}:
            salida[pid] = bool(re.search(r"\b(true|sí|si|yes)\b", v.lower()))
        else:
            salida[pid] = next((k for k in c if k.lower() in v.lower()), None)
    return ({pid: {"value": salida[pid]} for pid, _, _, _ in preguntas},
            ms, tokens, corte)


FUNCIONES = {"tipado": bm.modo_tipado, "natural": bm.modo_natural,
             "llm": modo_llm_largo}


def _candado():
    """Deja medir a UNA sola instancia; las demas se retiran.

    En esta maquina el terminal lanza CADA comando DOS veces (dos procesos identicos
    en el mismo segundo). Si los dos miden a la vez, sus peticiones se encolan en el
    servidor y los tiempos de los dos salen contaminados: es lo que paso, dos corridas
    se pisaron el fichero de salida y dieron cifras distintas.

    El fichero se crea con O_EXCL, que es atomico en el sistema de ficheros: de los
    dos, exactamente uno lo consigue y el otro recibe FileExistsError.
    """
    ruta = os.path.join(AQUI, ".cascada.lock")
    try:
        fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return ruta
    except FileExistsError:
        try:                              # candado huerfano de una corrida que murio
            edad = time.time() - os.path.getmtime(ruta)
        except OSError:
            edad = 0
        if edad > 900:
            os.remove(ruta)
            return _candado()
        print(f"  ya hay otra instancia midiendo (PID en .cascada.lock); "
              f"esta se retira para no contaminar", flush=True)
        return None


def main():
    candado = _candado()
    if candado is None:
        return 0
    try:
        return _main()
    finally:
        try:
            os.remove(candado)
        except OSError:
            pass


def _main():
    ap = argparse.ArgumentParser(prog="bench_cascada")
    ap.add_argument("--reps", type=int, default=5,
                    help="repeticiones por nivel y modo; se publica la mediana")
    ap.add_argument("--out", default=os.path.join(AQUI, "results", "cascada.json"))
    a = ap.parse_args()

    registro = []
    for nombre_caso, estado, fondo in cc.CASOS:
        print(f"\n{nombre_caso}: {len(cc.NIVELES)} niveles x {a.reps} vueltas",
              flush=True)
        # Las vueltas van POR FUERA y los niveles POR DENTRO: midiendo cada nivel en
        # bloque, uno heredaba el estado del anterior y salia una diferencia falsa.
        # Medido asi, el nivel de 10 daba 126 ms y el de 15 daba 95 ms; alternandolos
        # en la misma tanda, los dos dan ~93 ms. El orden importaba mas que el nivel.
        tiempos = {(n, m): [] for n in cc.NIVELES for m in MODOS}
        cuentas = {(n, m): [] for n in cc.NIVELES for m in MODOS}
        tokens_v = {(n, m): [] for n in cc.NIVELES for m in MODOS}
        cortes = {(n, m): False for n in cc.NIVELES for m in MODOS}
        fallos = set()

        for m in MODOS:                       # calentamiento, una vez por modo
            try:
                FUNCIONES[m](estado, fondo[:1])
            except Exception:                                 # noqa: BLE001
                pass

        for vuelta in range(a.reps):
            for n in cc.NIVELES:
                preguntas = fondo[:n]
                # Orden de modos aleatorio en cada vuelta: con un orden fijo, el que va
                # primero paga siempre el arranque y el ultimo lo hereda.
                orden = list(MODOS)
                rnd.shuffle(orden)
                for modo in orden:
                    try:
                        # Calentamiento INMEDIATAMENTE antes de medir. Sin esto, los
                        # modos comparten prefijo de prompt y el que corre primero paga
                        # la lectura mientras los siguientes la reutilizan: medido asi,
                        # `tipado` daba 101→278 ms y `natural` 62→99 ms con el MISMO
                        # esquema, cuando deberian ser iguales.
                        FUNCIONES[modo](estado, preguntas)
                        r = FUNCIONES[modo](estado, preguntas)
                    except Exception as e:                    # noqa: BLE001
                        if modo not in fallos:
                            fallos.add(modo)
                            print(f"    ERROR {modo}: {type(e).__name__}: {e}")
                        continue
                    campos, ms, tokens = r[0], r[1], r[2]
                    if len(r) > 3 and r[3]:
                        cortes[(n, modo)] = True
                    tiempos[(n, modo)].append(ms)
                    tokens_v[(n, modo)].append(tokens)
                    cuentas[(n, modo)].append(sum(
                        1 for pid, p, c, esp in preguntas
                        if bm.comparar(esp, (campos.get(pid) or {}).get("value"))))
            print(f"    vuelta {vuelta + 1}/{a.reps}", end="\r", flush=True)

        for n in cc.NIVELES:
            for modo in MODOS:
                v = tiempos[(n, modo)]
                if not v:
                    continue
                registro.append({
                    "caso": nombre_caso, "n": n, "modo": modo, "reps": len(v),
                    "ms": round(st.median(v), 1),
                    "ms_min": round(min(v), 1), "ms_max": round(max(v), 1),
                    "tokens": st.median(tokens_v[(n, modo)]),
                    "corte": cortes[(n, modo)],
                    "ok": st.median(cuentas[(n, modo)]), "total": n,
                    "acierto": 100 * st.median(cuentas[(n, modo)]) / n,
                })
            linea = "  ".join(
                f"{m} {st.median(tiempos[(n, m)]):.0f}ms"
                if tiempos[(n, m)] else f"{m} -" for m in MODOS)
            print(f"    n={n:<3} {linea}")

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1)

    informe(registro)
    print(f"\ncrudo: {a.out}\n")


def informe(reg):
    print("\n" + "=" * 78)
    print("  ESCALADO EN CASCADA")
    print("=" * 78)

    print("\n  --- tiempo por caso (ms) ---")
    print(f"  {'preguntas':<11}" + "".join(f"{m:>11}" for m in MODOS)
          + f"{'decision/chat':>15}")
    for n in cc.NIVELES:
        fila = [r for r in reg if r["n"] == n]
        ms = {}
        for m in MODOS:
            s = [x["ms"] for x in fila if x["modo"] == m]
            ms[m] = st.mean(s) if s else 0
        ratio = f"{ms['llm'] / ms['tipado']:.1f}x" if ms.get("tipado") else "-"
        print(f"  {n:<11}" + "".join(f"{ms.get(m, 0):>11.0f}" for m in MODOS)
              + f"{ratio:>15}")

    print("\n  --- coste marginal de cada pregunta añadida (ms) ---")
    print(f"  {'tramo':<16}" + "".join(f"{m:>11}" for m in MODOS))
    base = {m: next((r["ms"] for r in reg if r["n"] == 1 and r["modo"] == m), 0)
            for m in MODOS}
    prev = {m: base[m] for m in MODOS}
    for n in cc.NIVELES[1:]:
        fila = []
        for m in MODOS:
            v = st.mean([r["ms"] for r in reg if r["n"] == n and r["modo"] == m])
            fila.append((v - prev[m]) / (n - (cc.NIVELES[cc.NIVELES.index(n) - 1])))
            prev[m] = v
        print(f"  1→{n:<13}" + "".join(f"{v:>11.1f}" for v in fila))

    print("\n  --- acierto (%) ---")
    print(f"  {'preguntas':<11}" + "".join(f"{m:>11}" for m in MODOS))
    for n in cc.NIVELES:
        fila = [r for r in reg if r["n"] == n]
        celdas = []
        for m in MODOS:
            s = [x["acierto"] for x in fila if x["modo"] == m]
            celdas.append(st.mean(s) if s else 0)
        print(f"  {n:<11}" + "".join(f"{v:>10.1f}%" for v in celdas))

    print("\n  --- respuestas ilegibles (de 2 casos x N) ---")
    for n in cc.NIVELES:
        s = [r for r in reg if r["n"] == n and r["modo"] == "llm"]
        perdidas = sum(r["total"] - r["ok"] for r in s)
        cortes = sum(1 for r in s if r["corte"])
        print(f"  {n:<11} llm: {perdidas:>3} respuestas sin leer"
              f"   ({cortes} peticion(es) cortada(s) por longitud)")

    print("\n  --- tokens generados por el modo chat ---")
    for n in cc.NIVELES:
        s = [r["tokens"] for r in reg if r["n"] == n and r["modo"] == "llm"]
        print(f"  {n:<11} {st.mean(s):>7.0f} tokens   "
              f"({st.mean(s) / max(1, n):.1f} por pregunta)")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
