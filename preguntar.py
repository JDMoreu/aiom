"""El analizador del formato natural: texto con cabeceras -> esquema.

Aqui NO hay linea de comandos: esta es la pieza que usa la API. El .txt se escribe asi:

    input: Buenas tardes. Contrate el plan de 20 GB y llevo una semana con cortes.

    ask: A que area hay que enviar este correo?
    choice:
      soporte: Fallos y errores del producto
      facturacion: Cobros, facturas y reembolsos

El tipo se DECLARA con la cabecera: `choice` elige de una lista, `score` pone algo en una
escala y `noul` es verdadero o falso. `score` va de menor a mayor y se numera desde 0, y
`noul` escribe primero el significado de false y luego el de true.

Varias preguntas se separan con una linea de ---, y se mandan TODAS en una sola peticion.

Dos puertas lo usan: `POST /ask` con formato `natural`, y la interfaz web. El manual del
formato, con un ejemplo de cada tipo, esta en docs/MANUAL.md.
"""

import json
import os
import re
import time
import urllib.request

SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096")

# Los titulos que reconoce. Se aceptan varias formas para no obligar a recordar una.
#
# La forma ESTANDAR es la corta: input / ask / choice / score / boolean. Con ella el
# tipo se DECLARA (choice, score, boolean) en vez de deducirse de que seccion aparezca,
# que es mas facil de explicar y de leer. Las formas largas en espanol se siguen
# aceptando como alias, para no romper nada de lo ya escrito.
TITULOS = {
    "entrada": ("input", "entrada", "estado", "state", "contexto"),
    "pregunta": ("ask", "pregunta", "instrucciones", "pregunta / instrucciones",
                 "question"),
    "opciones": ("choice", "opciones", "choices", "criterios"),
    "niveles": ("score", "niveles", "niveles de puntuación", "niveles de puntuacion",
                "escala", "niveles de score"),
    # El tipo es verdadero o falso, pero aqui se aceptan tambien las formas en
    # espanol ("si o no", "que significa no o si"...) por COMPATIBILIDAD: quien ya
    # tenga ficheros escritos con esas cabeceras no tiene por que cambiarlos.
    "sino": ("noul", "boolean", "qué significa no o sí", "que significa no o si",
             "no o sí", "no o si", "significado", "sí o no", "si o no"),
}


def _titulo_de(linea):
    """Si la linea abre una seccion conocida, devuelve (clave, resto).

    Admite el titulo solo ("choice:") y el titulo con contenido en la misma linea
    ("ask: ¿Que equipo debe atenderlo?"), que es como se escribe naturalmente.

    Exige que empiece en la columna 0: el contenido de una seccion va sangrado, y sin
    esta condicion una opcion llamada "pregunta:" o "estado:" se confundiria con una
    cabecera. Paso de verdad: las opciones de "que quiere el usuario" eran pregunta,
    queja y peticion, y "pregunta" se comia la seccion entera.
    """
    if linea[:1].isspace():
        return None
    m = re.match(r"^([A-Za-zÁÉÍÓÚÜáéíóúüÑñ /]+?)\s*:\s*(.*)$", linea)
    if not m:
        return None
    etiqueta = m.group(1).strip().lower()
    for clave, formas in TITULOS.items():
        if etiqueta in formas:
            return clave, m.group(2).strip()
    return None


