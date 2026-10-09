"""Los tres ejemplos de TypeSafe, en su formato, ejecutados contra el modelo local.

Acepta el formato de TypeSafe tal cual -- `state.input` + `questions.decision` con
`type`, `instructions` y `criteria` -- lo traduce a lo que come el servidor local, y
devuelve la respuesta. Los tres casos son CHOICE, SCORE y PROBABILITY (que TypeSafe
llama `noul`).

    python ejemplos_typesafe.py            # los tres, en codigo y en lenguaje natural
    python ejemplos_typesafe.py --json     # la respuesta cruda del servidor

El mapeo, que es lo unico que hay que entender:

    TypeSafe                          aqui
    ------------------------------    ------------------------------------------
    state.input                       contexts[0]  (el estado)
    questions.decision.instructions   el `description` del campo
    type: choice + criteria {id: txt} type: enum, choices = las claves de criteria
    type: score  + criteria [niveles] type: number, rejilla 0..n-1
    type: noul   + criteria {t,f}     type: boolean
"""

import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aiom  # noqa: E402

SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096")


# --------------------------------------------------------------------------- #
# Los tres casos, en el formato de TypeSafe, copiados de su documentacion.
# Al pie de cada uno, como se ve en lenguaje natural.
# --------------------------------------------------------------------------- #
CASOS = [
    {
        "id": "choice",
        "code": {
            "model": "typesafe/jev-1.13",
            "state": {"input": "Me cobraron dos veces la suscripción. ¿Pueden ayudarme?"},
            "questions": {
                "decision": {
                    "type": "choice",
                    "instructions": "¿Qué equipo debe atenderlo?",
                    "criteria": {
                        "billing": "Pagos y reembolsos",
                        "technical": "Errores e integraciones",
                        "general": "Otras consultas",
                    },
                }
            },
        },
    },
    {
        "id": "score",
        "code": {
            "model": "typesafe/jev-1.13",
            "state": {"input": "Búsqueda: zapatillas de senderismo ligeras para días de lluvia. "
                               "Resultado: una ficha de zapatillas de trail impermeables con "
                               "guía de tallas y reseñas."},
            "questions": {
                "decision": {
                    "type": "score",
                    "instructions": "¿Qué relevancia tiene este elemento para la solicitud?",
                    "criteria": ["No relevante", "Algo relevante", "Muy relevante"],
                }
            },
        },
    },
    {
        "id": "probability",
        "code": {
            "model": "typesafe/jev-1.13",
            "state": {"input": "Son las 22:30. Una aplicación de calendario quiere recordar una "
                               "comida de equipo prevista para el próximo viernes. El usuario "
                               "tiene activado el horario de descanso hasta las 07:00."},
            "questions": {
                "decision": {
                    "type": "noul",
                    "instructions": "¿Debe esperar esta notificación hasta que termine el "
                                    "horario de descanso?",
                    "criteria": {
                        "false": "El recordatorio es urgente y debe enviarse ahora",
                        "true": "Puede enviarse después sin perjudicar al usuario",
                    },
                }
            },
        },
    },
]


# --------------------------------------------------------------------------- #
# traductor: formato TypeSafe -> peticion del servidor local
# --------------------------------------------------------------------------- #
def traducir(peticion):
    """Devuelve (estado, nombre_del_campo, esquema) listo para /v1/decision.

    TypeSafe agrupa todo en UNA pregunta con `criteria`. El servidor local pide un
    esquema de campos `{nombre: {type, description, ...}}`, asi que se construye uno
    de un solo campo, y la pregunta de TypeSafe pasa a ser la `description` de ese
    campo. Los `criteria` se convierten segun el tipo.
    """
    estado = peticion["state"]["input"] if isinstance(peticion["state"], dict) \
        else peticion["state"]

    (nombre, pregunta), = peticion["questions"].items()
    tipo = pregunta["type"]
    instrucciones = pregunta["instructions"]
    criterios = pregunta.get("criteria")

    if tipo == "choice":
        # {id: descripcion} -> choices = ids, y las descripciones al enunciado
        opciones = list(criterios.keys())
        detalle = " ".join(f"'{k}' = {v}." for k, v in criterios.items())
        campo = {"type": "enum", "choices": opciones,
                 "description": f"{instrucciones} {detalle}"}

    elif tipo == "score":
        # [nivel0, nivel1, ...] -> rejilla numerica 0..n-1, el nivel i vale i
        n = len(criterios)
        detalle = " ".join(f"{i} = {t}." for i, t in enumerate(criterios))
        campo = {"type": "number", "minimum": 0, "maximum": n - 1, "step": 1,
                 "description": f"{instrucciones} Niveles, de menor a mayor: {detalle}"}

    elif tipo == "noul":
        # {true: ..., false: ...} -> booleano, con el significado en el enunciado
        v = criterios.get("true", "") if criterios else ""
        f = criterios.get("false", "") if criterios else ""
        detalle = f"true = {v}. false = {f}." if criterios else ""
        campo = {"type": "boolean", "description": f"{instrucciones} {detalle}"}

    else:
        raise ValueError(f"tipo desconocido: {tipo}")

    return estado, nombre, {nombre: campo}


