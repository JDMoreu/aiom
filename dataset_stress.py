# -*- coding: utf-8 -*-
"""
dataset_stress.py — set adversario: donde se rompe el modo decision?

El dataset base esta SATURADO (100% en todos los campos), asi que no puede medir
nada mas. Este set busca los bordes, por categoria, y cada caso lleva la etiqueta
que se espera y por que.

Categorias, de mas facil a mas traicionera:

  distractor    hay un numero que NO es el predio ("el nodo 4 del predio 9")
  implicito     la magnitud no se nombra ("hace mucho calor" -> temperatura)
  negacion      la consulta NIEGA el problema, no lo reporta
  fuera_rango   el predio supera el maximo del esquema (1-12)  <- rompe mi arreglo
  fuera_cat     la magnitud no esta en el catalogo
  multi_predio  se mencionan dos predios: la respuesta unica no existe
  no_resp       pide prosa; debe relevarse a chat
"""


def _c(q, cat, **esp):
    return {"q": q, "cat": cat, "esperado": esp}


CASOS = [
    # ---- distractor: otro numero compite con el predio -----------------------
    _c("el nodo 4 del predio 9 manda lecturas raras", "distractor", magnitud="humedad", predio=9),
    _c("el sensor 7 del predio 3 no reporta temperatura", "distractor", magnitud="temperatura", predio=3),
    _c("en el predio 11 hay 5 nodos sin senal", "distractor", magnitud="senal", predio=11),
    _c("el nodo 2 del predio 8 tiene bateria baja", "distractor", magnitud="bateria", predio=8),
    _c("dos alertas en el predio 6, humedad rara", "distractor", magnitud="humedad", predio=6),
    _c("el gateway 1 del predio 12 se cayo", "distractor", magnitud="senal", predio=12),

    # ---- implicito: la magnitud va implicita en el lenguaje -----------------
    _c("hace mucho calor en el predio 4", "implicito", magnitud="temperatura", predio=4),
    _c("esta muy seco el predio 7", "implicito", magnitud="humedad", predio=7),
    _c("el nodo del predio 2 se queda sin carga", "implicito", magnitud="bateria", predio=2),
    _c("perdimos comunicacion con el predio 5", "implicito", magnitud="senal", predio=5),
    _c("hay que regar el predio 10", "implicito", magnitud="riego", predio=10),

    # ---- negacion: no hay problema ------------------------------------------
    _c("el predio 3 no tiene problemas de humedad", "negacion", magnitud="humedad", predio=3),
    _c("ya se restablecio la senal del predio 8", "negacion", magnitud="senal", predio=8),

    # ---- fuera_rango: predio > 12, el maximo del esquema --------------------
    # El valor correcto de `predio` no existe (esta fuera del contrato), asi que
    # lo unico evaluable es que el sistema DECLARE la invalidez en vez de
    # recortar en silencio a un valor valido.
    _c("el predio 30 lleva dias sin reportar humedad", "fuera_rango",
       magnitud="humedad", predio_valido=False),
    _c("revisen la temperatura del predio 45", "fuera_rango",
       magnitud="temperatura", predio_valido=False),
    _c("el predio 99 manda datos raros", "fuera_rango", predio_valido=False),
    _c("alerta de bateria en el predio 18", "fuera_rango",
       magnitud="bateria", predio_valido=False),

    # ---- fuera_cat: magnitud que el catalogo no cubre -----------------------
    _c("el sensor de viento del predio 2 marca rachas fuertes", "fuera_cat", predio=2),
    _c("como va la calidad del aire en el predio 6", "fuera_cat", predio=6),
    _c("hay plagas en el predio 4", "fuera_cat", predio=4),

    # ---- multi_predio: no hay respuesta unica -------------------------------
    _c("compara la humedad del predio 3 con la del predio 7", "multi_predio", magnitud="humedad"),

    # ---- no_resp: pide prosa ------------------------------------------------
    _c("redactame un informe del predio 5", "no_resp"),
    _c("explicame por que fallan los nodos", "no_resp"),
    _c("que hago para mejorar la senal del predio 3?", "no_resp"),
]


def casos():
    return CASOS


def score(valores, caso):
    """(aciertos, evaluables) solo sobre los campos inequivocos del caso."""
    if not isinstance(valores, dict):
        return 0, len(caso["esperado"])
    ok = sum(1 for k, v in caso["esperado"].items() if str(valores.get(k)) == str(v))
    return ok, len(caso["esperado"])
