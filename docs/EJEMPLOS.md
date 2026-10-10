# Ejemplos de consulta, completos

Aquí no hay `...`: todo lo que sigue se puede copiar y pegar tal cual, con el servidor
arriba. El caso y las preguntas son los mismos en todos los ejemplos, para que se puedan
comparar entre ellos.

```bash
# en una terminal: el servidor del modelo
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
# en otra: la API
python api.py
```

Hay **un endpoint para preguntar** (`POST /ask`) y **uno para leer un documento**
(`POST /documento`). Lo que cambia entre ejemplos es el campo `formato`, que **se declara y
no se adivina**.

> **Si vas a usar `curl` en Windows, lee esto primero.** Los acentos dentro de la línea de
> comandos se rompen: el intérprete los manda en la codificación vieja de Windows y el JSON
> llega inválido (`can't decode byte 0xbf`). Dos salidas, las dos probadas:
> dejar el cuerpo en un fichero y mandarlo con `--data-binary @cuerpo.json` (con la ruta de
> Windows, `C:/...`), o **usar los ejemplos de Python de esta página**, que no tienen ese
> problema porque el fichero es UTF-8. En Linux y macOS el `curl` directo funciona.

| `formato` | para qué | el caso va en |
|---|---|---|
| `texto` | una pregunta suelta, contra los campos de un catálogo | `question` |
| `natural` | una o varias preguntas, con cabeceras | `entrada` |
| `tipado` | el JSON de TypeSafe | `state` + `questions` |

Si no mandas `formato`, la API lo **deduce** del campo que traigas. Pero declararlo es más
claro, y es lo que hacen todos los ejemplos de esta página.

---

## 1. Lo mínimo: una pregunta suelta (`texto`)

**Ojo con el nombre: `texto` no es «modo chat».** Son dos cosas distintas y se confunden
fácil, así que van separadas:

- **`formato`** dice **cómo está escrita la pregunta**. `texto` es una frase suelta, sin
  esquema. Y como no trae esquema, se usa el del **catálogo** (`--catalog`, por defecto
  `catalogs/iot.json`).
- **`mode`** dice **quién contesta**, y solo existe en este formato:

| `mode` | quién contesta | qué devuelve |
|---|---|---|
| `auto` (por defecto) | la decisión; y si el catálogo no cubre la pregunta, el chat | valores, o prosa |
| `decision` | la decisión, siempre | un valor por cada campo del catálogo |
| `chat` | el chat, siempre | prosa |

**Para qué se usa `texto`:** cuando los campos ya están fijos y son los mismos para todas
las preguntas. El catálogo de ejemplo tiene cinco (`respondible`, `magnitud`, `predio`,
`predio_valido`, `urgencia`), así que cualquier pregunta sobre esa red devuelve esos cinco
valores y nada más. Es el camino más corto: **no hay que escribir ningún esquema**.

La misma pregunta, en los tres modos, medida en esta máquina:

| se manda | contesta | resultado | tiempo |
|---|---|---|---|
| `"mode": "decision"` | la decisión | los 5 valores del catálogo | 73 ms, 0 tokens |
| `"mode": "chat"` | el chat | prosa | 8399 ms, 793 tokens |
| sin `mode` (`auto`) | la decisión | los 5 valores del catálogo | 73 ms, 0 tokens |
| sin `mode`, pregunta que el catálogo no cubre | el chat | prosa | 11446 ms, 1162 tokens |

En las dos últimas filas se ve el `auto`: decide por su cuenta, y cuando la pregunta pide
algo que el catálogo no puede dar (un informe, por ejemplo) se la pasa al chat.

**Los otros dos formatos no usan el catálogo.** `natural` y `tipado` traen su propio
esquema, pregunta a pregunta, y van siempre por la decisión.

```bash
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "texto",
  "question": "El sensor del predio 3 lleva dos días sin reportar temperatura",
  "mode": "decision"
}'
```

```python
import json, urllib.request

cuerpo = {
    "formato": "texto",
    "question": "El sensor del predio 3 lleva dos días sin reportar temperatura",
    "mode": "decision",          # auto | decision | chat. Con auto, elige el motor
}
peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps(cuerpo).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

print(respuesta["tiempo_ms"], "ms,", respuesta["tokens"], "tokens")
for campo in respuesta["resultados"]:
    print(campo["campo"], "=", campo["value"], f"({campo['confidence']:.2f})")
```

