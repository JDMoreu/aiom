"""Genera docs/DETALLE.md: las 154 preguntas, con todo lo que hace falta para leerlas.

Un solo documento. Por cada pregunta:

  - la entrada y la pregunta
  - las OPCIONES posibles y qué significa cada una
  - qué se ESPERABA y por qué
  - qué eligió cada modo, cómo REPARTIÓ la probabilidad y cuánto TARDÓ

    python detalle.py
"""

import json
import os
import statistics as st

AQUI = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(AQUI, "docs", "DETALLE.md")

import casos_modos  # noqa: E402
import casos_multi  # noqa: E402
import razones  # noqa: E402

MODOS = ("tipado", "natural", "llm")


def leer(nombre):
    ruta = os.path.join(AQUI, "results", nombre)
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def describir(crit):
    """(tipo, [(valor, significado)]) a partir de los criterios del caso."""
    if isinstance(crit, list):
        return "score", [(str(i), t) for i, t in enumerate(crit)]
    if isinstance(crit, dict) and set(crit) <= {"true", "false"}:
        return "probability", [("true", crit.get("true", "Sí")),
                               ("false", crit.get("false", "No"))]
    return "choice", [(k, v) for k, v in crit.items()]


def reparto(prob, orden):
    """La probabilidad de cada opción, en el orden en que se declararon."""
    partes = []
    for k in orden:
        if k in prob:
            partes.append(f"`{k}` {float(prob[k]):.2f}")
    return " · ".join(partes)


def tabla(L, registros, orden):
    """Qué eligió cada modelo y cuánto tardó. Las probabilidades van al final."""
    L.append("| modelo | eligió | tiempo | probabilidad de cada opción |")
    L.append("|---|---|---|---|")
    for m in MODOS:
        r = next((x for x in registros if x["modo"] == m), None)
        if not r:
            continue
        v = r["obtenido"]
        ms = r.get("ms", r.get("ms_peticion", 0))
        if v in ("None", None):
            L.append(f"| `{m}` | **no se pudo leer** | {ms:.0f} ms | — |")
            continue
        # El veredicto sale del campo ya calculado en el banco: recomparar aqui como
        # texto marcaba en rojo respuestas correctas (el valor llega "1.0" y la
        # referencia es 1).
        marca = "" if r.get("exacto", r.get("ok")) else " **← MAL**"
        prob = r.get("probabilities")
        if prob:
            rep = reparto(prob, orden)
            conf = r.get("confidence") or r.get("confianza")
            if isinstance(conf, (int, float)):
                rep += f" · conf {conf:.2f}"
        else:
            rep = "escribe texto: no da probabilidades"
        L.append(f"| `{m}` | **`{v}`**{marca} | {ms:.0f} ms | {rep} |")
    L.append("")


def metricas(L, registros, clave_ms, clave_ok):
    """Tabla de métricas por modo: acierto, tiempos y confianza media.

    Sin columna de tokens a proposito: el modo decision no genera y el chat si, asi
    que ponerlos en la misma columna compara magnitudes distintas.
    """
    L.append("| modo | acierto | p50 | media | máx | confianza media |")
    L.append("|---|---|---|---|---|---|")
    for m in MODOS:
        s = [x for x in registros if x["modo"] == m]
        if not s:
            continue
        ok = sum(bool(x[clave_ok]) for x in s)
        ms = [x[clave_ms] for x in s]
        confs = [x.get("confidence") or x.get("confianza") for x in s]
        confs = [c for c in confs if isinstance(c, (int, float))]
        cf = f"{st.mean(confs):.2f}" if confs else "—"
        L.append(f"| `{m}` | **{100 * ok / len(s):.1f}%** ({ok}/{len(s)}) | "
                 f"{st.median(ms):.0f} ms | {st.mean(ms):.0f} ms | {max(ms):.0f} ms | "
                 f"{cf} |")
    L.append("")


def pregunta(L, titulo, entrada, crit, esperado, razon, registros):
    """Un bloque por pregunta: entrada, opciones, lo esperado y qué eligió cada modo."""
    _, opciones = describir(crit)
    L.append(f"\n#### {titulo}\n")
    L.append(f"> {entrada}\n")

    etiqueta = {"choice": "choice", "score": "score",
                "probability": "noul"}[describir(crit)[0]]
    L.append(f"**{etiqueta}:**\n")
    for valor, signif in opciones:
        L.append(f"- `{valor}` — {signif}")
    L.append("")

    L.append(f"**Se esperaba `{esperado}`.** {razon}\n")
    tabla(L, registros, [v for v, _ in opciones])



