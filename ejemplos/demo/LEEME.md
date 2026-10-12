# Demo en vivo de AIOM — PQR y log de servidor

Materiales para una demo de AIOM: se sube un documento a la API, se le saca el texto y se
le lanzan preguntas al modelo, que responde usando **solo lo que dice el documento**.

## Ficheros

| Fichero | Qué es |
|---|---|
| `pqr.pdf` | PQR (Petición, Queja o Reclamo) de un cliente, 2 páginas, con datos **ficticios** |
| `pqr.txt` | El mismo texto de la PQR, en UTF-8 (3.475 caracteres) |
| `servidor.log` | Log de errores de un servidor de aplicación, 336 líneas |
| `preguntas_pqr.txt` | 30 preguntas sobre la PQR — 15 `choice`, 8 `noul`, 7 `score` |
| `preguntas_log.txt` | 30 preguntas sobre el log — 15 `choice`, 8 `noul`, 7 `score` |
| `_gen_pqr.py`, `_gen_log.py` | Los generadores: vuelven a crear el PDF, el `.txt` y el log |

## El formato de las preguntas (formato `natural`)

Los dos ficheros de preguntas se copian y se pegan **tal cual**: dentro solo hay preguntas,
sin comentarios ni numeración. Cada pregunta es un bloque, y los bloques van separados por
una línea de `---`:

    ask: ¿la pregunta?
    choice:
      clave: descripción de la opción

- Los tres tipos: `choice` (elegir una opción), `noul` (verdadero/falso) y `score`
  (un nivel de una escala, de 0 en adelante).
- El caso **no** va dentro del texto de las preguntas: se carga aparte. En el cliente web,
  con el botón **Cargar documento**; por API, en el campo `documento` de `POST /ask`.
  Por eso los ficheros empiezan directamente en `ask:`.

> **El caso va en el campo `documento`, y las preguntas separadas por `---`.** Las dos
> cosas son obligatorias cuando se lanzan varias de una vez:
>
> - El documento **no** se pega dentro del texto de las preguntas: se pasa aparte, en el
>   campo `documento` del cuerpo de `POST /ask`. El analizador lo recibe separado a
>   propósito, porque una línea del documento que empezara por `ask:` en la columna cero
>   se confundiría con una cabecera.
> - Cada pregunta va separada de la siguiente por una línea de guiones (`---`). Sin los
>   separadores, las diez se leen como **una sola** pregunta con diez campos del mismo
>   nombre, y el motor contesta `400: field "decision" has duplicate allowed values`.
>
> Con eso, las 30 se resuelven en **una sola petición y ~1 segundo** (medido: 30 preguntas
> en 1025 ms, 0 tokens), no hace falta partirlas en grupos.

## Cómo se usa en la demo

La API escucha en `http://127.0.0.1:8100` y el modelo en el `8096`. Solo hay dos rutas:

- **`POST /documento`** — sube un fichero y devuelve su texto. El cuerpo va en crudo y el
  nombre en la cabecera `X-Nombre` o en `?nombre=`.
- **`POST /ask`** — la pregunta. Formato `natural`, con el texto del documento en `documento`.

### 1. Subir el PDF y sacar su texto (curl)

    curl -s -X POST "http://127.0.0.1:8100/documento?nombre=pqr.pdf" \
         --data-binary @pqr.pdf

Devuelve un JSON con `texto` (y `caracteres`, `paginas`, ...). Del PDF de la demo salen
**3.536 caracteres** en 2 páginas.

### 2. Preguntar

Con el cliente web: abre `http://127.0.0.1:8100/`.

O con un script de Python (los dos pasos: subir el fichero y preguntar):

```python
import json, urllib.request

BASE = "http://127.0.0.1:8100"

def subir(ruta, nombre):
    datos = open(ruta, "rb").read()
    req = urllib.request.Request(BASE + "/documento", data=datos,
                                 headers={"X-Nombre": nombre})
    return json.load(urllib.request.urlopen(req))

def preguntar(documento, entrada):
    cuerpo = json.dumps({"formato": "natural", "documento": documento,
                         "entrada": entrada}).encode("utf-8")
    req = urllib.request.Request(BASE + "/ask", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))

doc = subir("pqr.pdf", "pqr.pdf")
print("caracteres:", doc["caracteres"])

# una pregunta suelta
q = """ask: ¿Cuánto dinero reclama en total el peticionario?
choice:
  206310: $206.310
  98700: $98.700
  107610: $107.610
  288600: $288.600"""
r = preguntar(doc["texto"], q)
for x in r["resultados"]:
    print(x["campo"], "->", x["value"], x["probabilities"])

# o el fichero entero, con las 30 preguntas de golpe
entrada = open("preguntas_pqr.txt", encoding="utf-8").read()
r = preguntar(doc["texto"], entrada)
```

Lo mismo con el log: se sube `servidor.log` con `POST /documento` y se pregunta con
`preguntas_log.txt`.

## Consejo para la demo

El motor de decisión resuelve todas las preguntas de una petición en una sola pasada. Con
las 30 a la vez la precisión baja un poco; va mejor por grupos de unos 10. Las 30 preguntas
de cada bloque están verificadas contra la API en grupos de 10 y responden todas bien.

Si `POST /ask` devuelve un 502, es que el modelo (8096) se ha caído: espera unos segundos
y reintenta.
