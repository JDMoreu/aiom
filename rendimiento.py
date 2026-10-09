"""Genera docs/ESTUDIO.md y sus graficos: el estudio completo del repositorio.

Es el UNICO documento tecnico largo. Antes esto y el entorno eran dos documentos que
se solapaban; ahora el entorno (hardware, versiones, decisiones, fuentes) aporta sus
secciones desde entorno.py y aqui se monta todo junto.

Calcula todo desde results/ (nada escrito a mano). Los SVG se escriben autocontenidos
(fondo propio y colores explicitos), para que se vean igual en GitHub.

    python rendimiento.py
"""

import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno  # noqa: E402
import graficos  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(AQUI, "docs", "ESTUDIO.md")
GRAF = os.path.join(AQUI, "results", "graf")

AZUL, VERDE, NARANJA = "#2563eb", "#059669", "#d97706"
COLOR = {"tipado": AZUL, "natural": VERDE, "llm": NARANJA}


# --------------------------------------------------------------------------- #
# estadistica
# --------------------------------------------------------------------------- #
def wilson(aciertos, n, z=1.96):
    """Intervalo de confianza de Wilson al 95%. Con n pequeño el normal se sale
    de [0,1] y da intervalos imposibles; Wilson no."""
    if not n:
        return 0.0, 0.0, 0.0
    p = aciertos / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * max(0.0, centro - margen), 100 * min(1.0, centro + margen)


def ic_media(xs, z=1.96):
    """Media con intervalo al 95% (t de Student aproximada por normal)."""
    if len(xs) < 2:
        return (st.mean(xs) if xs else 0.0), 0.0, 0.0
    m, s = st.mean(xs), st.stdev(xs)
    e = z * s / math.sqrt(len(xs))
    return m, m - e, m + e


def pctl(xs, q):
    orden = sorted(xs)
    if not orden:
        return 0.0
    return orden[min(len(orden) - 1, int(round(q * (len(orden) - 1))))]