def sin_numerar(lineas):
    """Quita la numeracion manual de los encabezados.

    Norma del estandar de documentacion: Pandoc numera solo al exportar, y si el
    encabezado ya trae el numero sale "1. 1. Introduccion". Ademas, al no llevar
    numero, reorganizar secciones no obliga a renumerar a mano.
    """
    import re
    salida = []
    for l in lineas:
        m = re.match("^(#{2,4})[ ]+[0-9]+(?:[.][0-9]+)*[.]?[ ]+(.*)$", l)
        salida.append(m.group(1) + " " + m.group(2) if m else l)
    return salida

def main():
    modos = leer("modos.json")
    multi = leer("multi.json")
    L = []

    L.append("# Las 154 preguntas: opciones, respuesta esperada y tiempos\n")
    L.append("Cada pregunta con sus opciones, lo que se esperaba y por qué, lo que")
    L.append("contestó cada modo, cómo repartió la probabilidad y cuánto tardó.\n")
    L.append("Se regenera con `python detalle.py`.\n")

    # ------------------------------------------------------- los tres tipos
    L.append("---\n")
    L.append("## Los tres tipos\n")
    for clave in ("choice", "score", "probability"):
        t = razones.TIPOS[clave]
        L.append(f"- **{t['nombre']}** — {t['que_es']} {t['que_mirar']}")
    L.append("")

    # ------------------------------------------------------------- resumen
    L.append("---\n")
    L.append("## Resumen\n")
    L.append("Todo junto, para ver la diferencia de un vistazo. El detalle de cada")
    L.append("sección va más abajo.\n")

    L.append("### Una pregunta por caso (90 casos, 30 de cada tipo)\n")
    metricas(L, modos, "ms", "exacto")

    L.append("### Varias preguntas encadenadas (64 preguntas, 14 casos)\n")
    metricas(L, multi, "ms_peticion", "ok")

    L.append("### Por tipo de pregunta\n")
    L.append("| tipo | modo | acierto | p50 | confianza media |")
    L.append("|---|---|---|---|---|")
    for tipo, nom in (("choice", "CHOICE"), ("score", "SCORE"),
                      ("probability", "PROBABILITY")):
        for m in MODOS:
            s = [x for x in modos if x["tipo"] == tipo and x["modo"] == m]
            if not s:
                continue
            ok = sum(bool(x["exacto"]) for x in s)
            confs = [x["confidence"] for x in s
                     if isinstance(x.get("confidence"), (int, float))]
            cf = f"{st.mean(confs):.2f}" if confs else "—"
            L.append(f"| {nom} | `{m}` | {100 * ok / len(s):.1f}% | "
                     f"{st.median([x['ms'] for x in s]):.0f} ms | {cf} |")
    for tipo, nom in (("choice", "encadenada CHOICE"), ("score", "encadenada SCORE"),
                      ("noul", "encadenada sí/no")):
        for m in MODOS:
            s = [x for x in multi if x["tipo"] == tipo and x["modo"] == m]
            if not s:
                continue
            ok = sum(bool(x["ok"]) for x in s)
            confs = [x["confianza"] for x in s
                     if isinstance(x.get("confianza"), (int, float))]
            cf = f"{st.mean(confs):.2f}" if confs else "—"
            L.append(f"| {nom} | `{m}` | {100 * ok / len(s):.1f}% | "
                     f"{st.median([x['ms_peticion'] for x in s]):.0f} ms | {cf} |")
    L.append("")

    # --------------------------------------------------------- hallazgos
    L.append("\n---\n")
    L.append("## Dos fallos que NO son del modelo\n")
    L.append("Antes de echarle la culpa al tamaño del modelo conviene comprobar la")
    L.append("pregunta. Estos dos casos se repitieron cambiando **solo la descripción del")
    L.append("campo**, con el mismo modelo y la misma máquina.\n")

    for h in razones.DIAGNOSTICO:
        L.append(f"### {h['titulo']}\n")
        L.append(f"**Qué se ve.** {h['sintoma']}\n")
        L.append("**Medido:**\n")
        for que, res in h["medido"]:
            L.append(f"- {que} → {res}")
        L.append("")
        L.append(f"**Causa.** {h['causa']}\n")
        L.append(f"**Lección.** {h['leccion']}\n")

    L.append("### Y sobre el RAG\n")
    L.append("La intuición de que un modelo pequeño se queda corto y hay que suplirlo")
    L.append("con RAG y una base vectorial es buena **en general** — pero ninguno de")
    L.append("estos dos fallos se arregla con eso. En los dos, **el mismo modelo acierta")
    L.append("cuando se le quita la descripción de encima**: no le falta información,")
    L.append("le sobra ruido. Un RAG habría traído más texto al contexto, que es")
    L.append("exactamente lo que aquí empeora el resultado.\n")
    L.append("El orden correcto es: **primero simplificar la pregunta, después medir, y")
    L.append("solo si el modelo sigue sin poder, darle más contexto.** Meterse en RAG")
    L.append("antes de eso es pagar complejidad por un problema que no existe.\n")

    L.append("---\n")
    L.append("## 1. Una pregunta por caso (90)\n")

    for tipo, lista, titulo in (
            ("choice", casos_modos.CHOICE, "CHOICE"),
            ("score", casos_modos.SCORE, "SCORE"),
            ("probability", casos_modos.PROBABILITY, "PROBABILITY")):
        L.append(f"\n### {titulo} — {len(lista)} preguntas\n")
        metricas(L, [r for r in modos if r["tipo"] == tipo], "ms", "exacto")
        por_razon = {"choice": razones.CHOICE, "score": razones.SCORE,
                     "probability": razones.PROBABILITY}[tipo]
        for i, (estado, preg, crit, esperado) in enumerate(lista, 1):
            regs = [r for r in modos if r["tipo"] == tipo and r["indice"] == i]
            if not regs:
                continue
            pregunta(L, f"{i}. {preg}", estado, crit, esperado,
                     por_razon.get(i, ""), regs)

    # ------------------------------------------------- 2. encadenadas
    if multi:
        L.append("\n---\n")
        L.append("## 2. Varias preguntas encadenadas (64)\n")
        L.append("Cada entrada lleva varias preguntas **en una sola petición**. El")
        L.append("tiempo es el de la petición completa: responde a todas de golpe.\n")

        for grupo, casos in casos_multi.CASOS.items():
            L.append(f"\n### {grupo.capitalize()}\n")
            metricas(L, [r for r in multi if r["grupo"] == grupo], "ms_peticion", "ok")
            for estado, preguntas in casos:
                L.append(f"\n### {estado}\n")
                if estado in razones.FRUTAS:
                    L.append(f"{razones.FRUTAS[estado]}\n")
                for pid, preg, crit, esperado in preguntas:
                    regs = [r for r in multi
                            if r["estado"] == estado and r["id"] == pid]
                    pregunta(L, preg, estado, crit, esperado,
                             razones.TICKETS.get((estado, pid), ""), regs)
                r0 = [r for r in multi
                      if r["estado"] == estado and r["modo"] == "tipado"]
                if r0:
                    L.append(f"*La petición completa tarda "
                             f"{r0[0]['ms_peticion']:.0f} ms.*\n")

    # ------------------------------------------------------------ leyenda
    L.append("\n---\n")
    L.append("## Cómo leerlo\n")
    L.append("- **`← MAL`** — no coincide con lo que se esperaba. Si no aparece, acertó.")
    L.append("- **`conf`** — lo repartida que está la probabilidad: 1,00 es un solo pico,")
    L.append("  cerca de 0 es un empate. En PROBABILITY no hace falta, el número ya lo dice.")
    L.append("- **`escribe texto`** — el modo `llm` no da probabilidades: redacta, y de ahí")
    L.append("  se lee una sola respuesta. **`no se pudo leer`** es que ni eso.")
    L.append("- El tiempo es el de la petición HTTP, con la caché ya caliente.\n")
    L.append("---\n")
    L.append("*Documento generado por `detalle.py` a partir de `results/modos.json` y")
    L.append("`results/multi.json`. Para comprobar que las cifras siguen cuadrando con los")
    L.append("datos: `python verificar.py`.*\n")

    with open(DOC, "w", encoding="utf-8") as f:
        f.write("\n".join(sin_numerar(L)) + "\n")
    print(f"escrito {DOC}  ({len(L)} lineas)")


if __name__ == "__main__":
    raise SystemExit(main())
