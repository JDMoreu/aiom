# -*- coding: utf-8 -*-
"""
dataset.py — conjunto de consultas etiquetadas para el benchmark de AIOM.

Por que etiquetado: comparar latencias sin comprobar el acierto es enganarse.
Un modo que responde en 60 ms pero se equivoca en el campo `predio` no es
"mas rapido", es peor. Cada consulta lleva SOLO los campos cuyo valor esperado
es inequivoco; los ambiguos se omiten y no se puntuan.

  respondible  True  -> se puede contestar con el catalogo
               False -> pide redactar, explicar u opinar: debe relevarse a chat
"""

# Preguntas respondibles con el catalogo (operador de campo).
RESPONDIBLES = [
    # (consulta, magnitud, predio, urgencia)   urgencia None = ambigua, no se puntua
    ("el sensor del predio 3 lleva dos dias sin reportar temperatura, revisen ya", "temperatura", 3, "alta"),
    ("cuanta humedad promedio tuvimos en el predio 7 la semana pasada?",           "humedad",     7, "baja"),
    ("como va la bateria de los nodos del predio 2",                               "bateria",     2, None),
    ("se cayo la senal en el predio 11, es grave",                                 "senal",      11, "alta"),
    ("el nodo 4 del predio 9 manda lecturas raras de humedad",                     "humedad",     9, "alta"),
    ("revisen la temperatura del predio 1, esta muy alta",                         "temperatura", 1, "alta"),
    ("cuanta agua se aplico en el riego del predio 5?",                            "riego",       5, None),
    ("la bateria del predio 12 esta por debajo del veinte por ciento",             "bateria",    12, "alta"),
    ("hay perdida de senal en el predio 6?",                                       "senal",       6, None),
    ("dame la humedad del predio 4",                                               "humedad",     4, "baja"),
    ("el predio 8 no reporta desde ayer, se perdio la senal",                      "senal",       8, "alta"),
    ("como estuvo el riego en el predio 10 esta semana",                           "riego",      10, None),
    ("alerta por temperatura en el predio 2",                                      "temperatura", 2, "alta"),
    ("cuanta bateria le queda al nodo del predio 3",                               "bateria",     3, None),
    ("promedio de humedad del predio 12 del ultimo mes",                           "humedad",    12, "baja"),
    ("temperaturas registradas en el predio 6 durante la madrugada",               "temperatura", 6, None),
    ("el riego del predio 9 no arranco esta manana",                               "riego",       9, "alta"),
    ("la senal del predio 1 va intermitente",                                      "senal",       1, None),
    ("bateria critica en el predio 5, cambienla",                                  "bateria",     5, "alta"),
    ("necesito el historico de temperatura del predio 11",                         "temperatura",11, "baja"),
]

# Preguntas NO respondibles: piden lenguaje natural. Deben relevarse a chat.
NO_RESPONDIBLES = [
    "redactame un informe para el cliente sobre el estado de la red",
    "explicame por que se descargan tan rapido las baterias de los nodos",
    "que me recomiendas para mejorar el rendimiento de toda la red?",
    "escribeme un correo para el proveedor de los nodos",
    "cual es la mejor epoca del ano para sembrar maiz en esta region?",
    "resumeme en un parrafo el historial de mantenimiento del ultimo ano",
]


def cases():
    """Devuelve [{q, respondible, esperado:{...}}] listo para puntuar."""
    out = []
    for q, mag, predio, urg in RESPONDIBLES:
        esperado = {"magnitud": mag, "predio": predio}
        if urg is not None:
            esperado["urgencia"] = urg
        out.append({"q": q, "respondible": True, "esperado": esperado})
    for q in NO_RESPONDIBLES:
        out.append({"q": q, "respondible": False, "esperado": {}})
    return out


def score(values: dict, case: dict) -> tuple[int, int]:
    """(aciertos, evaluables) sobre los campos inequivocos del caso."""
    if not isinstance(values, dict):
        return 0, len(case["esperado"])
    ok = sum(1 for k, v in case["esperado"].items() if str(values.get(k)) == str(v))
    return ok, len(case["esperado"])