---

## 2. Los tres tipos de pregunta (`natural`)

El formato `natural` es el de las cabeceras: `input:` con el caso, y luego una cabecera por
pregunta. Las preguntas se separan con una línea de tres guiones.

```bash
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "natural",
  "entrada": "input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión. Ya probé a reinstalarla y sigue igual.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  comercial: Ventas y planes\n  otros: Todo lo demás\n\n---\n\nask: ¿Qué urgencia tiene?\nscore:\n  Baja: puede esperar\n  Media: conviene atenderlo esta semana\n  Alta: hay una fecha límite encima\n\n---\n\nask: ¿El cliente ya pagó el plan anual?\nnoul:\n  false: No ha pagado todavía\n  true: Sí, ya lo pagó"
}'
```

Lo mismo desde Python, con el texto legible en vez de escapado —que es como conviene
escribirlo—:

```python
import json, urllib.request

ENTRADA = """input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión. Ya probé a reinstalarla y sigue igual.

ask: ¿A qué área hay que enviar este correo?
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

peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps({"formato": "natural", "entrada": ENTRADA}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

for r_ in respuesta["resultados"]:
    print(f"[{r_['tipo']}] {r_['pregunta']}")
    print(f"   {r_['campo']} = {r_['value']!r}")
    print(f"   reparto: {r_['probabilities']}")
    if r_.get("niveles"):
        print(f"   niveles: {r_['niveles']}")
```

Los tres tipos, uno por uno, y qué devuelve cada uno:

| cabecera | tipo | devuelve |
|---|---|---|
| `choice:` | `choice` | la opción elegida, y la probabilidad de **todas** |
| `score:` | `score` | el nivel, como número (puede caer entre dos) |
| `noul:` | `noul` | `true` o `false`, con su probabilidad |

**Un `noul` es verdadero o falso**, no «sí o no»: sus dos valores son `false` y `true` y no
se pueden añadir más. Lo que se elige es **qué significa cada uno**.

---

## 3. Una sola pregunta de cada tipo

Si solo quieres una, se manda igual, sin los guiones:

```python
import json, urllib.request

def preguntar(entrada):
    peticion = urllib.request.Request(
        "http://127.0.0.1:8100/ask",
        data=json.dumps({"formato": "natural", "entrada": entrada}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=600) as r:
        return json.loads(r.read().decode())["resultados"][0]

# choice: elegir de una lista
r = preguntar("""input: Llevo desde ayer sin poder entrar: me sale un error 500.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  otros: Todo lo demás""")
print("choice:", r["value"], r["probabilities"])

# score: poner algo en una escala
r = preguntar("""input: Se cayó la conexión en la oficina central y llevan dos horas sin servicio.

ask: ¿Qué urgencia tiene?
score:
  Baja: puede esperar
  Media: conviene atenderlo esta semana
  Alta: hay una fecha límite encima""")
print("score:", r["value"], r["niveles"])

# noul: verdadero o falso
r = preguntar("""input: Un cliente escribe diciendo que han entrado en su cuenta desde otro país y que no reconoce dos compras hechas esta madrugada.

ask: ¿Hay indicios de que la cuenta esté comprometida?
noul:
  false: No hay indicios de acceso no autorizado
  true: Hay indicios de acceso no autorizado""")
print("noul:", r["value"], r["probability"])
```

---

## 4. El formato tipado (`tipado`)

El mismo caso en el JSON de TypeSafe: `state.input` con el caso, y `questions` con un objeto
por pregunta. `type` es el tipo, `instructions` el enunciado y `criteria` los criterios. En
un `noul` los criterios son `true` y `false`.

