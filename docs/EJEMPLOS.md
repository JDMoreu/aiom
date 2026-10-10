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
| `natural` | una o varias preguntas de decisión, con cabeceras | `entrada` |
| `tipado` | lo mismo, en el JSON de TypeSafe | `state` + `questions` |
| `chat` | lo mismo que `natural`, pero en prosa | `entrada` (o `question`, una frase) |

Los dos primeros son **vías de decisión**: traen su propio esquema y devuelven valores, sin
generar un token. El tercero es **prosa**: el modelo escribe.

`natural` y `chat` aceptan **la misma entrada**, así que el mismo caso se puede mandar por
las dos y comparar las respuestas sin reescribir nada. `tipado` es lo mismo con el esquema
en JSON.

Si no mandas `formato`, la API lo **deduce** del campo que traigas. Pero declararlo es más
claro, y es lo que hacen todos los ejemplos de esta página.

---

## 1. Una pregunta suelta, en prosa (`chat`)

El formato `chat` no tiene esquema: ni campos, ni opciones, ni probabilidades. El modelo
escribe la respuesta, y es el camino para lo que no es una decisión —redactar, explicar,
resumir—.

**Acepta la misma entrada que `natural`**, así que se le puede pasar **el mismo caso** y
comparar las dos respuestas sin reescribir nada. El texto de abajo es exactamente el mismo
que el del apartado 2:

```bash
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "chat",
  "entrada": "input: Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás"
}'
```

Lo mismo desde Python, con el texto legible en vez de escapado:

```python
import json, urllib.request

ENTRADA = """input: Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  otros: Todo lo demás"""

peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps({"formato": "chat", "entrada": ENTRADA}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

print(respuesta["tiempo_ms"], "ms,", respuesta["tokens"], "tokens")
print(respuesta["resultados"][0]["texto"])
```

Y esto es lo que devuelve —la prosa, recortada—:

```json
{
  "resultados": [
    {
      "via": "chat",
      "texto": "Buenos días. Entiendo perfectamente tu situación, y es muy frustrante no poder acceder a la aplicación cuando necesitas usarla. El error 500 es un problema técnico que indica que hay un fallo en el servidor o en el proceso de carga de la aplicación, por lo que el reinstalación no soluciona el problema, ya que el fallo no está en el archivo de la app.\n\nA continuación, respondo a las preguntas que has planteado:\n\n**1. ¿A qué área hay que enviar este correo?**\nDeberías enviar el correo a la **sección de soporte técnico o atención al cliente** de la plataforma o aplicación en la que utilizas..."
    }
  ],
  "tiempo_ms": 6519.5,
  "tokens": 675,
  "formato": "chat",
  "n_preguntas": 1
}
```

Fíjate en lo que **no** hay: ni `campo`, ni `tipo`, ni `probability`, ni `confidence`. Esos
campos son de la decisión, y aquí no existen porque no hay nada que elegir.

**Las cabeceras no llegan al modelo.** Con `entrada`, el `input:`, los `ask:` y los
`choice:` se quitan antes de pasárselo: medido, con ellos delante el modelo contesta en el
formato de la decisión —devolvió un `true` a secas en 2 tokens— y eso no es prosa.

**Y también acepta una pregunta suelta**, si lo que quieres es preguntar algo y ya está:

```json
{"formato": "chat", "question": "Explícame en dos frases qué es una red de sensores"}
```

**La diferencia con los otros dos, en una línea:** `natural` y `tipado` **eligen** un valor
de una lista que tú escribes; `chat` **escribe** lo que le parece. Los dos primeros gastan 0
tokens; el tercero escribe, y por eso tarda mucho más. Con el mismo caso de arriba: 85 ms y
0 tokens la decisión, 6519 ms y 675 tokens el chat.

*(La prosa del chat cambia de una corrida a otra —la de decisión es estable—, así que los
tiempos y el texto de aquí son los de la corrida en la que se capturaron. Lo que no cambia
es la diferencia: 0 tokens contra cientos.)*

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

La respuesta de verdad, con las tres preguntas resueltas en la misma petición. Está
recortada solo en la prosa del primer resultado, que es larga:

