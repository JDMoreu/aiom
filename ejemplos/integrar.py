"""Ejemplo: consultar la API de AIOM desde Python.

Es el ejemplo de INTEGRACION: como lo llama otro programa. Dos caminos, y en los dos se
pregunta lo mismo sobre el mismo caso:

  1. Con un DOCUMENTO. El fichero se sube a `POST /documento`, que devuelve su texto, y
     ese texto entra en `POST /ask` como el campo `documento`.
  2. Con el caso escrito a mano. El caso y las preguntas van juntos en `entrada`.

Los dos endpoints, entonces, son estos dos:

    POST /documento     bytes del fichero -> su texto
    POST /ask           el caso y las preguntas -> los valores

El caso cambia de sitio segun de donde salga, pero **el endpoint de la pregunta es
siempre el mismo**: `POST /ask`. Y el campo `formato` dice como viene la entrada -aqui
`natural`, el de las cabeceras-: no se adivina.

    python ejemplos/integrar.py                     # con el caso escrito a mano
    python ejemplos/integrar.py carta.pdf           # con un documento

Solo usa la biblioteca estandar. No hay nada que instalar.

Antes de ejecutarlo hace falta el servidor del modelo y la API:

    llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
    python api.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

# La API. Se puede cambiar sin tocar el codigo: AIOM_SERVER=http://otra:8100
SERVIDOR = os.environ.get("AIOM_SERVER", "http://127.0.0.1:8100")

# Las preguntas, en el formato de cabeceras: una cabecera por pregunta y los criterios
# debajo. Es el mismo texto que se escribiria en un .txt.
PREGUNTAS = """ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas y planes
  otros: Todo lo demás

---

ask: ¿Qué urgencia tiene?
score:
  Baja: puede esperar
  Media: conviene atenderlo esta semana
  Alta: hay una fecha límite encima

---

ask: ¿El cliente ya pagó el plan anual?
noul:
  false: No ha pagado todavía
  true: Sí, ya lo pagó"""

CASO = """Buenas tardes. Escribo porque estoy bastante molesto: contraté el plan de 20 GB
el mes pasado y llevo una semana con cortes de conexión casi todas las noches. He llamado
tres veces y nadie me ha dado una solución. Además me han cobrado dos veces la factura de
este mes. Si esto sigue así me voy a dar de baja."""


def pedir(ruta, cuerpo, cabeceras=None):
    """Una peticion a la API. Devuelve el JSON de la respuesta ya leido.

    `cuerpo` puede ser un dict (se manda como JSON) o bytes (se manda en crudo, que es
    como espera los ficheros POST /documento).
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

    El cuerpo van los BYTES del fichero, en crudo, y el nombre en la cabecera
    `X-Nombre`: de la extension sale como se lee. No se adivina por el contenido, porque
    un .docx y un .zip empiezan igual.
    """
    with open(ruta, "rb") as f:
        datos = f.read()
    return pedir("/documento", datos, cabeceras={
        "Content-Type": "application/octet-stream",
        "X-Nombre": os.path.basename(ruta)})


def main():
    try:
        return correr()
    except urllib.error.HTTPError as e:
        # La API contesta con el motivo: un 400 dice que falta, un 502 que el modelo
        # fallo. Se enseña tal cual, sin adornarlo.
        detalle = e.read()[:400].decode("utf-8", "replace")
        print(f"la API contesto {e.code}: {detalle}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        # Aqui no hay API al otro lado. Es el fallo mas comun al empezar, asi que se
        # dice que falta y como levantarlo, en vez de soltar el traceback de urllib.
        print(f"no puedo hablar con la API en {SERVIDOR} ({e.reason})", file=sys.stderr)
        print("esta levantada? en otra terminal:  python api.py", file=sys.stderr)
        return 1


def correr():
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
        print(f"1. Subiendo '{os.path.basename(ruta)}' a POST /documento")
        documento = texto_del_documento(ruta)
        cifras = [f"{documento['caracteres']} caracteres",
                  f"{documento['palabras']} palabras"]
        if documento.get("paginas"):
            cifras.append(f"{documento['paginas']} paginas")
        print("   ->", ", ".join(cifras))
        if documento.get("aviso"):
            print("   aviso:", documento["aviso"])
        # El texto extraido entra como `documento`. A partir de aqui, igual que el otro
        # camino: el documento manda sobre el `input:` del texto de la entrada.
        cuerpo = {"formato": "natural", "entrada": PREGUNTAS,
                  "documento": documento["texto"]}
    else:
        print("1. Sin documento: el caso va escrito en la entrada")
        cuerpo = {"formato": "natural", "entrada": f"input: {CASO}\n\n{PREGUNTAS}"}

    print("2. Preguntando a POST /ask")
    respuesta = pedir("/ask", cuerpo)

    print(f"\n   {respuesta['n_preguntas']} preguntas, "
          f"{round(respuesta['tiempo_ms'])} ms, {respuesta['tokens']} tokens\n")
    for r in respuesta["resultados"]:
        print(f"   {r['pregunta']}")
        print(f"     -> {r['value']}   (confianza {r['confidence']:.2f})")
        if r.get("niveles"):
            print(f"        niveles: {', '.join(r['niveles'])}")
    print("\n   Para comparar con el chat, anade \"comparar\": true al cuerpo de /ask.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