```python
import json, urllib.request

CUERPO = {
    "formato": "tipado",
    "state": {
        "input": "Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale "
                 "un error 500 cada vez que intento iniciar sesión. Ya probé a reinstalarla "
                 "y sigue igual."
    },
    "questions": {
        "q1": {
            "type": "choice",
            "instructions": "¿A qué área hay que enviar este correo?",
            "criteria": {
                "soporte": "Fallos y errores del producto",
                "facturacion": "Cobros, facturas y reembolsos",
                "comercial": "Ventas y planes",
                "otros": "Todo lo demás"
            }
        },
        "q2": {
            "type": "score",
            "instructions": "¿Qué urgencia tiene?",
            "criteria": ["Baja: puede esperar",
                         "Media: conviene atenderlo esta semana",
                         "Alta: hay una fecha límite encima"]
        },
        "q3": {
            "type": "noul",
            "instructions": "¿El cliente ya pagó el plan anual?",
            "criteria": {"false": "No ha pagado todavía",
                         "true": "Sí, ya lo pagó"}
        }
    }
}

peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps(CUERPO).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

for r_ in respuesta["resultados"]:
    print(r_["campo"], r_["tipo"], "=", r_["value"])
```

**Da exactamente lo mismo que el formato natural**: son dos vistas del mismo caso, no dos
motores distintos. Si quieres comprobarlo, manda el mismo contenido por los dos y compara.

---

## 5. Con un documento: dos llamadas

El caso puede ser un documento en vez de un texto. Son **dos llamadas**: primero
`POST /documento`, que devuelve el texto, y luego `POST /ask` con ese texto.

```python
import json, os, urllib.request

SERVIDOR = "http://127.0.0.1:8100"
RUTA = "carta.pdf"          # vale .txt, .md, .csv, .json, .log, .docx y .pdf

# 1. Subir el fichero. El cuerpo son los BYTES, en crudo, y el nombre en X-Nombre:
#    de la extension sale como se lee, y no se adivina por el contenido.
with open(RUTA, "rb") as f:
    datos = f.read()

peticion = urllib.request.Request(
    SERVIDOR + "/documento", data=datos, method="POST")
peticion.add_header("Content-Type", "application/octet-stream")
peticion.add_header("X-Nombre", os.path.basename(RUTA))
with urllib.request.urlopen(peticion, timeout=600) as r:
    documento = json.loads(r.read().decode())

print(documento["nombre"], documento["caracteres"], "caracteres")
if documento.get("aviso"):
    print("aviso:", documento["aviso"])

# 2. Preguntar. El texto extraido va en `documento`, y manda sobre el `input:`.
ENTRADA = """ask: ¿De qué trata el documento?
choice:
  factura: Una factura o un cobro
  contrato: Un contrato
  carta: Una carta o una solicitud
  otro: Otra cosa

---

ask: ¿Aparece una fecha?
noul:
  false: No aparece ninguna fecha
  true: Sí aparece alguna fecha"""

peticion = urllib.request.Request(
    SERVIDOR + "/ask",
    data=json.dumps({"formato": "natural", "entrada": ENTRADA,
                     "documento": documento["texto"]}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

for r_ in respuesta["resultados"]:
    print(r_["pregunta"], "->", r_["value"])
```

Lo mismo con `curl`, que para el fichero usa `--data-binary`:

```bash
# 1. subir (el nombre va en la cabecera X-Nombre)
curl -s http://127.0.0.1:8100/documento \
  -H "X-Nombre: carta.pdf" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @carta.pdf

# 2. preguntar, con el texto que devolvio el paso 1 dentro de "documento"
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "natural",
  "documento": "<el texto que devolvio el paso 1>",
  "entrada": "ask: ¿De qué trata el documento?\nchoice:\n  factura: Una factura\n  contrato: Un contrato\n  otro: Otra cosa"
}'
```

Los dos endpoints, en una tabla:

| | |
|---|---|
| `POST /documento` | los bytes del fichero y el nombre en `X-Nombre` → su texto |
| `POST /ask` | el caso y las preguntas → los valores |

Un PDF escaneado se lee por OCR si está instalado (`pip install rapidocr-onnxruntime`), y
la respuesta lo dice en `aviso`: ese texto puede traer errores.

---

## 6. La comparación: las dos vías a la vez

Con `"comparar": true`, la **misma** petición resuelve el caso por las dos vías —decisión y
chat— y devuelve las dos, para que los tiempos sean del mismo momento.