```json
{
  "resultados": [
    {
      "campo": "q1", "tipo": "choice",
      "pregunta": "¿A qué área hay que enviar este correo?",
      "value": "soporte",
      "probability": 1.0,
      "probabilities": {"soporte": 1.0, "facturacion": 0.0, "comercial": 0.0, "otros": 0.0},
      "confidence": 1.0
    },
    {
      "campo": "q2", "tipo": "score",
      "pregunta": "¿Qué urgencia tiene?",
      "value": 2.0,
      "probability": 0.7025,
      "probabilities": {"0.0": 0.1575, "1.0": 0.1401, "2.0": 0.7025},
      "confidence": 0.2586,
      "niveles": ["Baja: puede esperar",
                  "Media: conviene atenderlo esta semana",
                  "Alta: hay una fecha límite encima"]
    },
    {
      "campo": "q3", "tipo": "noul",
      "pregunta": "¿El cliente ya pagó el plan anual?",
      "value": false,
      "probability": 0.9825,
      "probabilities": {"true": 0.0175, "false": 0.9825},
      "confidence": 0.8726
    }
  ],
  "tiempo_ms": 117.7,
  "tokens": 0,
  "n_preguntas": 3,
  "formato": "natural"
}
```

**`tokens: 0`** es lo que distingue esta vía de la de chat: el modelo no escribió nada,
eligió. Y en el `score`, `value: 2.0` solo significa algo porque `niveles` dice cuál es el
2 — «Alta: hay una fecha límite encima»—.

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

Y esto es lo que devuelve cada una, de verdad:

```json
{"campo": "decision", "tipo": "choice",
 "pregunta": "¿A qué área hay que enviar este correo?",
 "value": "soporte", "probability": 1.0,
 "probabilities": {"soporte": 1.0, "facturacion": 0.0, "otros": 0.0},
 "confidence": 1.0}
```

```json
{"campo": "decision", "tipo": "score",
 "pregunta": "¿Qué urgencia tiene?",
 "value": 2.0, "probability": 0.7826,
 "probabilities": {"0.0": 0.0018, "1.0": 0.2156, "2.0": 0.7826},
 "confidence": 0.5142,
 "niveles": ["Baja: puede esperar",
             "Media: conviene atenderlo esta semana",
             "Alta: hay una fecha límite encima"]}
```

```json
{"campo": "decision", "tipo": "noul",
 "pregunta": "¿Hay indicios de que la cuenta esté comprometida?",
 "value": true, "probability": 0.8281,
 "probabilities": {"true": 0.8281, "false": 0.1719},
 "confidence": 0.338}
```

El `campo` se llama `decision` cuando no le has dado un nombre tú: en `natural` y `tipado`
el nombre sale de lo que escribiste (`q1`, `area`...), y aquí no hay ninguno.

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
motores distintos. Los tres resultados de este ejemplo salen **idénticos** a los del
apartado 2 —mismo `soporte`, mismo `2.0`, mismo `false`, hasta la misma probabilidad—,
porque el esquema que recibe el modelo es el mismo.

Lo único que cambia es el nombre del campo, si tú lo cambias: aquí las preguntas se llaman
`q1`, `q2`, `q3` porque así se llaman en el JSON de arriba. En `natural` salían igual
porque allí también se llamaban así.

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

Lo que devuelve el paso 1, recortado (el texto entero son 3900 caracteres):

```json
{
  "texto": "JOSE DAVID MOREU CEBALLOS\nIngeniero Electrónico\n\njdmoreudev@gmail.com...",
  "nombre": "cv.pdf", "tipo": "pdf",
  "caracteres": 3925, "palabras": 587, "lineas": 71,
  "paginas": 1, "paginas_con_texto": 1,
  "paginas_con_ocr": 0, "paginas_ilegibles": 0, "paginas_sin_texto": 0,
  "aviso": "de 1 paginas: 1 con texto propio."
}
```

Y lo que devuelve el paso 2, con ese texto dentro de `documento`:

```json
{
  "resultados": [
    {
      "campo": "q1", "tipo": "choice",
      "pregunta": "¿De qué trata el documento?",
      "value": "otro",
      "probability": 0.7585,
      "probabilities": {"factura": 0.002, "contrato": 0.0488,
                        "carta": 0.1907, "otro": 0.7585},
      "confidence": 0.5056
    },
    {
      "campo": "q2", "tipo": "noul",
      "pregunta": "¿Aparece una fecha?",
      "value": false,
      "probability": 0.9381,
      "probabilities": {"true": 0.0619, "false": 0.9381},
      "confidence": 0.6651
    }
  ],
  "tiempo_ms": 369.5,
  "tokens": 0,
  "n_preguntas": 2,
  "formato": "natural"
}
```

