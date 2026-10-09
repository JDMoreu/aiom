"""Escribe la decision en lenguaje natural; el sistema lee el tipo y la ejecuta.

No hay que escribir JSON. Se escribe el caso asi:

    input: Buenas tardes. Contraté el plan de 20 GB y llevo una semana con cortes de
    conexión casi todas las noches. Además me han cobrado dos veces la factura.

    ask: ¿A qué área hay que enviar este correo?
    choice:
      soporte: Fallos y errores del producto
      facturacion: Cobros, facturas y reembolsos
      comercial: Ventas, planes y bajas
      otros: Todo lo demás

El tipo se DECLARA con la cabecera: `choice` elige de una lista, `score` pone algo en
una escala y `noul` es un si o un no.

    ask: ¿Qué urgencia tiene?
    score:
      Baja: puede esperar
      Media: conviene atenderlo esta semana
      Alta: hay una fecha límite encima

    ask: ¿Amenaza el cliente con darse de baja?
    noul:
      false: No lo menciona
      true: Sí lo menciona

`score` va de menor a mayor y se numera desde 0, asi que en el ejemplo Baja=0, Media=1
y Alta=2. Y `noul` escribe primero el significado de false y luego el de true.

Se pueden poner varias preguntas separadas por una linea con ---, y se mandan TODAS
en una sola peticion: es la ventaja de tener un solo modelo sirviendo varios campos.

    python preguntar.py caso.txt          # desde un fichero
    python preguntar.py --texto "..."     # desde la linea de comandos
    python preguntar.py --json            # la respuesta cruda del servidor

Las cabeceras largas en espanol (Entrada / Pregunta / Opciones / Niveles de puntuación
/ Qué significa no o sí) se siguen aceptando, pero el estandar es el corto.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def parsear(texto):
    """Texto en lenguaje natural -> (estado, [(nombre, campo_de_esquema)]).

    El tipo NO se declara: se deduce de que seccion aparece.
    """
    bloques = re.split(r"\n\s*-{3,}\s*\n", texto.strip())
    estado = None
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

        # la entrada solo se toma del primer bloque
        if i == 0 and buffer.get("entrada"):
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
            # el modo decision exige un conjunto finito, se trata como si/no.
            campo = {"type": "boolean",
                     "pregunta": instrucciones,
                     "description": f"{instrucciones} Responde true si si, false si no."}

        preguntas.append((nombre, campo))

    if not estado:
        raise ValueError("Falta el 'input:' (o 'Entrada:') -- sin el caso no hay "
                         "nada que evaluar")
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


def barra(p):
    n = int(round(float(p) * ANCHO))
    return "#" * n + "." * (ANCHO - n)


def mostrar(estado, preguntas, cuerpo, ms):
    tipos = {"enum": "CHOICE", "number": "SCORE", "boolean": "NOUL"}
    campos = cuerpo["results"][0]["fields"]

    print(f"input: {estado}")
    print(f"\n{len(preguntas)} pregunta(s), una sola peticion  "
          f"({ms:.0f} ms, 0 tokens)")

    for nombre, spec in preguntas:
        f = campos.get(nombre)
        if not f:
            continue
        dist = f.get("probabilities") or {}
        tipo = tipos.get(spec["type"], spec["type"])

        print("\n" + "-" * 62)
        # La cabecera muestra SOLO la pregunta. Antes imprimia la descripcion del
        # campo cortada en el primer punto, y como la descripcion empieza por la
        # lista de opciones, la primera opcion salia en la cabecera como si fuera
        # la respuesta: ponia "'soporte' = Fallos y errores" mientras la flecha
        # marcaba "facturacion".
        print(f"{tipo}  ·  {spec.get('pregunta') or spec['description'].split('.')[0]}")
        print("-" * 62)

        if spec["type"] == "enum":
            for k, p in sorted(dist.items(), key=lambda kv: -kv[1]):
                print(f"  {k:<14} {p:6.3f}  {barra(p)}"
                      f"{'  <-' if k == f['value'] else ''}")
        elif spec["type"] == "number":
            niveles = re.findall(r"\d+ = ([^.]+)\.", spec["description"])
            for k, p in sorted(dist.items(), key=lambda kv: float(kv[0])):
                j = int(float(k))
                etiqueta = niveles[j].strip() if j < len(niveles) else f"nivel {j}"
                print(f"  {etiqueta:<14} {p:6.3f}  {barra(p)}"
                      f"{'  <-' if float(k) == float(f['value']) else ''}")
            punt = sum(float(k) * float(p) for k, p in dist.items())
            print(f"\n  puntuacion = {punt:.2f}")
        else:
            for k, p in sorted(dist.items(), key=lambda kv: -kv[1]):
                print(f"  {'sí' if k == 'true' else 'no':<14} {p:6.3f}  {barra(p)}"
                      f"{'  <-' if k == f['value'] else ''}")
            print(f"\n  probabilidad de que sí = {dist.get('true', 1 - f['probability']):.3f}")

        print(f"  confianza = {f.get('confidence', float('nan')):.3f}")


def main():
    ap = argparse.ArgumentParser(prog="preguntar")
    ap.add_argument("fichero", nargs="?", help="fichero de texto con el caso")
    ap.add_argument("--texto", help="el caso, escrito aqui mismo")
    ap.add_argument("--json", action="store_true", help="respuesta cruda del servidor")
    a = ap.parse_args()

    if a.texto:
        texto = a.texto
    elif a.fichero:
        with open(a.fichero, encoding="utf-8") as f:
            texto = f.read()
    else:
        texto = sys.stdin.read()

    estado, preguntas = parsear(texto)

    print()
    cuerpo, ms = ejecutar(estado, preguntas)
    if a.json:
        print(json.dumps(cuerpo, ensure_ascii=False, indent=2))
    else:
        mostrar(estado, preguntas, cuerpo, ms)
    print()


if __name__ == "__main__":
    raise SystemExit(main())