```python
import json, urllib.request

ENTRADA = """input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  otros: Todo lo demás"""

peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps({"formato": "natural", "entrada": ENTRADA,
                     "comparar": True}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    d = json.loads(r.read().decode())

print("decision:", d["decision"]["peticiones"], "peticion,",
      d["decision"]["tiempo_ms"], "ms,", d["decision"]["tokens"], "tokens")
print("chat:    ", d["chat"]["peticiones"], "peticion,",
      d["chat"]["tiempo_ms"], "ms,", d["chat"]["tokens"], "tokens")

print()
print("lo que respondio la decision:")
for r_ in d["decision"]["resultados"]:
    print(" ", r_["campo"], "=", r_["value"])

print()
print("lo que respondio el chat, entero:")
print(d["chat"]["resultados"][0]["texto"])
```

Los dos tiempos se miden **con el mismo reloj** —la ida y vuelta completa—, así que la
comparación es honesta. La decisión contesta por preguntas; el chat contesta todo de una
vez, porque así se le pregunta a un asistente.

---

## 7. Desde el navegador

Si lo que estás montando es una página, es el mismo `POST /ask` con `fetch`:

```html
<script>
fetch("http://127.0.0.1:8100/ask", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    formato: "natural",
    entrada: `input: Llevo desde ayer sin poder entrar: me sale un error 500.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  otros: Todo lo demás`
  })
})
  .then((r) => r.json())
  .then((d) => {
    for (const r of d.resultados) {
      console.log(r.tipo, r.pregunta, "->", r.value);
    }
  });
</script>
```

Las cabeceras CORS van abiertas a propósito: la API solo escucha en `127.0.0.1`, así que una
página servida desde otro sitio puede llamarla.

---

## 8. Qué devuelve cada cosa

Lo que hay dentro de cada `resultado` de `/ask`:

| campo | qué es |
|---|---|
| `campo` | el nombre del campo (`q1`, `q2`...) |
| `tipo` | `choice`, `score` o `noul` |
| `pregunta` | el enunciado, para no tener que recordarlo |
| `value` | **la respuesta.** Es el dato |
| `probability` | la probabilidad de **ese** valor |
| `probabilities` | la de **todas** las opciones: aquí se ve si dudó entre dos |
| `confidence` | la confianza de la lectura entera |
| `niveles` | solo en un `score`: la etiqueta de cada nivel |

Y lo que devuelve `/documento`:

| campo | qué es |
|---|---|
| `texto` | el texto extraído, que es lo que se manda luego en `documento` |
| `nombre`, `tipo` | el fichero y cómo se leyó |
| `caracteres`, `palabras`, `lineas` | el tamaño |
| `paginas` | cuántas tiene (solo en PDF: es el único formato donde ese dato es real) |
| `paginas_con_texto`, `paginas_con_ocr`, `paginas_ilegibles`, `paginas_sin_texto` | cómo salió cada página |
| `aviso` | si hubo páginas que no se pudieron leer, o el texto no cabe en el contexto |

---

## 9. Cuando algo va mal

| lo que ves | qué pasa |
|---|---|
| `formato no valido: None` | no mandaste `formato` y tampoco se pudo deducir: no hay `question`, ni `entrada`, ni `questions` |
| `formato no valido: 'raro'` | `formato` no es `texto`, `natural` ni `tipado` |
| `falta 'question'` | mandaste `formato: "texto"` sin `question` |
| `falta 'entrada'` | mandaste `formato: "natural"` sin `entrada` |
| `Falta el 'input:'` | la entrada no trae el caso. Si es un documento, va en el campo `documento` |
| `llama-server 400` | el modelo rechazó la petición: mira el `detail`, suele decir cuál |
| `llama-server` no responde (502) | el servidor del modelo no está levantado |
| `no puedo hablar con la API` | `api.py` no está levantado, o el puerto no es ese |

Todos los errores vienen en JSON, con un campo `error` que lo dice. No hay que adivinar.

Y si mandas `formato` **no** pasa nada malo: la API lo **deduce** del campo que traigas
—`question` → `texto`, `entrada` → `natural`, `questions` → `tipado`—. Pero declararlo es
más claro, y es lo que hacen todos los ejemplos de arriba.

---

Todo esto está también, ejecutable y de una pieza, en
[`ejemplos/integrar.py`](../ejemplos/integrar.py): seis preguntas de los tres tipos, los tres
formatos y los tres caminos del caso.
