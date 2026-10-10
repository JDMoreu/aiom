"""Ejemplo completo: consultar la API de AIOM desde Python.

Es el ejemplo de INTEGRACION: como lo llama otro programa. Se puede copiar y correr.

LOS DOS ENDPOINTS

    POST /documento     los bytes del fichero -> su texto
    POST /ask           el caso y las preguntas -> los valores

Con un DOCUMENTO son DOS llamadas: primero a `/documento` para sacarle el texto, y luego a
`/ask` con ese texto en el campo `documento`. Con el caso escrito es UNA sola: el caso va
dentro de `entrada`, junto a las preguntas. **El endpoint de la pregunta es el mismo en los
dos casos**, que es lo que conviene recordar.

LOS TRES TIPOS DE PREGUNTA

Cada pregunta se declara con su cabecera, y hay tres:

    choice:     elegir UNA de una lista. Devuelve la opcion elegida y la probabilidad de
                TODAS, que es lo que permite ver si el modelo dudo entre dos.
    score:      poner algo en una escala. Devuelve el nivel, y puede caer entre dos.
    noul:       VERDADERO O FALSO. Sus dos valores son `false` y `true` y no se pueden
                anadir mas: solo se cambia que significa cada uno.

Este ejemplo lleva SEIS preguntas, dos de cada tipo, y las resuelve todas en UNA peticion.

LOS TRES FORMATOS DE ENTRADA

`formato` dice como viene la entrada, y NO se adivina:

    natural     el de las cabeceras (`input:`, `ask:`, `choice:`...). Es el de este
                ejemplo, y el mas comodo de escribir a mano.
    tipado      el JSON de TypeSafe: `state.input` + `questions`. Para cuando el que
                llama ya trabaja con esquemas.
    texto       una pregunta suelta, contra los campos de un CATALOGO. Para preguntas
                rapidas sin escribir el esquema.

Para ver el mismo caso en `tipado`, ejecuta este fichero con `--tipado`.

    python ejemplos/integrar.py                     # el caso escrito, en natural
    python ejemplos/integrar.py carta.pdf           # el caso sacado de un documento
    python ejemplos/integrar.py --tipado            # el mismo caso, en JSON tipado
    python ejemplos/integrar.py --comparar          # y ademas, la misma pregunta al chat

Solo usa la biblioteca estandar. No hay nada que instalar.

Antes hace falta el servidor del modelo y la API, en dos terminales:

    llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
    python api.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Donde esta la API. Se cambia sin tocar el codigo: AIOM_SERVER=http://otra:8100
SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8100")

# --------------------------------------------------------------------------- #
# El caso: sobre esto van las preguntas
# --------------------------------------------------------------------------- #
CASO = """Buenas tardes. Escribo porque estoy bastante molesto: contraté el plan de 20 GB
el mes pasado y llevo una semana con cortes de conexión casi todas las noches. He llamado
tres veces y nadie me ha dado una solución. Además me han cobrado dos veces la factura de
este mes. Si esto sigue así me voy a dar de baja."""

# --------------------------------------------------------------------------- #
# Las preguntas: seis, dos de cada tipo
#
# Se separan con una linea de tres guiones. Cada una empieza por su cabecera, que declara
# el tipo: no se adivina. Debajo, los criterios: lo que significa cada opcion.
# --------------------------------------------------------------------------- #
PREGUNTAS = """ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas, planes y bajas
  otros: Todo lo demás

---

ask: ¿Quién debería responderlo?
choice:
  un agente: Basta con el equipo de siempre
  un supervisor: Conviene que lo vea alguien con más margen

---

ask: ¿Qué urgencia tiene?
score:
  Baja: puede esperar
  Media: conviene atenderlo esta semana
  Alta: hay una fecha límite encima

---

ask: ¿Cómo de molesto está el cliente?
score:
  tranquilo: Lo cuenta sin más
  molesto: Se le nota el enfado
  furioso: Amenaza con irse

---

ask: ¿El cliente ya pagó el plan anual?
noul:
  false: No ha pagado todavía
  true: Sí, ya lo pagó

---

