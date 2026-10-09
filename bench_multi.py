"""Preguntas encadenadas: las mismas N preguntas sobre el mismo caso, en tres modos.

Ademas de los tres modos, mide una cuarta cosa que es la clave de todo: cuanto cuesta
preguntar N cosas de UNA vez frente a preguntarlas de una en una. En modo decision la
respuesta es "casi nada"; en modo chat es "N veces".

    python bench_multi.py
    python bench_multi.py --grupo frutas
"""

import argparse
import json
import os
import re
import statistics as st
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casos_multi  # noqa: E402
import preguntar  # noqa: E402
import ejemplos_typesafe as ts  # noqa: E402

SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096")
AQUI = os.path.dirname(os.path.abspath(__file__))


def _post(path, payload, timeout=180):
    req = urllib.request.Request(
        SERVIDOR.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        cuerpo = json.loads(r.read().decode("utf-8"))
    return cuerpo, (time.perf_counter() - t0) * 1000.0


def _tipo_ts(criterios):
    if isinstance(criterios, list):
        return "score"
    if isinstance(criterios, dict) and set(criterios) <= {"true", "false"}:
        return "noul"
    return "choice"


# --------------------------------------------------------------------------- #
# los modos
# --------------------------------------------------------------------------- #
def modo_tipado(estado, preguntas):
    """Formato TypeSafe: un `questions` por pregunta, todas en una peticion."""
    # El formato de TypeSafe es `questions: {id: {type, instructions, criteria}}`.
    # Aqui se traduce igual que en ejemplos_typesafe, pero con N preguntas en vez de
    # una: es la misma conversion campo a campo.
    esquema = {}
    for pid, p, c, _ in preguntas:
        if isinstance(c, list):
            detalle = " ".join(f"{i} = {t}." for i, t in enumerate(c))
            esquema[pid] = {"type": "number", "minimum": 0, "maximum": len(c) - 1,
                            "step": 1,
                            "description": f"{p} Niveles, de menor a mayor: {detalle}"}
        elif isinstance(c, dict) and set(c) <= {"true", "false"}:
            esquema[pid] = {"type": "boolean",
                            "description": (f"{p} true = {c['true']}. "
                                            f"false = {c['false']}.")}
        else:
            esq = {"type": "enum", "choices": list(c),
                   "description": f"{p} " + " ".join(f"'{k}' = {v}." for k, v in c.items())}
            esquema[pid] = esq

    cuerpo, ms = _post("/v1/decision",
                       {"instructions": "Respondes solo con los valores del esquema.",
                        "schema": esquema, "contexts": [estado]})
    return cuerpo["results"][0]["fields"], ms, 0


def modo_natural(estado, preguntas):
    """El caso escrito con cabeceras -> parseado -> N campos en una peticion."""
    partes = [f"input: {estado}"]
    for pid, p, c, _ in preguntas:
        if isinstance(c, list):
            partes.append(f"---\nask: {p}\nscore:\n"
                          + "\n".join(f"  {n}" for n in c))
        elif isinstance(c, dict) and set(c) <= {"true", "false"}:
            partes.append(f"---\nask: {p}\nnoul:\n"
                          f"  false: {c['false']}\n  true: {c['true']}")
        else:
            partes.append(f"---\nask: {p}\nchoice:\n"
                          + "\n".join(f"  {k}: {v}" for k, v in c.items()))
    texto = "\n\n".join(partes)

    estado2, parseadas = preguntar.parsear(texto)

    # El parser nombra las preguntas q1..qN (no conoce los ids originales), asi que
    # hay que renombrarlas al id de verdad. Sin esto el campo no se encuentra y todas
    # las respuestas salen vacias: daba 0% con 64 "sin respuesta".
    esquema = {}
    for (_, spec), (pid, _, _, _) in zip(parseadas, preguntas):
        esquema[pid] = spec

    cuerpo, ms = _post("/v1/decision",
                       {"instructions": "Respondes solo con los valores del esquema.",
                        "schema": esquema, "contexts": [estado2]})
    return cuerpo["results"][0]["fields"], ms, 0


def modo_llm(estado, preguntas):
    """Las N preguntas en un solo texto, y a leer la respuesta del texto."""
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
                        "max_tokens": 512,
                        "chat_template_kwargs": {"enable_thinking": False}})
    texto = (cuerpo["choices"][0]["message"].get("content") or "").strip()
    tokens = cuerpo.get("usage", {}).get("completion_tokens", 0)

    # se lee id=valor, una por linea, como haria cualquier cliente
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
            ms, tokens)