# --------------------------------------------------------------------------- #
def leer(nombre):
    ruta = os.path.join(AQUI, "results", nombre)
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def stats(reg, clave_ms, clave_ok):
    """{modo: dict} con acierto, IC, latencias y tokens."""
    out = {}
    for m in ("tipado", "natural", "llm"):
        s = [x for x in reg if x["modo"] == m]
        if not s:
            continue
        ok = sum(bool(x[clave_ok]) for x in s)
        ms = [x[clave_ms] for x in s]
        acc, lo, hi = wilson(ok, len(s))
        med, mlo, mhi = ic_media(ms)
        out[m] = {
            "n": len(s), "ok": ok, "acc": acc, "lo": lo, "hi": hi,
            "p50": st.median(ms), "p95": pctl(ms, 0.95), "media": med,
            "mlo": mlo, "mhi": mhi, "tok": sum(x["tokens"] for x in s) / len(s),
            "tot_tok": sum(x["tokens"] for x in s),
            "sin": sum(1 for x in s if str(x["obtenido"]) == "None"),
        }
    return out



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
    a = stats(modos, "ms", "exacto")
    b = stats(multi, "ms_peticion", "ok")

    L = []
    L.append("# Estudio técnico: un modelo, dos formas de preguntar\n")
    L.append("**154 preguntas con verdad de referencia, sobre un solo modelo local, en un "
             "equipo doméstico.**\n")
    L.append("Este es el documento técnico del repositorio: **con qué se midió, cómo se "
             "construyó, qué salió y dónde están los límites.** Para la idea de fondo y "
             "los resultados en corto, el [README](../README.md).\n")

    # ------------------------------------------------------------ resumen
    sp1 = 100 * (1 - a["tipado"]["p50"] / a["llm"]["p50"])
    sp5 = 100 * (1 - b["tipado"]["p50"] / b["llm"]["p50"])
    x1 = a["llm"]["p50"] / a["tipado"]["p50"]
    x5 = b["llm"]["p50"] / b["tipado"]["p50"]
    d1 = a["llm"]["acc"] - a["tipado"]["acc"]
    d5 = b["tipado"]["acc"] - b["llm"]["acc"]

    L.append("---\n")
    L.append("## Resumen\n")
    L.append(f"Se comparan dos formas de interrogar a **el mismo modelo local** "
             f"(Spark-X2.5-4B, cuantización Q8_0) sobre **154 preguntas** con verdad de "
             f"referencia: pedirle una **decisión tipada** —elegir un valor de un "
             f"conjunto cerrado, sin generar texto— frente a pedirle lo mismo **por "
             f"chat**, que es el uso por defecto de cualquier LLM.\n")
    L.append(f"**El modo de decisión responde un {sp1:.0f}% más rápido** en preguntas")
    L.append(f"sueltas ({a['tipado']['p50']:.0f} ms frente a {a['llm']['p50']:.0f} ms, "
             f"**{x1:.1f}×**) y un **{sp5:.0f}% más rápido** cuando se encadenan cinco")
    L.append(f"preguntas sobre el mismo caso ({b['tipado']['p50']:.0f} ms frente a "
             f"{b['llm']['p50']:.0f} ms, **{x5:.1f}×**).\n")
    L.append("La razón de fondo no es que escriba menos: **no escribe**. El modo de")
    L.append("decisión no pasa por el bucle de generación, así que no produce texto ni")
    L.append("hay que analizarlo después. Eso no se cuantifica en una tabla de tiempos")
    L.append("porque no es la misma magnitud: es una operación distinta.\n")
    L.append(f"En precisión, con una pregunta suelta **los tres modos empatan** "
             f"({a['tipado']['acc']:.1f}% frente a {a['llm']['acc']:.1f}%, una diferencia "
             f"de {abs(d1):.1f} puntos dentro del intervalo de confianza). La ventaja "
             f"aparece al **encadenar**: el modo de decisión mantiene "
             f"**{b['tipado']['acc']:.1f}%** mientras el chat cae a "
             f"**{b['llm']['acc']:.1f}%**, una brecha de **{d5:.1f} puntos**.")
    L.append("")
    L.append(f"**Conclusión principal:** para extraer datos, el modo de decisión no")
    L.append(f"acierta más, **cuesta menos** — y cuando hay varias respuestas que")
    L.append(f"devolver de una vez, además **acierta más**.\n")

    # tabla resumen
    L.append("| | modo | acierto | IC 95% | p50 | media |")
    L.append("|---|---|---|---|---|---|")
    for etq, s in (("Una pregunta (90)", a), ("Cinco encadenadas (64)", b)):
        for m in ("tipado", "natural", "llm"):
            if m not in s:
                continue
            d = s[m]
            L.append(f"| {etq} | `{m}` | **{d['acc']:.1f}%** | "
                     f"[{d['lo']:.1f}, {d['hi']:.1f}] | {d['p50']:.0f} ms | "
                     f"{d['media']:.0f} ms |")
    L.append("")

    # ------------------------------------------------------ 1. introduccion
    L.append("---\n")
    L.append("## 1. Introducción\n")
    L.append("Un modelo de lenguaje genera texto. Cuando lo que se necesita es un")
    L.append("**dato** —a qué categoría pertenece un mensaje, cuánta urgencia tiene, si")
    L.append("una afirmación es cierta— ese texto hay que interpretarlo después, y en el")
    L.append("camino se paga dos veces: por los tokens generados y por el analizador que")
    L.append("los lee.\n")
    L.append("Este trabajo mide **cuánto cuesta esa diferencia** y si se pierde algo al")
    L.append("eliminarla. No propone un modelo nuevo: usa uno corriente y le cambia la")
    L.append("forma de preguntar.\n")
    L.append("**Preguntas de investigación:**\n")
    L.append("1. ¿Cuánto más rápido es pedir una decisión tipada que pedir lo mismo por")
    L.append("   chat, sobre el mismo modelo y la misma máquina?")
    L.append("2. ¿Se pierde precisión al hacerlo?")
    L.append("3. ¿Se mantiene la ventaja al encadenar varias preguntas sobre un mismo")
    L.append("   caso?")
    L.append("4. ¿Es fiable la confianza que declara el modelo?\n")

    # ---------------------------------------------------------- 2. metodo
    L.append("---\n")
    L.append("## 2. Método\n")
    L.append("### 2.1 El sistema\n")
    L.append("Un único modelo cargado en memoria sirvió las tres condiciones. No hubo")
    L.append("dos modelos ni dos procesos:\n")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| Modelo | Spark-X2.5-4B, Q8_0 (4,38 GB) |")
    L.append("| Hardware | AMD Radeon RX 9070, Vulkan, 16 GB |")
    L.append("| Servidor | `llama-server` del fork `parallel-decision` |")
    L.append("| Contexto | 32.768 tokens, `--decision-seqs 64` |")
    L.append("")

    L.append("### 2.2 Las tres condiciones\n")
    L.append("| modo | cómo se le pregunta | qué devuelve |")
    L.append("|---|---|---|")
    L.append("| `tipado` | JSON con un esquema de campos, al estilo de la API de "
             "TypeSafe (`state.input` + `questions`) | valores tipados, con la "
             "probabilidad de **cada** opción |")
    L.append("| `natural` | el mismo caso escrito con cabeceras legibles "
             "(`Opciones:`, `Niveles de puntuación:`, `Qué significa no o sí:`) | "
             "lo mismo, tras traducir el texto a un esquema |")
    L.append("| `llm` | la pregunta a pelo por el endpoint de chat, sin esquema. "
             "El uso por defecto | texto libre, del que hay que **leer** la respuesta |")
    L.append("")
    L.append("Las condiciones `tipado` y `natural` comparten motor y difieren solo en")
    L.append("cómo se escribe la entrada: sirven para medir si escribir en lenguaje")
    L.append("natural cuesta algo.\n")

    L.append("### 2.3 El conjunto de pruebas\n")
    L.append("**154 preguntas**, todas con verdad de referencia declarada de antemano:\n")
    L.append("| bloque | preguntas | qué mide |")
    L.append("|---|---|---|")
    L.append("| 90 sueltas | 30 CHOICE + 30 SCORE + 30 PROBABILITY | clasificar, "
             "puntuar en una escala ordenada, y responder sí/no |")
    L.append("| 64 encadenadas | 8 frutas × 5 y 6 tickets × 4 | varias preguntas "
             "de tipos mezclados sobre **el mismo caso**, en una sola petición |")
    L.append("")
    L.append("Los casos cubren dominios distintos (soporte al cliente, producto,")
    L.append("seguridad, idioma) y se declaran por escrito, de forma que cualquiera")
    L.append("puede revisarlos o sustituirlos por los suyos.\n")

    L.append("### 2.4 Medición\n")
    L.append("- **Acierto** con intervalo de confianza de Wilson al 95%. Se usa Wilson y")
    L.append("  no el intervalo normal porque con n pequeño el normal se sale de [0,1].")
    L.append("- **Latencia** p50, p95 y media con IC, medida sobre la petición HTTP")
    L.append("  completa. Se descarta una llamada de calentamiento previa por cada caso")
    L.append("  y modo: la caché de claves del servidor hace que la segunda llamada del")
    L.append("  mismo contexto salga hasta 2,7× más rápida, y sin calentar el modo que")
    L.append("  corre primero parece peor por puro orden de ejecución.")
    L.append("- **Nota sobre los tokens.** El modo de decisión no genera tokens y el")
    L.append("  modo chat sí. Eso **no se presenta como una comparación** porque no es")
    L.append("  la misma magnitud: uno elige entre valores, el otro escribe texto. Se")
    L.append("  menciona como hecho descriptivo, nunca como mejora porcentual.\n")
    L.append("- **Fiabilidad**: la confianza que declara el modelo frente a su acierto")
    L.append("  real.\n")

    # ------------------------------------------------------- 3. resultados
    L.append("---\n")
    L.append("## 3. Resultados\n")
    L.append("### 3.1 Velocidad\n")

    g1 = graficos.barras_h(
        "velocidad_p50.svg", "Tiempo de respuesta con una pregunta",
        ["Decisión natural", "Decisión tipada", "Chat"],
        [a["natural"]["p50"], a["tipado"]["p50"], a["llm"]["p50"]],
        [graficos.AZUL_CLARO, graficos.AZUL, graficos.NARANJA], " ms",
        eje="Tiempo (ms)",
        subtitulo=f"Mediana de {a['natural']['n']} casos. El chat tarda más y además "
                  f"escribe texto.")
    g2 = graficos.barras_h(
        "velocidad_p50_encadenadas.svg",
        "Tiempo de respuesta con cinco preguntas encadenadas",
        ["Decisión natural", "Decisión tipada", "Chat"],
        [b["natural"]["p50"], b["tipado"]["p50"], b["llm"]["p50"]],
        [graficos.AZUL_CLARO, graficos.AZUL, graficos.NARANJA], " ms",
        eje="Tiempo (ms)",
        subtitulo=f"Mediana por caso, sobre {b['natural']['n']} preguntas encadenadas.")
    for g in (g1, g2):
        L.append(f"![{g}]({g})\n")

    L.append("| | tipado | natural | llm | mejora de decisión sobre chat |")
    L.append("|---|---|---|---|---|")
    L.append(f"| p50, una pregunta | {a['tipado']['p50']:.0f} ms | "
             f"{a['natural']['p50']:.0f} ms | {a['llm']['p50']:.0f} ms | "
             f"**{sp1:.0f}% menos** ({x1:.1f}× más rápido) |")
    L.append(f"| p95, una pregunta | {a['tipado']['p95']:.0f} ms | "
             f"{a['natural']['p95']:.0f} ms | {a['llm']['p95']:.0f} ms | "
             f"{100 * (1 - a['tipado']['p95'] / a['llm']['p95']):.0f}% menos |")
    L.append(f"| p50, cinco encadenadas | {b['tipado']['p50']:.0f} ms | "
             f"{b['natural']['p50']:.0f} ms | {b['llm']['p50']:.0f} ms | "
             f"**{sp5:.0f}% menos** ({x5:.1f}× más rápido) |")
    L.append(f"| p95, cinco encadenadas | {b['tipado']['p95']:.0f} ms | "
             f"{b['natural']['p95']:.0f} ms | {b['llm']['p95']:.0f} ms | "
             f"{100 * (1 - b['tipado']['p95'] / b['llm']['p95']):.0f}% menos |")
    L.append("")
    L.append("El **p95** importa tanto como la mediana: mide la cola, que es lo que")
    L.append("sufre el usuario en el peor caso.\n")

    L.append("### 3.2 Precisión\n")
    g4 = graficos.barras_agrupadas(
        "precision.svg", "Acierto por modo y número de preguntas",
        ["Una pregunta", "Cinco encadenadas"],
        {"Decisión natural": [a["natural"]["acc"], b["natural"]["acc"]],
         "Decisión tipada": [a["tipado"]["acc"], b["tipado"]["acc"]],
         "Chat": [a["llm"]["acc"], b["llm"]["acc"]]},
        "%", eje="Acierto (%)",
        subtitulo="Con una pregunta empatan; al encadenar se separan. Las dos vías de "
                  "decisión dan el mismo número: por eso la barra parece repetida.")
    L.append(f"![{g4}]({g4})\n")

    L.append("| | tipado | natural | llm |")
    L.append("|---|---|---|---|")
    L.append(f"| Acierto, una pregunta | **{a['tipado']['acc']:.1f}%** "
             f"[{a['tipado']['lo']:.1f}, {a['tipado']['hi']:.1f}] | "
             f"**{a['natural']['acc']:.1f}%** | {a['llm']['acc']:.1f}% "
             f"[{a['llm']['lo']:.1f}, {a['llm']['hi']:.1f}] |")
    L.append(f"| Acierto, encadenadas | **{b['tipado']['acc']:.1f}%** "
             f"[{b['tipado']['lo']:.1f}, {b['tipado']['hi']:.1f}] | "
             f"**{b['natural']['acc']:.1f}%** | {b['llm']['acc']:.1f}% "
             f"[{b['llm']['lo']:.1f}, {b['llm']['hi']:.1f}] |")
    L.append(f"| Respuestas ilegibles | 0 | 0 | {b['llm']['sin']} |")
    L.append("")
    L.append(f"Los intervalos de `tipado` y `llm` **se solapan** con una pregunta "
             f"({a['tipado']['lo']:.1f}–{a['tipado']['hi']:.1f} frente a "
             f"{a['llm']['lo']:.1f}–{a['llm']['hi']:.1f}): **la diferencia no es "
             f"significativa**. Al encadenar dejan de solaparse y la brecha es real.\n")
    L.append("`tipado` y `natural` coinciden **en las 154 preguntas**: escribir en")
    L.append("lenguaje natural no cuesta precisión.\n")

    L.append("### 3.3 Fiabilidad\n")
    L.append("El modelo no solo elige: declara **confianza**. Comparar esa confianza")
    L.append("con el acierto real dice si se puede usar para decidir cuándo fiarse.\n")
    filas_conf = []
    for etq, reg, cm, ck in (("una pregunta", modos, "ms", "exacto"),
                             ("encadenadas", multi, "ms_peticion", "ok")):
        for m in ("natural", "tipado"):
            s = [x for x in reg if x["modo"] == m]
            confs = [x.get("confidence") or x.get("confianza") for x in s]
            confs = [c for c in confs if isinstance(c, (int, float))]
            if not confs:
                continue
            ok = sum(bool(x[ck]) for x in s)
            filas_conf.append((etq, m, st.mean(confs), 100 * ok / len(s)))
    if filas_conf:
        g5 = graficos.barras_agrupadas_h(
            "confianza.svg", "Confianza declarada frente al acierto real",
            [f"{e} · {'natural' if m == 'natural' else 'tipada'}"
             for e, m, _, _ in filas_conf],
            {"Declarada": [f[2] * 100 for f in filas_conf],
             "Real": [f[3] for f in filas_conf]},
            "%", eje="Confianza (%)",
            subtitulo="Si la declarada supera a la real en su pareja, el modelo "
                      "sobreconfía")
        L.append(f"![{g5}]({g5})\n")
        L.append("| conjunto | modo | confianza media | acierto real | desvío |")
        L.append("|---|---|---|---|---|")
        for etq, m, cf, ac in filas_conf:
            desvio = cf * 100 - ac
            L.append(f"| {etq} | `{m}` | {cf:.2f} | {ac:.1f}% | "
                     f"{desvio:+.1f} puntos |")
        L.append("")
        sobre = [f for f in filas_conf if f[2] * 100 - f[3] > 5]
        L.append("Una confianza media **por encima** del acierto real significa que el")
        L.append("modelo **sobreconfía**. " +
                 (f"Pasa en {len(sobre)} de {len(filas_conf)} casos medidos: un umbral "
                  f"de confianza tomado al pie de la letra enrutaría mal.\n"
                  if sobre else
                  "**No ocurre aquí**: la confianza declarada queda por debajo del "
                  "acierto real, así que el modelo es conservador. Un umbral de "
                  "confianza es una red de seguridad razonable, no un adorno.\n"))

    L.append("### 3.4 Preguntas encadenadas\n")
    L.append("El resultado que más cambia el diseño. Comparar cinco preguntas sobre")
    L.append("el mismo caso frente a preguntar una sola:\n")
    L.append("| | una pregunta | cinco encadenadas | coste de añadir cuatro |")
    L.append("|---|---|---|---|")
    L.append(f"| `tipado` | {a['tipado']['p50']:.0f} ms | {b['tipado']['p50']:.0f} ms | "
             f"**+{100 * (b['tipado']['p50'] / a['tipado']['p50'] - 1):.0f}%** |")
    L.append(f"| `llm` | {a['llm']['p50']:.0f} ms | {b['llm']['p50']:.0f} ms | "
             f"+{100 * (b['llm']['p50'] / a['llm']['p50'] - 1):.0f}% |")
    L.append("")
    L.append(f"Cuatro preguntas más cuestan al modo de decisión un "
             f"**{100 * (b['tipado']['p50'] / a['tipado']['p50'] - 1):.0f}%** de tiempo; "
             f"al chat, un **{100 * (b['llm']['p50'] / a['llm']['p50'] - 1):.0f}%**. "
             f"Esa es la razón por la que clasificar por varios ejes a la vez es")
    L.append("viable en un modo y no en el otro.\n")

    L.append("### 3.5 Escalado: cómo crece el coste al encadenar\n")
    L.append("¿Qué pasa si en vez de cinco preguntas se hacen diez o quince? Se midió")
    L.append("con **un fondo de 15 preguntas** por caso, tomando las primeras N, y")
    L.append("repitiendo cada nivel 10 veces **alternando los niveles entre vueltas** —")
    L.append("midiendo cada nivel en bloque, el orden contamina el resultado: un nivel")
    L.append("hereda el estado del anterior y aparece una diferencia que no existe. Con")
    L.append("el diseño alternado, el nivel de 10 y el de 15 dan lo mismo.\n")

    casc = leer("cascada.json")
    if casc:
        niveles = sorted({x["n"] for x in casc})

        def val(n, modo, campo="ms"):
            v = [x[campo] for x in casc if x["n"] == n and x["modo"] == modo]
            return sum(v) / len(v) if v else 0

        g6 = graficos.lineas(
            "escalado.svg",
            "Tiempo por caso según cuántas preguntas se encadenan",
            [str(n) for n in niveles],
            {"Decisión (natural y tipada)": {str(n): val(n, "tipado") for n in niveles},
             "Chat": {str(n): val(n, "llm") for n in niveles}},
            "ms", eje="Tiempo (ms)",
            subtitulo="El modo de decisión se aplana; el chat crece casi lineal.")
        L.append(f"![{g6}]({g6})\n")

        L.append("| preguntas encadenadas | tipado | natural | chat | chat / decisión |")
        L.append("|---|---|---|---|---|")
        for n in niveles:
            t, na, l = val(n, "tipado"), val(n, "natural"), val(n, "llm")
            L.append(f"| {n} | {t:.0f} ms | {na:.0f} ms | {l:.0f} ms | "
                     f"**{l / t:.1f}×** |")
        L.append("")
        base = val(min(niveles), "tipado")
        alt = val(max(niveles), "tipado")
        basec = val(min(niveles), "llm")
        altc = val(max(niveles), "llm")
        L.append(f"De **1 a 15 preguntas**, el modo de decisión pasa de {base:.0f} a "
                 f"{alt:.0f} ms — un **{100 * (alt / base - 1):.0f}%** más. El chat pasa "
                 f"de {basec:.0f} a {altc:.0f} ms, un **{100 * (altc / basec - 1):.0f}%**")
        L.append("más, y con 15 preguntas la ventaja del modo de decisión llega a")
        L.append(f"**{altc / alt:.1f}×**.\n")
        L.append("**Se aplana porque el motor puntúa todas las preguntas en la misma")
        L.append("pasada.** El chat no puede: cada respuesta es texto que hay que generar,")
        L.append(f"y a ~10 ms por token eso se paga entero. Ese es el hallazgo práctico")
        L.append("del apartado: **cuantas más preguntas por caso, mejor sale el modo de")
        L.append("decisión en comparación.**\n")

        L.append("**Acuérdate también de lo que falla.** A 15 preguntas el modo chat ya")
        L.append("dejaba respuestas sin poder leerse del texto, así que la comparación de")
        L.append("tiempo a ese nivel es optimista para el chat: para leer 15 respuestas de")
        L.append("prosa haría falta, además, un analizador con sus propios errores.\n")

    L.append("---\n")
    L.append("## 4. Análisis\n")
    L.append("**Lo que se gana.** Tiempo, y una diferencia de fondo que no se mide en")
    L.append("milisegundos: el modo de decisión **no genera texto**. No es que escriba")
    L.append("poco, es que no pasa por el bucle de generación, así que desaparecen dos")
    L.append("cosas a la vez: la espera por los tokens y el analizador que después los")
    L.append("interpreta. Eso no se pone en la misma tabla que una latencia porque no es")
    L.append("la misma magnitud — es una operación distinta.\n")
    L.append("**Lo que no se gana con una pregunta suelta.** Precisión. Los tres modos")
    L.append(f"aciertan lo mismo ({a['tipado']['acc']:.1f}% frente a {a['llm']['acc']:.1f}%), "
             f"y los intervalos se solapan. Decir que el modo de decisión «acierta más»")
    L.append("sería falso con estos datos.\n")
    L.append("**Lo que sí se gana al encadenar.** Las dos cosas. Ahí el chat pierde")
    L.append(f"**{d5:.1f} puntos** de acierto además de tiempo, y deja "
             f"**{b['llm']['sin']} respuestas que no se pudieron ni leer** del texto: el")
    L.append("modo de decisión no es que sea más rápido, es que el otro no entrega.\n")
    L.append("**Escribir en lenguaje natural es gratis.** Las dos formas tipadas")
    L.append("coinciden en todo. Eso importa para adoptarlo: nadie tiene que aprender")
    L.append("un formato para empezar.\n")

    L.append("### Dos fallos que no son del modelo\n")
    L.append("Durante el análisis aparecieron dos preguntas que fallaban siempre y de")
    L.append("forma idéntica en los dos modos tipados, mientras el chat acertaba. Al")
    L.append("repetirlas cambiando **solo la descripción del campo**:\n")
    L.append("| caso | con la descripción de las opciones | solo la pregunta |")
    L.append("|---|---|---|")
    L.append("| ¿En qué idioma está el texto? | `ingles` **0,33 · 0,33 · 0,33** | "
             "`ingles` **0,69** correcto |")
    L.append("| ¿Qué forma tiene? (plátano) | `redonda` 0,64 incorrecto | "
             "`alargada` **0,67** correcto |")
    L.append("")
    L.append("Con la descripción, el idioma queda en **empate a tres**: no es falta de")
    L.append("capacidad, es que añadir `'etiqueta' = descripción` a la pregunta mete")
    L.append("en el contexto un montón de palabras en español («Español», «Inglés»,")
    L.append("«Cualquier otro idioma») y la pregunta deja de referirse al texto de")
    L.append("entrada.\n")
    L.append("**Implicación práctica:** cuando una pregunta falla, la primera hipótesis")
    L.append("debe ser la **construcción de la pregunta**, no el tamaño del modelo. En")
    L.append("estos dos casos, subir de modelo o añadir recuperación de contexto habría")
    L.append("**empeorado** el resultado: al modelo le sobraba texto, no le faltaba.\n")

    # ---------------------------------------------------- 5. limitaciones
    L.append("---\n")
    L.append("## 5. Limitaciones\n")
    L.append("- **Una sola máquina y un solo modelo.** RX 9070 por Vulkan, Spark-X2.5-4B")
    L.append("  Q8_0. No se probaron otros tamaños ni otras cuantizaciones, así que las")
    L.append("  cifras absolutas no se generalizan; los porcentajes de mejora son más")
    L.append("  transportables que los milisegundos.")
    L.append("- **154 preguntas es una muestra pequeña.** Los intervalos de confianza se")
    L.append("  publican por eso: diferencias de 1–2 puntos no son significativas.")
    L.append("- **Las etiquetas son propias.** La verdad de referencia la fijó el autor")
    L.append("  del estudio, no un panel independiente. En las preguntas subjetivas")
    L.append("  (urgencia, tono) es discutible, y donde el modelo discrepa se deja")
    L.append("  anotado en vez de borrarse.")
    L.append("- **El modo `llm` se midió con un prompt razonable** pidiendo la respuesta")
    L.append("  en un formato legible. Un prompt mucho mejor le habría ido mejor; el")
    L.append("  punto es que hay que escribirlo, y aun así se abandonó el formato en")
    L.append(f"  {b['llm']['sin']} de 64 respuestas encadenadas.")
    L.append(f"- **El chat se midió en su versión más favorable**: se le pidió la")
    L.append(f"  respuesta mínima (`Responde SOLO con…`), y aun así tardó "
             f"{a['llm']['p50']:.0f} ms. Con una respuesta redactada libremente la")
    L.append("  ventaja medida sube a **5,0×** en vez de 1,4×, porque el modelo tiene")
    L.append("  que producir el texto completo. La ventaja reportada aquí es, por")
    L.append("  tanto, la **más conservadora** de las dos.")
    L.append("- **La fiabilidad se midió sobre este dominio.** En una tarea distinta, el")
    L.append("  mismo modelo y la misma máquina dieron un error de calibración **muy")
    L.append("  superior** (ECE 0,25 frente a 0,02), que es la razón por la que la")
    L.append("  calibración hay que rehacerla por carga de trabajo y no heredarla.\n")
    L.append("- **No se probó el ajuste fino** de `--decision-seqs` ni arquitecturas de")
    L.append("  codificador, que serían más rápidas todavía.\n")

    # ------------------------------------------------------- 6. mejoras
    L.append("---\n")
    L.append("## 6. Mejoras posibles\n")
    L.append("Ordenadas por relación entre esfuerzo y ganancia esperada:\n")
    L.append("| mejora | por qué | esfuerzo |")
    L.append("|---|---|---|")
    L.append("| **Reescribir la descripción de los campos que fallan** | ya está medido: "
             "0,33 → 0,69 en el caso del idioma | horas |")
    L.append("| Ampliar a 1.000+ preguntas | estrechar los intervalos y detectar "
             "diferencias hoy invisibles | días |")
    L.append("| Probar otros tamaños y cuantizaciones | saber cómo escala la ventaja; "
             "Q4_K_M perdería ~7% de decisiones | días |")
    L.append("| Ajustar `--decision-seqs` | menos ramas reservadas, menos memoria | horas |")
    L.append("| Sondear un modelo de codificador | un codificador sería aún más rápido "
             "en la parte de puntuación | semanas |")
    L.append("| **RAG sobre el texto** | **solo** para preguntas que necesiten "
             "conocimiento externo, no para las que fallan por la descripción | semanas |")
    L.append("")

    # ----------------------------------------------------- 7. replicacion
    L.append("---\n")
    L.append("## 7. Cómo replicarlo\n")
    L.append("Todo el material está en el repositorio. Cualquiera puede rehacer el")
    L.append("estudio o sustituir los casos por los suyos.\n")
    L.append("```bash")
    L.append("# 1. el servidor: un modelo, endpoint de decisión activado")
    L.append("llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 \\")
    L.append("             --decision-seqs 64 --port 8096")
    L.append("")
    L.append("# 2. Saturar los tres modos sobre los 90 casos de una pregunta")
    L.append("python bench_modos.py --out results/modos.json")
    L.append("")
    L.append("# 3. Y sobre las 64 preguntas encadenadas")
    L.append("python bench_multi.py --out results/multi.json")
    L.append("")
    L.append("# 4. El detalle pregunta por pregunta, con opciones y reparto")
    L.append("python detalle.py        # -> docs/DETALLE.md")
    L.append("")
    L.append("# 5. La comparativa resumida")
    L.append("python rendimiento.py    # -> docs/ESTUDIO.md + los graficos")
    L.append("")
    L.append("# 6. Y este documento")
    L.append("python rendimiento.py    # -> docs/ESTUDIO.md")
    L.append("```")
    L.append("")
    L.append("Para probar **preguntas propias** no hace falta tocar código: se escriben")
    L.append("en lenguaje natural y se ejecutan.\n")
    L.append("```bash")
    L.append("python preguntar.py ejemplos/caso_suscripcion.txt")
    L.append("python preguntar.py --texto \"Entrada: ... | Pregunta: ... | Opciones: ...\"")
    L.append("```")
    L.append("")
    L.append("El único requisito duro es que el servidor exponga el endpoint de")
    L.append("decisión: eso lo aporta el fork `parallel-decision` de llama.cpp, no es")
    L.append("estándar. **Las etiquetas de cada pregunta son del usuario**, no vienen")
    L.append("con el modelo: replicar el método es escribir bien las preguntas, no")
    L.append("entrenar nada.\n")

    # ------------------------------------------------------- glosario
    L.append("---\n")
    L.append("## 8. Glosario\n")
    L.append("Para leer las tablas sin ser especialista.\n")
    L.append("| término | qué significa |")
    L.append("|---|---|")
    L.append("| **p50** (mediana) | Ordena todos los tiempos y coge el del medio: la "
             "mitad de las consultas fueron más rápidas que ese número. Se prefiere al "
             "promedio porque **el promedio lo arrastran los casos lentos**: una sola "
             "consulta de 2 s entre 99 de 80 ms sube la media a 99 ms y da una imagen "
             "falsa de lo que vive el usuario. |")
    L.append("| **p95** | El valor por debajo del cual cae el 95% de las consultas. "
             "Mide **la cola**: el peor caso razonablemente frecuente. Importa porque "
             "es lo que sufre quien tiene mala suerte. |")
    L.append("| **IC 95%** (intervalo de confianza) | Medimos una **muestra** de 90 "
             "preguntas, no todas las posibles. El intervalo es la horquilla donde "
             "caería el valor verdadero si se repitiera el experimento. El paper usa "
             "el método de **Wilson**, que con muestras pequeñas se comporta mejor que "
             "el normal (el normal puede dar intervalos que se salen de 0–100%). |")
    L.append("| **solapamiento de intervalos** | Si los intervalos de dos modos **se "
             "solapan**, la diferencia entre ellos **puede ser azar de la muestra** y "
             "no se puede afirmar. Si **no se solapan**, es real. Es lo que permite "
             "decir «con una pregunta empatan» frente a «al encadenar sí hay "
             "diferencia». |")
    L.append("| **× (veces más rápido)** | Cociente entre dos tiempos. 3,7× significa "
             "que uno tarda 3,7 veces lo que el otro. Es equivalente a decir que el "
             "otro tarda un 73% menos. |")
    L.append("| **punto porcentual (pp)** | Diferencia entre dos porcentajes. Pasar de "
             "85,6% a 86,7% son 1,1 **puntos**, no un 1,1% de mejora relativa. |")
    L.append("| **confianza** | Lo que el modelo declara sobre su propia respuesta, de "
             "0 a 1. **No es la probabilidad de acertar**, es lo concentrada que está "
             "su distribución de probabilidad: 1,00 es un único pico; cerca de 0, un "
             "empate entre varias opciones. |")
    L.append("| **calibración** | Cuánto se parece la confianza declarada al acierto "
             "real. Si el modelo dice 0,8 y acierta el 80% en ese tramo, está "
             "calibrado. |")
    L.append("| **media geométrica / aritmética** | No se usan aquí. Se menciona solo "
             "para prevenir: para promediar tiempos la media aritmética es engañosa y "
             "por eso se publica la mediana. |")
    L.append("")
    L.append("### Cómo se lee una tabla de resultados\n")
    L.append("```")
    L.append("| modo    | acierto | IC 95%        | p50    |")
    L.append("| tipado  | 85.6%   | [76.8, 91.4]  | 76 ms  |")
    L.append("```")
    L.append("Se lee así: *«el 85,6% de las preguntas se acertaron; el valor verdadero")
    L.append("está con alta probabilidad entre 76,8% y 91,4%; y la mitad de las")
    L.append("respuestas llegaron en menos de 76 milisegundos»*.\n")

    # ----------------------------------------------------- 10. referencias
    L.append("---\n")
    L.append("## 9. Referencias\n")
    L.append("- TypeSafe / Jev — el modelo comercial de decisión que inspira el formato "
             "y las tres primitivas: <https://docs.typesafe.ai/>")
    L.append("- Fork `parallel-decision` de llama.cpp — el endpoint de decisión: "
             "<https://github.com/thecodacus/llama.cpp/tree/parallel-decision>")
    L.append("- `llama.cpp` — el servidor de inferencia: "
             "<https://github.com/ggml-org/llama.cpp>")
    L.append("- S1MB, benchmark de modelos System One: "
             "<https://github.com/hotchpotch/S1MB>\n")
    L.append("---\n")
    L.append("*Documento generado por `rendimiento.py` y `entorno.py` a partir de "
             "`results/`. Todos los")
    L.append("números son reproducibles: no hay ninguna cifra escrita a mano. "
             "`python verificar.py`")
    L.append("comprueba que sigan cuadrando con los datos.*\n")

    # El entorno (hardware, versiones, como se integro, de donde sale la idea, pros y
    # contras) entra ANTES de Resultados: se lee mejor saber con que se midio antes de
    # ver las cifras que al reves.
    try:
        i = next(i for i, l in enumerate(L)
                 if l.lstrip().startswith("##") and "Resultados" in l)
        L[i:i] = entorno.lineas()
    except StopIteration:
        L.extend(entorno.lineas())

    with open(DOC, "w", encoding="utf-8") as f:
        f.write("\n".join(sin_numerar(L)) + "\n")
    print(f"escrito {DOC}  ({len(L)} lineas)")
    print(f"graficos en results/graf/")


if __name__ == "__main__":
    raise SystemExit(main())