def parsear(texto, entrada=None):
    """Texto en lenguaje natural -> (estado, [(nombre, campo_de_esquema)]).

    El tipo NO se declara: se deduce de que seccion aparece.

    `entrada` es para cuando el caso NO se escribe: llega de un documento. Si se pasa,
    manda sobre lo que diga el texto, y el texto puede traer solo las preguntas. Se
    pasa aparte a proposito: si se pegara el documento dentro del texto, una linea suya
    que empezara por "ask:" en la columna cero se confundiria con una cabecera.
    """
    bloques = re.split(r"\n\s*-{3,}\s*\n", texto.strip())
    estado = entrada.strip() if isinstance(entrada, str) and entrada.strip() else None
    preguntas = []

    for i, bloque in enumerate(bloques):
        seccion = None
        buffer = {}

        for linea in bloque.splitlines():
            if not linea.strip():
                continue
            t = _titulo_de(linea)
            if t:
                seccion, resto = t
                buffer.setdefault(seccion, [])
                if resto:
                    buffer[seccion].append(resto)
                continue
            if seccion:
                buffer[seccion].append(linea.strip())
            else:
                # texto suelto antes de cualquier titulo: es la entrada
                buffer.setdefault("entrada", []).append(linea.strip())

        # la entrada solo se toma del primer bloque, y solo si no vino de fuera
        if i == 0 and not estado and buffer.get("entrada"):
            estado = "\n".join(l for l in buffer["entrada"] if l)

        instrucciones = " ".join(buffer.get("pregunta", []))
        if not instrucciones:
            continue

        # el nombre sale del indice del bloque: un contador local se reiniciaria
        # en cada vuelta y todas las preguntas acabarian llamandose igual.
        nombre = "decision" if len(bloques) == 1 else f"q{i + 1}"

        opciones = buffer.get("opciones", [])
        niveles = buffer.get("niveles", [])
        sino = buffer.get("sino", [])

        if opciones:
            # "clave: descripcion" o solo "clave"
            claves, detalles = [], []
            for l in opciones:
                l = l.strip()
                if ":" in l:
                    k, v = l.split(":", 1)
                    claves.append(k.strip())
                    detalles.append(f"'{k.strip()}' = {v.strip()}.")
                else:
                    claves.append(l)
                    detalles.append(f"'{l}'.")
            campo = {"type": "enum", "choices": claves,
                     "pregunta": instrucciones,
                     "description": f"{instrucciones} " + " ".join(detalles)}

        elif niveles:
            n = len(niveles)
            detalle = " ".join(f"{j} = {t}." for j, t in enumerate(niveles))
            campo = {"type": "number", "minimum": 0, "maximum": n - 1, "step": 1,
                     "pregunta": instrucciones,
                     "description": f"{instrucciones} Niveles, de menor a mayor: {detalle}"}

        elif sino:
            partes = {}
            for l in sino:
                if ":" in l:
                    k, v = l.split(":", 1)
                    partes[k.strip().lower()] = v.strip()
            t = partes.get("true", partes.get("sí", partes.get("si", "")))
            f = partes.get("false", partes.get("no", ""))
            campo = {"type": "boolean",
                     "pregunta": instrucciones,
                     "description": f"{instrucciones} true = {t}. false = {f}."}

        else:
            # sin opciones/niveles/si-no: se pregunta por un valor libre, pero como
            # el modo decision exige un conjunto finito, se trata como verdadero/falso.
            campo = {"type": "boolean",
                     "pregunta": instrucciones,
                     "description": f"{instrucciones} Responde true si si, false si no."}

        preguntas.append((nombre, campo))

    if not estado:
        raise ValueError("Falta el 'input:' (o 'Entrada:') -- sin el caso no hay "
                         "nada que evaluar. Si el caso es un documento, pasalo con "
                         "entrada=<el texto>")
    if not preguntas:
        raise ValueError("Falta al menos un 'ask:' (o 'Pregunta:')")
    return estado, preguntas


def ejecutar(estado, preguntas, timeout=120):
    esquema = {n: c for n, c in preguntas}
    payload = {"instructions": "Respondes solo con los valores del esquema.",
               "schema": esquema, "contexts": [estado]}
    req = urllib.request.Request(
        SERVIDOR.rstrip("/") + "/v1/decision",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        cuerpo = json.loads(r.read().decode("utf-8"))
    return cuerpo, (time.perf_counter() - t0) * 1000.0


ANCHO = 30