def comparar(esperado, obtenido):
    if obtenido is None:
        return False
    if isinstance(esperado, bool):
        return obtenido is esperado
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        try:
            return float(obtenido) == float(esperado)
        except (TypeError, ValueError):
            return False
    return obtenido == esperado


MODOS = {"tipado": modo_tipado, "natural": modo_natural, "llm": modo_llm}


def main():
    ap = argparse.ArgumentParser(prog="bench_multi")
    ap.add_argument("--grupo", choices=list(casos_multi.CASOS))
    ap.add_argument("--out", default=os.path.join(AQUI, "results", "multi.json"))
    a = ap.parse_args()

    grupos = [a.grupo] if a.grupo else list(casos_multi.CASOS)
    registro = []

    for grupo in grupos:
        for caso in casos_multi.CASOS[grupo]:
            estado, preguntas = caso
            print(f"\n{grupo} · {estado}  ({len(preguntas)} preguntas)", flush=True)
            for nombre, fn in MODOS.items():
                try:
                    # Calentamiento: la primera llamada del mismo estado deja la cache
                    # KV caliente y la segunda sale mucho mas rapida. Sin esto, el modo
                    # que corre primero parece mas lento por puro orden de ejecucion
                    # (medido: 178 ms el primero frente a 65 ms el segundo, con el mismo
                    # esquema). Se mide la segunda.
                    fn(estado, preguntas)
                    campos, ms, tokens = fn(estado, preguntas)
                except Exception as e:                             # noqa: BLE001
                    campos, ms, tokens = {}, 0.0, 0
                    print(f"    ERROR {nombre}: {type(e).__name__}: {e}")
                for pid, p, c, esperado in preguntas:
                    f = campos.get(pid) or {}
                    obtenido = f.get("value")
                    registro.append({
                        "grupo": grupo, "estado": estado, "id": pid, "modo": nombre,
                        "tipo": _tipo_ts(c), "esperado": str(esperado),
                        "obtenido": str(obtenido), "ok": comparar(esperado, obtenido),
                        "ms_peticion": round(ms, 1), "tokens": tokens,
                        "confianza": f.get("confidence"),
                        # La distribucion entera sobre las opciones, para poder explicar
                        # no solo que eligio sino como repartio la probabilidad.
                        "probabilities": f.get("probabilities"),
                    })
                print(f"    {nombre:<11} {ms:>7.0f} ms  {tokens:>4} tok", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1)

    informe(registro, grupos)
    print(f"\ncrudo: {a.out}   ({len(registro)} respuestas)\n")


def informe(registro, grupos):
    print("\n" + "=" * 78)
    print("  PREGUNTAS ENCADENADAS")
    print("=" * 78)

    print(f"\n  {'modo':<12} {'acierto':>9} {'p50 ms/caso':>13} "
          f"{'tok/caso':>10} {'sin resp':>9}")
    for modo in MODOS:
        filas = [r for r in registro if r["modo"] == modo]
        if not filas:
            continue
        n = len(filas)
        ok = sum(r["ok"] for r in filas)
        porcaso = {}
        for r in filas:
            porcaso.setdefault(r["estado"], r["ms_peticion"])
        ms = list(porcaso.values())
        tk = sum(r["tokens"] for r in filas) / len(porcaso)
        sin = sum(1 for r in filas if r["obtenido"] == "None")
        print(f"  {modo:<12} {100*ok/n:>7.1f}% {st.median(ms):>13.0f} "
              f"{tk:>10.1f} {sin:>9}")

    print("\n  --- por tipo de pregunta ---")
    print(f"  {'modo':<12} {'choice':>9} {'score':>9} {'si/no':>9}")
    for modo in MODOS:
        linea = f"  {modo:<12}"
        for tipo in ("choice", "score", "noul"):
            filas = [r for r in registro if r["modo"] == modo and r["tipo"] == tipo]
            linea += f" {100*sum(r['ok'] for r in filas)/len(filas):>8.1f}%" \
                if filas else f" {'-':>9}"
        print(linea)

    print("\n  --- cada caso, en los modos con esquema ---")
    for estado in dict.fromkeys(r["estado"] for r in registro):
        filas = [r for r in registro if r["estado"] == estado]
        for modo in MODOS:
            sub = [r for r in filas if r["modo"] == modo]
            if not sub:
                continue
            ok = sum(r["ok"] for r in sub)
            ms = sub[0]["ms_peticion"]
            fallos = [r["id"] for r in sub if not r["ok"]]
            marca = "" if ok == len(sub) else f"   falla: {', '.join(fallos)}"
            print(f"  {estado[:34]:<34} {modo:<11} {ok:>2}/{len(sub)}"
                  f" {ms:>6.0f} ms{marca}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
