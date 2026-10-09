"""El formato tipado: la peticion con su esquema dentro.

Acepta el formato de TypeSafe tal cual -- `state.input` + `questions.decision` con
`type`, `instructions` y `criteria` -- lo traduce a lo que come el servidor local, y
devuelve la respuesta.

El mapeo, que es lo unico que hay que entender, y la idea entera del proyecto:

    TypeSafe                          aqui
    ------------------------------    ------------------------------------------
    state.input                       contexts[0]  (el estado)
    questions.decision.instructions   el `description` del campo
    type: choice + criteria {id: txt} type: enum, choices = las claves de criteria
    type: score  + criteria [niveles] type: number, rejilla 0..n-1
    type: noul   + criteria {t,f}     type: boolean

No hay nada que entrenar ni que cambiar del modelo: es el MISMO modelo, y lo unico que
cambia es como se le da la entrada y que se espera de la salida.
"""

import json
import time
import urllib.request

import aiom  # noqa: F401  (el servidor y los tiempos salen de aqui)


def traducir(peticion):
    """Devuelve (estado, esquema) listo para /v1/decision.

    TypeSafe agrupa las preguntas en `questions: {id: {type, instructions, criteria}}`,
    y ese diccionario puede llevar VARIAS. Cada una pasa a ser un campo del esquema,
    asi que N preguntas se resuelven en UNA sola peticion.

    Los `criteria` se convierten segun el tipo:

        choice  {id: descripcion}  -> enum con choices = ids
        score   [nivel0, nivel1…]  -> rejilla numerica 0..n-1, el nivel i vale i
        noul    {true: …, false: …} -> booleano, con el significado en el enunciado
    """
    estado = peticion["state"]["input"] if isinstance(peticion["state"], dict) \
        else peticion["state"]

    esquema = {}
    for nombre, pregunta in peticion["questions"].items():
        tipo = pregunta["type"]
        instrucciones = pregunta["instructions"]
        criterios = pregunta.get("criteria")
        if tipo not in aiom.AL_MOTOR:
            raise ValueError(
                f"tipo '{tipo}' desconocido. "
                f"Los tipos son: {', '.join(sorted(aiom.AL_MOTOR))}")

        if tipo == "choice":
            # {id: descripcion} -> choices = ids, y las descripciones al enunciado
            opciones = list(criterios.keys())
            detalle = " ".join(f"'{k}' = {v}." for k, v in criterios.items())
            campo = {"type": aiom.AL_MOTOR[tipo], "choices": opciones,
                     "description": f"{instrucciones} {detalle}"}

        elif tipo == "score":
            # [nivel0, nivel1, ...] -> rejilla numerica 0..n-1, el nivel i vale i
            n = len(criterios)
            detalle = " ".join(f"{i} = {t}." for i, t in enumerate(criterios))
            campo = {"type": aiom.AL_MOTOR[tipo], "minimum": 0, "maximum": n - 1,
                     "step": 1,
                     "description": f"{instrucciones} Niveles, de menor a mayor: {detalle}"}

        elif tipo == "noul":
            # {true: ..., false: ...} -> booleano, con el significado en el enunciado
            v = criterios.get("true", "") if criterios else ""
            f = criterios.get("false", "") if criterios else ""
            detalle = f"true = {v}. false = {f}." if criterios else ""
            campo = {"type": aiom.AL_MOTOR[tipo],
                     "description": f"{instrucciones} {detalle}"}

        else:
            raise ValueError(f"tipo desconocido: {tipo}")

        esquema[nombre] = campo

    if not esquema:
        raise ValueError("'questions' esta vacio")
    return estado, esquema


def ejecutar(peticion, timeout=120, servidor=None):
    """Manda la peticion traducida y devuelve (respuesta cruda, milisegundos)."""
    estado, esquema = traducir(peticion)
    payload = {"instructions": "Respondes solo con los valores del esquema.",
               "schema": esquema, "contexts": [estado]}
    base = (servidor or aiom.DEFAULTS["server"]).rstrip("/")
    req = urllib.request.Request(
        base + "/v1/decision",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cuerpo = json.loads(resp.read().decode("utf-8"))
    return cuerpo, (time.perf_counter() - t0) * 1000.0
