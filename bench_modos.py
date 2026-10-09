"""Los mismos 90 casos, en tres modos, para comparar precision, tiempos y fallos.

  tipado    el formato de TypeSafe: JSON con state.input + questions.decision y
            `criteria`. El que usa quien integra por API.
  natural   el mismo caso escrito con cabeceras (choice: / score: / boolean:).
            El que usa quien escribe a mano.
  llm       la pregunta a pelo por /v1/chat/completions, sin esquema: es el modo por
            defecto de cualquier LLM. Hay que leerle la respuesta del texto.

Los tres responden a los MISMOS casos con la MISMA verdad de referencia.

    python bench_modos.py                 # los 90 casos x 3 modos
    python bench_modos.py --tipo choice   # solo un tipo
    python bench_modos.py --modo llm      # solo un modo
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
import casos_modos  # noqa: E402
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


# --------------------------------------------------------------------------- #
# los tres modos: cada uno devuelve (respuesta, ms, tokens)
# --------------------------------------------------------------------------- #
def modo_tipado(caso):
    """Formato TypeSafe -> traducido -> /v1/decision. El camino de una integracion."""
    estado, pregunta, criterios, _ = caso

    # El tipo sale de la forma de los criterios, igual que en TypeSafe:
    # lista -> niveles ordenados; {true,false} -> si/no; resto -> opciones.
    if isinstance(criterios, list):
        tipo_ts = "score"
    elif isinstance(criterios, dict) and set(criterios) <= {"true", "false"}:
        tipo_ts = "noul"
    else:
        tipo_ts = "choice"

    peticion = {"state": {"input": estado},
                "questions": {"decision": {"type": tipo_ts,
                                           "instructions": pregunta,
                                           "criteria": criterios}}}
    estado2, nombre, esquema = ts.traducir(peticion)
    cuerpo, ms = _post("/v1/decision",
                       {"instructions": "Respondes solo con los valores del esquema.",
                        "schema": esquema, "contexts": [estado2]})
    campo = cuerpo["results"][0]["fields"][nombre]
    return campo["value"], ms, 0, campo


def modo_natural(caso):
    """El caso escrito con cabeceras -> parseado -> /v1/decision."""
    estado, pregunta, criterios, _ = caso
    if isinstance(criterios, list):
        texto = (f"input: {estado}\n\nask: {pregunta}\n"
                 f"score:\n" +
                 "\n".join(f"  {n}" for n in criterios))
    elif isinstance(criterios, dict) and set(criterios) <= {"true", "false"}:
        texto = (f"input: {estado}\n\nask: {pregunta}\n"
                 f"boolean:\n"
                 f"  false: {criterios['false']}\n  true: {criterios['true']}")
    else:
        texto = (f"input: {estado}\n\nask: {pregunta}\nchoice:\n" +
                 "\n".join(f"  {k}: {v}" for k, v in criterios.items()))

    estado2, preguntas = preguntar.parsear(texto)
    cuerpo, ms = _post("/v1/decision",
                       {"instructions": "Respondes solo con los valores del esquema.",
                        "schema": {n: c for n, c in preguntas}, "contexts": [estado2]})
    nombre = preguntas[0][0]
    campo = cuerpo["results"][0]["fields"][nombre]
    return campo["value"], ms, 0, campo


def modo_llm(caso):
    """La pregunta a pelo por chat. Hay que sacarle la respuesta del texto."""
    estado, pregunta, criterios, _ = caso

    if isinstance(criterios, list):
        opciones = "\n".join(f"{i}. {n}" for i, n in enumerate(criterios))
        pide = f"Responde SOLO con un número del 0 al {len(criterios) - 1}, nada más."
    elif isinstance(criterios, dict) and set(criterios) <= {"true", "false"}:
        opciones = f"true: {criterios['true']}\nfalse: {criterios['false']}"
        pide = "Responde SOLO con true o false, nada más."
    else:
        opciones = "\n".join(f"{k}: {v}" for k, v in criterios.items())
        pide = ("Responde SOLO con una de estas palabras clave, nada más: "
                + ", ".join(criterios.keys()))

    prompt = (f"Caso:\n{estado}\n\nPregunta: {pregunta}\n\n"
              f"Respuestas posibles:\n{opciones}\n\n{pide}")

    cuerpo, ms = _post("/v1/chat/completions",
                       {"messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 64,
                        "chat_template_kwargs": {"enable_thinking": False}})
    texto = (cuerpo["choices"][0]["message"].get("content") or "").strip()
    tokens = cuerpo.get("usage", {}).get("completion_tokens", 0)

    return _interpretar(texto, criterios), ms, tokens, {"texto": texto}


def _interpretar(texto, criterios):
    """Saca la respuesta del texto libre del modelo, como haria cualquier cliente."""
    t = texto.strip().lower().strip('."\'`')

    if isinstance(criterios, list):
        m = re.search(r"\b([0-9])\b", t)
        return float(m.group(1)) if m and int(m.group(1)) < len(criterios) else None

    if isinstance(criterios, dict) and set(criterios) <= {"true", "false"}:
        if re.search(r"\b(true|sí|si|yes|correcto)\b", t):
            return True
        if re.search(r"\b(false|no|nope)\b", t):
            return False
        return None

    for k in criterios:
        if re.search(rf"\b{re.escape(k.lower())}\b", t):
            return k
    return None


# --------------------------------------------------------------------------- #
def comparar(esperado, obtenido):
    """(acierto_exacto, acierto_aproximado). En SCORE, dentro de un nivel cuenta."""
    if obtenido is None:
        return False, False
    if isinstance(esperado, bool):
        return obtenido == esperado, obtenido == esperado
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        try:
            v = float(obtenido)
        except (TypeError, ValueError):
            return False, False
        return v == float(esperado), abs(v - float(esperado)) <= 1
    return obtenido == esperado, obtenido == esperado


def main():
    ap = argparse.ArgumentParser(prog="bench_modos")
    ap.add_argument("--tipo", choices=list(casos_modos.TODOS), help="solo un tipo")
    ap.add_argument("--modo", choices=["tipado", "natural", "llm"], help="solo un modo")
    ap.add_argument("--out", default=os.path.join(AQUI, "results", "modos.json"))
    a = ap.parse_args()

    tipos = [a.tipo] if a.tipo else list(casos_modos.TODOS)
    modos = [a.modo] if a.modo else ["tipado", "natural", "llm"]
    funciones = {"tipado": modo_tipado, "natural": modo_natural, "llm": modo_llm}

    registro = []
    total_casos = sum(len(casos_modos.TODOS[t]) for t in tipos)
    hechos = 0

    for tipo in tipos:
        casos = casos_modos.TODOS[tipo]
        print(f"\n{tipo.upper()}  ({len(casos)} casos)", flush=True)

        for i, caso in enumerate(casos, 1):
            esperado = caso[3]
            for modo in modos:
                try:
                    # Calentamiento: el mismo caso ya enviado deja la cache KV caliente
                    # y la segunda llamada sale mas rapida. Sin esto el modo que corre
                    # primero parece mas lento por orden de ejecucion, no por ser peor.
                    funciones[modo](caso)
                    obtenido, ms, tokens, extra = funciones[modo](caso)
                except Exception as e:                              # noqa: BLE001
                    obtenido, ms, tokens, extra = None, 0.0, 0, {"error": str(e)[:120]}
                exacto, aprox = comparar(esperado, obtenido)
                # Se guarda la distribucion entera (probabilidad de CADA opcion) y la
                # confianza, no solo la ganadora: sin esto no se puede explicar por que
                # el modelo eligio lo que eligio ni que tan cerca estuvo el resto.
                registro.append({
                    "tipo": tipo, "indice": i, "modo": modo,
                    "esperado": esperado if not isinstance(esperado, bool) else str(esperado),
                    "obtenido": (obtenido if not isinstance(obtenido, bool)
                                 else str(obtenido)),
                    "exacto": exacto, "aproximado": aprox,
                    "ms": round(ms, 1), "tokens": tokens,
                    "probabilities": (extra or {}).get("probabilities"),
                    "confidence": (extra or {}).get("confidence"),
                    "extra": extra if modo == "llm" else {},
                })
                hechos += 1
            print(f"  {i:>2}/{len(casos)}", end="\r", flush=True)
        print(f"  {len(casos)}/{len(casos)} listo" + " " * 20)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1)

    informe(registro, tipos, modos)
    print(f"\ncrudo: {a.out}   ({hechos} ejecuciones)\n")


def informe(registro, tipos, modos):
    print("\n" + "=" * 78)
    print("  RESULTADOS")
    print("=" * 78)

    for tipo in tipos:
        print(f"\n  --- {tipo.upper()} ---")
        print(f"  {'modo':<10} {'acierto':>9} {'aprox':>8} {'p50 ms':>9} "
              f"{'media ms':>10} {'tokens':>8} {'sin resp':>9}")
        for modo in modos:
            filas = [r for r in registro if r["tipo"] == tipo and r["modo"] == modo]
            if not filas:
                continue
            n = len(filas)
            ex = sum(r["exacto"] for r in filas)
            ap = sum(r["aproximado"] for r in filas)
            ms = [r["ms"] for r in filas if r["ms"]]
            tk = sum(r["tokens"] for r in filas)
            sin = sum(1 for r in filas if r["obtenido"] is None)
            print(f"  {modo:<10} {100*ex/n:>7.1f}% {100*ap/n:>7.1f}% "
                  f"{st.median(ms):>9.0f} {st.mean(ms):>10.0f} "
                  f"{tk/n:>8.1f} {sin:>9}")

    print(f"\n  --- GLOBAL (los {len(tipos)} tipos juntos) ---")
    print(f"  {'modo':<10} {'acierto':>9} {'aprox':>8} {'p50 ms':>9} "
          f"{'media ms':>10} {'tokens':>8} {'sin resp':>9}")
    for modo in modos:
        filas = [r for r in registro if r["modo"] == modo]
        if not filas:
            continue
        n = len(filas)
        ex = sum(r["exacto"] for r in filas)
        ap = sum(r["aproximado"] for r in filas)
        ms = [r["ms"] for r in filas if r["ms"]]
        tk = sum(r["tokens"] for r in filas)
        sin = sum(1 for r in filas if r["obtenido"] is None)
        print(f"  {modo:<10} {100*ex/n:>7.1f}% {100*ap/n:>7.1f}% "
              f"{st.median(ms):>9.0f} {st.mean(ms):>10.0f} "
              f"{tk/n:>8.1f} {sin:>9}")

    print("\n  --- los dos modos con esquema, caso por caso (donde discrepan) ---")
    disc = 0
    for tipo in tipos:
        for i in range(1, len(casos_modos.TODOS[tipo]) + 1):
            t = [r for r in registro if r["tipo"] == tipo and r["indice"] == i
                 and r["modo"] == "tipado"]
            ntl = [r for r in registro if r["tipo"] == tipo and r["indice"] == i
                   and r["modo"] == "natural"]
            if not t or not ntl:
                continue
            if (t[0]["obtenido"], t[0]["exacto"]) != (ntl[0]["obtenido"],
                                                      ntl[0]["exacto"]):
                disc += 1
                print(f"  {tipo:<12} caso {i:>2}: tipado={t[0]['obtenido']!r} "
                      f"(ok={t[0]['exacto']})  natural={ntl[0]['obtenido']!r} "
                      f"(ok={ntl[0]['exacto']})")
    if not disc:
        print("  ninguna: los dos modos coinciden en los 90 casos")

    print("\n  --- los fallos del modo llm (texto que no se pudo interpretar) ---")
    fallos = [r for r in registro if r["modo"] == "llm" and r["obtenido"] is None]
    for r in fallos[:8]:
        t = (r["extra"] or {}).get("texto", "")[:70].replace("\n", " ")
        print(f"  {r['tipo']:<12} caso {r['indice']:>2}: el texto decia {t!r}")
    if len(fallos) > 8:
        print(f"  ... y {len(fallos) - 8} mas")


if __name__ == "__main__":
    raise SystemExit(main())