ask: ¿Menciona una fecha límite?
noul:
  false: No hay ninguna fecha
  true: Sí, hay una fecha que corre"""

# --------------------------------------------------------------------------- #
# La misma cosa en el formato tipado. Se usa con --tipado.
#
# Es el formato de TypeSafe: `state.input` con el caso y `questions` con un objeto por
# pregunta. `type` es el tipo, `instructions` el enunciado, y `criteria` los criterios.
# En un `noul` los criterios son `true` y `false`, y no se pueden anadir mas.
# --------------------------------------------------------------------------- #
PREGUNTAS_TIPADO = {
    "state": {"input": CASO},
    "questions": {
        "q1": {"type": "choice",
               "instructions": "¿A qué área hay que enviar este correo?",
               "criteria": {"soporte": "Fallos y errores del producto",
                            "facturacion": "Cobros, facturas y reembolsos",
                            "comercial": "Ventas, planes y bajas",
                            "otros": "Todo lo demás"}},
        "q2": {"type": "choice",
               "instructions": "¿Quién debería responderlo?",
               "criteria": {"un agente": "Basta con el equipo de siempre",
                            "un supervisor": "Conviene que lo vea alguien con más margen"}},
        "q3": {"type": "score",
               "instructions": "¿Qué urgencia tiene?",
               "criteria": ["Baja: puede esperar",
                            "Media: conviene atenderlo esta semana",
                            "Alta: hay una fecha límite encima"]},
        "q4": {"type": "score",
               "instructions": "¿Cómo de molesto está el cliente?",
               "criteria": ["tranquilo: Lo cuenta sin más",
                            "molesto: Se le nota el enfado",
                            "furioso: Amenaza con irse"]},
        "q5": {"type": "noul",
               "instructions": "¿El cliente ya pagó el plan anual?",
               "criteria": {"false": "No ha pagado todavía",
                            "true": "Sí, ya lo pagó"}},
        "q6": {"type": "noul",
               "instructions": "¿Menciona una fecha límite?",
               "criteria": {"false": "No hay ninguna fecha",
                            "true": "Sí, hay una fecha que corre"}},
    },
}


# --------------------------------------------------------------------------- #
# Hablar con la API
# --------------------------------------------------------------------------- #
def pedir(ruta, cuerpo, cabeceras=None):
    """Una peticion a la API. Devuelve el JSON de la respuesta, ya leido.

    `cuerpo` puede ser un dict -se manda como JSON- o bytes, que es como espera los
    ficheros POST /documento.
    """
    datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(SERVIDOR + ruta, data=datos, method="POST")
    peticion.add_header("Content-Type", "application/json")
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    with urllib.request.urlopen(peticion, timeout=300) as r:
        return json.load(r)


def texto_del_documento(ruta):
    """Sube un fichero a POST /documento y devuelve su texto.

    El cuerpo son los BYTES del fichero, en crudo, y el nombre va en la cabecera
    `X-Nombre`: de la extension sale como se lee. No se adivina por el contenido, porque
    un .docx y un .zip empiezan igual.

    Devuelve el texto y, ademas, lo que hay que saber de el: cuantos caracteres, cuantas
    palabras, cuantas paginas -solo en PDF, que es donde ese dato es real-, y un `aviso`
    si hubo paginas que no se pudieron leer.
    """
    with open(ruta, "rb") as f:
        datos = f.read()
    return pedir("/documento", datos, cabeceras={
        "Content-Type": "application/octet-stream",
        "X-Nombre": os.path.basename(ruta)})


# --------------------------------------------------------------------------- #
# Enseñar la respuesta
# --------------------------------------------------------------------------- #
def mostrar(respuesta):
    """Imprime la respuesta campo por campo, diciendo que es cada uno.

    `POST /ask` devuelve esto:

        formato         el que se mando, tal cual
        n_preguntas     cuantas preguntas se resolvieron
        tiempo_ms       lo que se tardo, de ida y vuelta. El MISMO reloj en las dos vias
        tokens          0 en decision: no se genera ni un token
        resultados      una entrada por pregunta, con estos campos:

            campo          el nombre del campo (q1, q2...)
            tipo           choice | score | noul
            pregunta       el enunciado, para no tener que recordarlo
            value          LO QUE RESPONDE. Es el dato
            probability    la probabilidad de ESE valor
            probabilities  la de TODAS las opciones: aqui se ve si dudo entre dos
            confidence     la confianza de la lectura entera
            niveles        solo en un score: la etiqueta de cada nivel, para que un
                           numero suelto signifique algo
    """
    print(f"   formato: {respuesta['formato']}   "
          f"{respuesta['n_preguntas']} preguntas   "
          f"{round(respuesta['tiempo_ms'])} ms   "
          f"{respuesta['tokens']} tokens")
    print()

    for r in respuesta["resultados"]:
        print(f"   [{r['tipo']}] {r['pregunta']}")
        print(f"       {r['campo']} = {r['value']!r}   "
              f"(probabilidad {r['probability']:.3f}, confianza {r['confidence']:.3f})")
        if r.get("probabilities"):
            # La distribucion entera: es lo que deja ver una duda.
            reparto = ", ".join(f"{k} {v:.2f}" for k, v in
                                sorted(r["probabilities"].items(),
                                       key=lambda x: -x[1]))
            print(f"       reparto: {reparto}")
        if r.get("niveles"):
            print(f"       niveles: {' | '.join(r['niveles'])}")
        print()


def mostrar_comparacion(comparacion):
    """Imprime las dos vias, que es lo unico que se mide aqui.

    Con `"comparar": true`, `/ask` resuelve la misma pregunta por las DOS vias -decision y
    chat- en la misma corrida, para que los tiempos sean del mismo momento. La decision
    contesta por preguntas; el chat contesta todo de una vez, porque asi se le pregunta a
    un asistente.
    """
    d, c = comparacion["decision"], comparacion["chat"]
    print(f"   decision: {d['peticiones']} peticion  "
          f"{round(d['tiempo_ms'])} ms  {d['tokens']} tokens")
    print(f"   chat:     {c['peticiones']} peticion  "
          f"{round(c['tiempo_ms'])} ms  {c['tokens']} tokens")
    veces = c["tiempo_ms"] / max(d["tiempo_ms"], 1)
    print(f"   el chat tardo {veces:.1f} veces mas")
    print()
    print("   --- lo que respondio el chat, entero ---")
    for linea in (c["resultados"][0].get("texto") or "").splitlines():
        print("   ", linea)


# --------------------------------------------------------------------------- #
# Los tres caminos
# --------------------------------------------------------------------------- #
def con_documento(ruta, comparar):
    """El caso sale de un fichero: primero /documento, y luego /ask."""
    print(f"1. Subiendo '{os.path.basename(ruta)}' a POST /documento")
    documento = texto_del_documento(ruta)
    cifras = [f"{documento['caracteres']} caracteres",
              f"{documento['palabras']} palabras",
              f"{documento['lineas']} lineas"]
    if documento.get("paginas"):
        # Las paginas solo se informan en un PDF: en un .txt no hay hasta que se maqueta.
        cifras.append(f"{documento['paginas']} paginas")
        cifras.append(f"{documento['paginas_con_texto']} con texto propio")
        if documento.get("paginas_con_ocr"):
            cifras.append(f"{documento['paginas_con_ocr']} leidas con OCR")
        if documento.get("paginas_ilegibles"):
            cifras.append(f"{documento['paginas_ilegibles']} ilegibles")
    print("   ->", ", ".join(cifras))
    if documento.get("aviso"):
        # El aviso no es decoracion: dice de donde sale el texto y que puede faltar.
        print("   aviso:", documento["aviso"])
    # El texto extraido entra como `documento`, y MANDA sobre el `input:` de la entrada.
    return {"formato": "natural", "entrada": PREGUNTAS,
            "documento": documento["texto"], "comparar": comparar}


def con_texto(comparar):
    """El caso va escrito: todo junto en `entrada`, y una sola llamada."""
    return {"formato": "natural", "entrada": f"input: {CASO}\n\n{PREGUNTAS}",
            "comparar": comparar}


def con_tipado(comparar):
    """El mismo caso en el JSON de TypeSafe. Aqui el caso va en `state.input`."""
    return {"formato": "tipado", "comparar": comparar, **PREGUNTAS_TIPADO}


# --------------------------------------------------------------------------- #
def correr():
    args = sys.argv[1:]
    comparar = "--comparar" in args
    tipado = "--tipado" in args
    rutas = [a for a in args if not a.startswith("--")]

    if tipado:
        print("1. El caso va en `state.input` y las preguntas en `questions` (tipado)")
        cuerpo = con_tipado(comparar)
    elif rutas:
        cuerpo = con_documento(rutas[0], comparar)
    else:
        print("1. Sin documento: el caso va escrito dentro de `entrada`")
        cuerpo = con_texto(comparar)

    print("2. Preguntando a POST /ask")
    respuesta = pedir("/ask", cuerpo)
    print()

    if comparar:
        mostrar_comparacion(respuesta)
    else:
        mostrar(respuesta)
        print("   Para ver tambien lo que contestaria el chat, anade --comparar.")


def main():
    try:
        return correr()
    except urllib.error.HTTPError as e:
        # La API contesta con el motivo: un 400 dice que falta, un 502 que el modelo
        # fallo. Se enseña tal cual, sin adornarlo.
        print(f"la API contesto {e.code}: {e.read()[:400].decode('utf-8', 'replace')}",
              file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        # Aqui no hay API al otro lado. Es el fallo mas comun al empezar, asi que se dice
        # que falta y como levantarlo, en vez de soltar el traceback de urllib.
        print(f"no puedo hablar con la API en {SERVIDOR} ({e.reason})", file=sys.stderr)
        print("esta levantada? en otra terminal:  python api.py", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"no puedo leer el fichero: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