def ejecutar(peticion, timeout=120):
    """Manda la peticion traducida y devuelve la respuesta cruda del servidor."""
    estado, nombre, esquema = traducir(peticion)
    payload = {"instructions": "Respondes solo con los valores del esquema.",
               "schema": esquema, "contexts": [estado]}
    req = urllib.request.Request(
        SERVIDOR.rstrip("/") + "/v1/decision",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cuerpo = json.loads(resp.read().decode("utf-8"))
    return cuerpo, (time.perf_counter() - t0) * 1000.0, nombre


# --------------------------------------------------------------------------- #
# presentacion
# --------------------------------------------------------------------------- #
ANCHO = 30


def barra(p):
    n = int(round(p * ANCHO))
    return "#" * n + "." * (ANCHO - n)


def en_codigo(caso):
    print(json.dumps(caso["code"], ensure_ascii=False, indent=2))


def en_lenguaje_natural(caso):
    """El mismo caso, escrito como se lo dirias a una persona."""
    p = caso["code"]
    q = p["questions"]["decision"]
    print(f"input:\n  {p['state']['input']}\n")
    print(f"ask:\n  {q['instructions']}\n")

    if q["type"] == "choice":
        print("choice:")
        for k, v in q["criteria"].items():
            print(f"  {k}: {v}")
    elif q["type"] == "score":
        print("score:")
        for t in q["criteria"]:
            print(f"  {t}")
    else:
        print("boolean:")
        for k in ("false", "true"):
            print(f"  {k}: {q['criteria'][k]}")


def respuesta(caso, nombre, cuerpo, ms):
    campos = cuerpo["results"][0]["fields"][nombre]
    print(f"RESPUESTA del modelo local   ({ms:.0f} ms, 0 tokens)")
    print()

    dist = campos.get("probabilities") or {}
    valor = campos["value"]

    if caso["id"] == "choice":
        for k, p in sorted(dist.items(), key=lambda kv: -kv[1]):
            marca = " <-" if k == valor else ""
            print(f"  {k:<12} {p:6.3f}  {barra(p)}{marca}")
    elif caso["id"] == "score":
        for k, p in sorted(dist.items(), key=lambda kv: float(kv[0])):
            marca = " <-" if float(k) == float(valor) else ""
            print(f"  nivel {float(k):<5.0f} {p:6.3f}  {barra(p)}{marca}")
        # la puntuacion de TypeSafe: cada nivel por su probabilidad, sumado
        punt = sum(float(k) * float(p) for k, p in dist.items())
        print(f"\n  puntuación = {punt:.2f}   (0 = no relevante, 2 = muy relevante)")
    else:
        for k, p in sorted(dist.items(), key=lambda kv: -kv[1]):
            etiqueta = "sí " if k == "true" else "no "
            marca = " <-" if k == valor else ""
            print(f"  {etiqueta} {p:6.3f}  {barra(p)}{marca}")
        print(f"\n  probabilidad de que sí = {dist.get('true', 1 - campos['probability']):.3f}")

    print(f"\n  confianza = {campos.get('confidence', float('nan')):.3f}"
          f"   (0 = repartida, 1 = un solo valor claro)")


def main():
    ap = argparse.ArgumentParser(prog="ejemplos_typesafe")
    ap.add_argument("--json", action="store_true", help="respuesta cruda del servidor")
    ap.add_argument("--solo", choices=[c["id"] for c in CASOS],
                    help="ejecuta solo uno de los tres")
    a = ap.parse_args()

    elegidos = [c for c in CASOS if not a.solo or c["id"] == a.solo]

    for caso in elegidos:
        print()
        print("=" * 78)
        print(f"  {caso['id'].upper()}")
        print("=" * 78)

        print("\n--- modo código (lo que le mandarías al modelo) ---\n")
        en_codigo(caso)

        print("\n--- el mismo caso, en lenguaje natural ---\n")
        en_lenguaje_natural(caso)

        print()
        try:
            cuerpo, ms, nombre = ejecutar(caso["code"])
        except Exception as e:                                    # noqa: BLE001
            print(f"ERROR al ejecutar: {type(e).__name__}: {e}")
            continue

        if a.json:
            print(json.dumps(cuerpo, ensure_ascii=False, indent=2))
        else:
            respuesta(caso, nombre, cuerpo, ms)

    print()
    print("=" * 78)
    print("  Los tres son el mismo modelo: solo cambia el tipo de la pregunta.")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