**El `aviso` no es decoración.** Dice de dónde salió el texto: si una página se leyó con
OCR (una imagen, y por tanto con posibles errores) o si se quedó sin leer. Quien pregunte
sobre el documento tiene que saberlo antes de fiarse de la respuesta.

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

La respuesta de verdad. La decisión acierta y tarda 85 ms sin escribir nada; el chat escribe
500 tokens y de paso se pone a opinar:

```json
{
  "formato": "natural",
  "comparar": true,
  "n_preguntas": 1,
  "decision": {
    "peticiones": 1,
    "resultados": [
      {"campo": "decision", "tipo": "choice",
       "pregunta": "¿A qué área hay que enviar este correo?",
       "value": "soporte", "probability": 1.0,
       "probabilities": {"soporte": 1.0, "facturacion": 0.0, "otros": 0.0},
       "confidence": 1.0}
    ],
    "tiempo_ms": 85.0,
    "tokens": 0
  },
  "chat": {
    "peticiones": 1,
    "resultados": [
      {"via": "chat",
       "texto": "¡Buenos días!\n\nEntiendo tu frustración, y es un problema común que ocurra cuando la aplicación tiene un fallo técnico (como el error 500) que impide el inicio de sesión.\n\n**1. ¿A qué área hay que enviar este correo?**\n\nPara que te pueda ayudar a resolver el problema, lo primero es enviar el correo a la **sección de soporte técnico o atención al cliente**..."}
    ],
    "tiempo_ms": 4896.1,
    "tokens": 513
  }
}
```

**Compáralas.** La decisión da `soporte` con un `1.0`: un valor, cerrado, que un programa
puede leer y usar. El chat da la misma respuesta, pero dentro de un párrafo que empieza
saludando, sigue explicando qué es un error 500 y acaba mandándote a buscar un formulario de
contacto. Para un humano está bien; para un programa, no hay por dónde cogerlo.

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

Lo que hay dentro de cada `resultado` de `/ask` cuando el formato es de decisión
(`natural` o `tipado`):

| campo | qué es |
|---|---|
| `campo` | el nombre del campo (`q1`, `q2`...; `decision` si no le pusiste nombre) |
| `tipo` | `choice`, `score` o `noul` |
| `pregunta` | el enunciado, para no tener que recordarlo |
| `value` | **la respuesta.** Es el dato |
| `probability` | la probabilidad de **ese** valor |
| `probabilities` | la de **todas** las opciones: aquí se ve si dudó entre dos |
| `confidence` | la confianza de la lectura entera |
| `niveles` | solo en un `score`: la etiqueta de cada nivel |

Las probabilidades van **redondeadas a 4 decimales**. El motor las devuelve con toda la
precisión del float —`0.9999997615814209`—, y eso no lo lee nadie.

Y en el formato `chat` el resultado es otro, porque no hay nada que elegir: `via` dice de
dónde viene y `texto` es la respuesta entera.

| campo | qué es |
|---|---|
| `via` | siempre `chat` |
| `texto` | la respuesta en prosa, con sus saltos de línea |

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
| `formato no valido: 'raro'` | `formato` no es `natural`, `tipado` ni `chat` |
| `falta 'question'` | mandaste `formato: "chat"` sin `question` |
| `falta 'entrada'` | mandaste `formato: "natural"` sin `entrada` |
| `Falta el 'input:'` | la entrada no trae el caso. Si es un documento, va en el campo `documento` |
| `llama-server 400` | el modelo rechazó la petición: mira el `detail`, suele decir cuál |
| `llama-server` no responde (502) | el servidor del modelo no está levantado |
| `no puedo hablar con la API` | `api.py` no está levantado, o el puerto no es ese |

Todos los errores vienen en JSON, con un campo `error` que lo dice. No hay que adivinar.

Y si mandas `formato` **no** pasa nada malo: la API lo **deduce** del campo que traigas
—`entrada` → `natural`, `questions` → `tipado`, `question` → `chat`—. Pero declararlo es
más claro, y es lo que hacen todos los ejemplos de arriba.

---

Todo esto está también, ejecutable y de una pieza, en
[`ejemplos/integrar.py`](../ejemplos/integrar.py): seis preguntas de los tres tipos, los tres
formatos y los tres caminos del caso.
