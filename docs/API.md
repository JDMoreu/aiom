# La API

El `.txt` es la puerta **humana**: escribir una pregunta sin saber JSON. Esto es la
puerta **de programa**: otro sistema manda la pregunta por HTTP y recibe JSON.

## Desplegarla

Necesita un `llama-server` con el endpoint `/v1/decision` ya levantado (ver
[`ARRANCAR.md`](ARRANCAR.md)); ella **no carga el modelo**, se conecta al que hay.

```bash
python api.py                 # escucha en 127.0.0.1:8100
python api.py --port 9000     # otro puerto
python api.py --ui otro.html  # sirve otra interfaz en vez de web/index.html
```

Es **FastAPI sobre uvicorn**, así que la API necesita instalar algo:

```bash
pip install fastapi "uvicorn[standard]"
python api.py                    # escucha en 127.0.0.1:8100
```

Escucha solo en `127.0.0.1`, así que no se expone a la red. Y sirve también la interfaz
web en el mismo proceso, así que no hay un segundo servidor que arrancar.

| | |
|---|---|
| `AIOM_SERVER` | dónde está el `llama-server` (por defecto `http://127.0.0.1:8096`) |

## Consumirla

Se pregunta siempre al mismo endpoint, **declarando el formato**:

```bash
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "natural",
  "entrada": "input: Llevo desde ayer sin poder entrar: me sale un error 500.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás"
}'
```

Y desde Python, con la biblioteca estándar y sin instalar nada más:

```python
import json, urllib.request

ENTRADA = """input: Llevo desde ayer sin poder entrar: me sale un error 500.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  otros: Todo lo demás"""

peticion = urllib.request.Request(
    "http://127.0.0.1:8100/ask",
    data=json.dumps({"formato": "natural", "entrada": ENTRADA}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(peticion, timeout=600) as r:
    respuesta = json.loads(r.read().decode())

for r_ in respuesta["resultados"]:
    print(r_["campo"], "=", r_["value"], r_["probabilities"])
```

Y hay un **ejemplo completo y ejecutable**, que enseña las tres formas de darle el caso
—escrito, sacado de un documento, o en JSON— y los dos endpoints que hay que llamar. Lleva
**seis preguntas, dos de cada tipo**, y las resuelve todas en una petición:

```bash
python ejemplos/integrar.py                # el caso, escrito
python ejemplos/integrar.py carta.pdf      # el caso, sacado de un documento
python ejemplos/integrar.py --tipado       # el mismo caso, en JSON tipado
python ejemplos/integrar.py --chat         # una pregunta suelta, en prosa
python ejemplos/integrar.py --comparar     # y además, lo mismo al chat
```

**Todos los ejemplos de consulta están en [`EJEMPLOS.md`](EJEMPLOS.md)**: los tres
formatos, los tres tipos de pregunta, con documento, la comparación y desde el
navegador. Cada uno con la **entrada y la salida de verdad**, tal cual las devuelve el
servidor. Sin un solo `...`.

Son **dos endpoints**, y cada uno hace una cosa:

| | |
|---|---|
| `POST /documento` | le mandas los bytes del fichero y te devuelve su texto |
| `POST /ask` | le mandas el caso y las preguntas, y te devuelve los valores |

Con un documento son **dos llamadas**: primero a `/documento` para sacarle el texto, y
luego a `/ask` con ese texto en el campo `documento`. Con el caso escrito es **una
sola**: el caso va dentro de `entrada`, junto a las preguntas. **El endpoint de la
pregunta es el mismo en los dos casos**, que es lo que conviene recordar.

**Las cabeceras CORS van abiertas**, a propósito: es una herramienta local que solo
escucha en `127.0.0.1`, y así el fichero `web/index.html` se puede servir desde otro sitio
si hiciera falta.

> **Una cosa que conviene saber antes de meterle carga:** hay **un solo modelo y un solo
> proceso**, así que las peticiones se atienden de una en una. Si le mandas diez a la vez
> no van más rápido: hacen cola. Para medir tiempos, de una en una.

## Los tres formatos

El campo `formato` dice qué se manda. **No se adivina**: si falta o no es uno de los
tres, la API contesta con un error y la lista de los que acepta.

### 1. `chat` — una pregunta suelta, en prosa

Aquí no hay campos ni probabilidades: **el modelo escribe**. Es el camino para lo que no es
una decisión (redactar, explicar, resumir), y acepta `documento` igual que los otros dos.
`comparar` no aplica aquí: las dos vías serían la misma cosa.

```json
{"formato": "chat", "question": "Explícame en dos frases qué es una red de sensores"}
```

Y devuelve:

```json
{"resultados": [{"via": "chat",
                 "texto": "Una red de sensores es un sistema tecnológico que conecta varios dispositivos para recopilar, transmitir y procesar datos de forma automática..."}],
 "tiempo_ms": 808.0, "tokens": 74, "n_preguntas": 1, "formato": "chat"}
```

### 2. `natural` — el contenido de un `.txt`, entero

```json
{"formato": "natural", "entrada": "input: Llevo desde ayer sin poder entrar: me sale un error 500.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás"}
```

Trae su propio esquema en el texto. Admite varias preguntas separadas por `---`, y las
resuelve todas en **una sola petición**.

Y devuelve un `resultado` por pregunta, con el valor y el reparto entero (la respuesta
completa está en «Lo que devuelve», más abajo):

```json
{"resultados": [{"campo": "q1", "tipo": "choice",
                 "pregunta": "¿A qué área hay que enviar este correo?",
                 "value": "soporte", "probability": 1.0,
                 "probabilities": {"soporte": 1.0, "facturacion": 0.0,
                                   "comercial": 0.0, "otros": 0.0},
                 "confidence": 1.0}],
 "tiempo_ms": 117.7, "tokens": 0, "n_preguntas": 3, "formato": "natural"}
```

### 3. `tipado` — el formato de TypeSafe, tal cual

```json
{"formato": "tipado",
 "state": {"input": "Me cobraron dos veces la suscripción. ¿Pueden ayudarme?"},
 "questions": {"decision": {"type": "choice",
                            "instructions": "¿Qué equipo debe atenderlo?",
                            "criteria": {"billing": "Pagos y reembolsos",
                                         "technical": "Errores e integraciones"}}}}
```

`questions` admite **varias**: cada una es un campo del esquema y todas se resuelven en
la misma petición, igual que en el formato natural.

Y devuelve **exactamente lo mismo** que el natural, porque el esquema que recibe el modelo
es idéntico: mismos valores, mismas probabilidades. Solo cambia el nombre de cada campo, si
tú lo cambias.

## El chat no lleva persona de dominio, y es a propósito

Contesta como **asistente genérico**: la vía de decisión es la que está diseñada para la
tarea, y el chat es el listón con el que se compara. Para que la comparación diga algo,
tiene que ser un LLM corriente y no un agente ya especializado en el tema.

### El formato de un campo

Cada campo del esquema se declara así:

```json
"magnitud": {
  "type": "choice",
  "choices": ["temperatura", "humedad", "bateria", "senal", "riego", "ninguna"],
  "description": "Sobre que variable pregunta el operador? Usa 'ninguna' si no menciona una."
}
```

**Los tipos son tres, y se llaman igual en todo el proyecto:**

- **`choice`** — elegir una de una lista (`choices`, en orden)
- **`score`** — una escala o un número (`minimum`, `maximum`, `step`)
- **`noul`** — verdadero o falso

**El motor de llama-server habla otro idioma por dentro** (`enum`, `number`, `boolean`), y
esa diferencia se resuelve en **un solo sitio**: el mapa `AL_MOTOR` de `aiom.py`. En
ningún otro fichero del repositorio aparecen esos nombres, ni hay que saberlos para
escribir un esquema. Si escribes un tipo que no existe, el error te dice cuáles hay.

## Los dos formatos dan lo mismo

`natural` y `tipado` son dos maneras de decir lo mismo, y devuelven los mismos valores.
Con el mismo caso y los mismos nombres de campo, el esquema que recibe el modelo es
**idéntico byte a byte**.

Hay un detalle que conviene saber: **el nombre del campo también llega al modelo**. Si
en un formato llamas `area` al campo y en el otro `q1`, los valores salen iguales pero
las probabilidades bailan un poco. No es un error; es que el nombre forma parte del
enunciado que ve el modelo.

*(El formato natural añade además una clave `pregunta` a cada campo, para poder mostrar
el enunciado por pantalla. Se comprobó que **no afecta** al resultado.)*

## Lo que devuelve

Los dos formatos de decisión devuelven **la misma forma**. Esta es una respuesta de
verdad, con tres preguntas de los tres tipos en una sola petición:

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

En un `score` hay además **`niveles`**, con las etiquetas de la escala:

```json
{"campo": "q2", "tipo": "score", "pregunta": "¿Qué urgencia tiene?",
 "value": 2.0, "probability": 0.7025, "confidence": 0.2586,
 "niveles": ["Baja: puede esperar",
             "Media: conviene atenderlo esta semana",
             "Alta: hay una fecha límite encima"],
 "probabilities": {"0.0": 0.1575, "1.0": 0.1401, "2.0": 0.7025}}
```

Hacen falta porque el motor devuelve un **número** (0, 1, 2…) y un `2.0` a secas no dice
nada: no hay forma de saber que ese 2 es «Alta». Los niveles van **de menor a mayor y
numerados desde 0**, así que el primero es `0`.

Las probabilidades van **redondeadas a 4 decimales**: el motor las devuelve con toda la
precisión del float (`0.9999997615814209`), y eso no lo lee nadie.

`tokens` es **0** en decisión: el valor sale de puntuar las opciones, no de escribir.
`confidence` no es la probabilidad de acertar, es lo concentrada que está la
distribución (ver el MANUAL, apartado 11).

En el formato `chat` el resultado es distinto, porque no hay valores: la respuesta es la
prosa, entera, en un solo campo, y `via` dice de dónde viene.

```json
{"formato": "chat", "tokens": 74, "n_preguntas": 1,
 "resultados": [{"via": "chat",
                 "texto": "Una red de sensores es un sistema tecnológico..."}]}
```

## Comparar las dos vías

Con `"comparar": true` se corre **la misma pregunta por las dos vías** y vuelven
juntas. Se hace en el servidor y no en el cliente a propósito: así los dos tiempos son
de la **misma corrida** y se pueden comparar; midiéndolos en dos llamadas separadas
serían de momentos distintos.

```json
{"formato": "natural", "entrada": "input: Llevo desde ayer sin poder entrar: me sale un error 500.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás", "comparar": true}
```

Y devuelve:

```json
{
  "formato": "natural",
  "comparar": true,
  "decision": {"peticiones": 1, "tiempo_ms": 72.0, "tokens": 0, "resultados": [ ... ]},
  "chat":     {"peticiones": 1, "tiempo_ms": 4418.0, "tokens": 446, "resultados": [ ... ]}
}
```

Funciona con los **dos formatos de decisión**: en `natural` cada pregunta del texto va a las
dos vías; en `tipado` igual, usando el `state.input` y las `instructions`. En `chat` no
aplica, porque las dos vías serían la misma cosa.

## El documento como caso

El caso no tiene por que escribirse: puede ser un documento que ya existe. Se sube y
el texto que sale de él pasa a ser la `entrada`.

```
POST /documento        (el cuerpo en crudo, el nombre en la cabecera X-Nombre)
  -> {"texto": "...", "nombre": "carta.pdf", "tipo": "pdf",
      "caracteres": 3925, "palabras": 587, "lineas": 71,
      "paginas": 1, "paginas_con_texto": 1, "paginas_con_ocr": 0,
      "paginas_ilegibles": 0, "paginas_sin_texto": 0}
```

Y luego se pregunta con normalidad, mandando `"documento": "<ese texto>"` junto a la
`entrada`. El documento **manda sobre el `input:`** del texto y sobre el `state.input`
del formato tipado.

Qué se puede leer:

| | |
|---|---|
| `.txt` `.md` `.csv` `.json` `.log` | tal cual, sin instalar nada |
| `.docx` | sin instalar nada: un .docx es un ZIP y se lee su XML |
| `.pdf` | hace falta `pip install pymupdf` |

El `.doc` y el `.rtf` antiguos no se leen; hay que convertirlos antes. Se dice cuál es
el problema en vez de devolver texto a medias.

### Un PDF no siempre trae texto que se pueda leer

Y eso no se puede tapar con un `try`. Hay dos casos, y se tratan distinto:

- **Páginas que son un escaneo.** No tienen capa de texto: la página *es* una imagen.
  Esas van al **OCR** y, si sale texto, se usa. Se cuentan en `paginas_con_ocr`.
- **Páginas con fuentes sin traducir.** El PDF trae una fuente *Type3* —los glifos están
  dibujados— y ninguna tabla que diga qué letra es cada uno. pymupdf no puede inventarlo
  y devuelve los códigos internos de la fuente, que no son letras. Esas **se tiran**, y
  se cuentan en `paginas_ilegibles`.

El OCR es `rapidocr-onnxruntime`, también opcional:

```bash
pip install rapidocr-onnxruntime     # ~100 MB, y ~2 s por página
```

Solo se usa **cuando una página no tiene texto**, así que un PDF normal no paga ese
tiempo. Y se dice siempre de dónde salió cada página, porque un texto leído de una imagen
**puede traer errores**:

```json
"aviso": "de 17 paginas: 1 con texto propio; 13 leidas con OCR (eran escaneos, el texto
          puede traer errores); 3 con texto ilegible (glifos de una fuente sin traducir)."
```

Los números cuadran con `paginas`: `paginas_con_texto + paginas_con_ocr +
paginas_ilegibles + paginas_sin_texto == paginas`. Si una página no sale en ninguno de
los cuatro, es un fallo de la cuenta y hay que mirarlo.

Si **ninguna** página se puede leer, `POST /documento` contesta con un `400` y lo dice
—incluido si el OCR no está instalado— en vez de devolver un texto vacío o a medias.

## Un aviso medido: preguntar «¿aparece X?» con `noul` falla

Esto se midió sobre un documento largo (un currículum de 3910 caracteres) con nueve
preguntas del tipo «¿aparece *una fecha* en el documento?», donde la respuesta correcta
se comprobó en el texto extraído:

| tipo | aciertos |
|---|---|
| `noul` | **4 de 9** |
| `choice` con sí/no como opciones | **7 de 9** |

Y lo preocupante no es solo que falle: es que **falla con seguridad**. En cinco de los
seis casos donde la respuesta era sí, `noul` dijo `False` con probabilidad entre 0,59 y
**0,99**. La confianza no avisa de este error.

**Por eso, para preguntar si algo aparece en un documento, usa `choice`:**

```
ask: ¿Aparecen fechas en el documento?
choice:
  si: Sí, aparece alguna fecha
  no: No aparece ninguna
```

O pregunta por el dato concreto («¿en qué fechas trabajó en X?») en vez de por su
existencia: así acertó.

*(Son nueve preguntas sobre un documento, no un estudio. Es una señal fuerte, no una
ley — pero la dirección es clara y el error es del tipo que hace daño: una respuesta
segura y equivocada.)*

## Cómo se comportan las dos vías

Tres cosas que se ven al comparar y conviene tener claras:

- **El chat no es determinista.** Genera prosa, así que la misma pregunta da respuestas de
  largo distinto y tiempos que bailan. La decisión no baila: no genera nada.
- **La razón «N× menos» no es una constante**, es una foto de esa corrida. Sirve para ver
  el orden de magnitud, no para afirmar un factor exacto.
- **Con un documento largo la ventaja se estrecha**, y es contraintuitivo. La decisión no
  escribe, así que su tiempo es casi todo *leer* — y leer el documento **no te lo ahorras
  en ninguna de las dos vías**. Cuando el caso es corto, leer es barato y el «0 tokens»
  pesa mucho; cuando el caso es un documento, leer pasa a ser el grueso de la decisión.

Y lo que la decisión da y no se mide en milisegundos: **valores con su probabilidad**, no
prosa que hay que interpretar.

## Muchas preguntas a la vez: rápido, pero ojo

**Las dos vías reciben la misma entrada y en una sola petición**: el caso y todas las
preguntas juntas. Es lo que hace la comparación justa — al chat no se le repite el caso
por pregunta, que sería medirle el peor caso posible.

Dicho eso, **las preguntas se estorban entre sí** en la decisión, y no todas igual. Se
separan solas en dos grupos:

- **«¿aparece X?»** (¿menciona contacto? ¿estudios? ¿nube?) → **no se mueven**. Agruparlas
  no cuesta nada.
- **De juicio** (qué tipo de documento es, cuánta experiencia, cuántos empleos) →
  **cambian** según con cuántas vayan.

Es un efecto sistemático de meterlas juntas, no ruido. *Por qué* pasa no está medido — la
explicación que le veo es que los campos de «¿aparece X?» anclan al modelo en el contenido
del documento y los de juicio se dejan arrastrar, pero eso es una hipótesis, no un dato.

**Lo práctico:** agrupa para velocidad y para las de «¿aparece X?»; si una respuesta de
juicio te importa, **pregúntala sola**.

## Qué mide exactamente `tiempo_ms`

**Lo que tardas en recibir la respuesta: la ida y vuelta completa al modelo**, medida
en el cliente, desde que sale la petición hasta que se lee el cuerpo entero.

Y se mide **con el mismo reloj en las dos vías**, que es lo que hace la comparación
honesta. Esto no es un detalle: el servidor también informa de un `total_ms` propio,
que es lo que tarda por dentro y **no cuenta la red**. Si se publicara la decisión con
`total_ms` y el chat con la ida y vuelta, se le estaría perdonando a una vía un coste que
a la otra se le cobra — y la ventaja saldría inflada.

El del chat es **su única petición**: las dos vías leen la misma entrada una sola vez, así
que lo que se compara es lo que cada una tarda en resolverla.

## La interfaz

`GET /` sirve `web/index.html`: un solo fichero, sin dependencias ni compilación, que
usa esta misma API.

El caso y las preguntas se escriben **una sola vez**, y hay tres formas de hacerlo —
**por bloques**, en **lenguaje natural** o en **JSON**— que son tres vistas del
mismo contenido, no tres sitios donde teclear por separado. Se cambia de pestaña y lo
escrito aparece en la otra forma. Con «Comparar» activado se pregunta lo mismo por las
dos vías y se ven juntas.

El **caso** puede ser un documento: se sube, se extrae su texto en el servidor y se
enseña una vista previa con lo que se extrajo (caracteres, palabras, páginas y el texto),
que es exactamente lo que recibe el modelo.

La **medida** —los números de las dos vías— vive **con la respuesta**, no en una banda
pegada arriba: son los números de esto que acabas de leer, y separarlos obligaba a mirar
en dos sitios para juntar el dato con su tiempo.

El **chat no lleva persona de dominio**: contesta como asistente genérico, para que la
comparación con la decisión sea contra un LLM corriente y no contra un agente ya
especializado en el tema.

## Los otros endpoints

| | |
|---|---|
| `GET /` | la interfaz |
| `GET /ui` | lo mismo: alias de `/`, por si se escribe |
| `GET /index.html` | lo mismo: alias de `/` |
| `GET /docs` | **Swagger**: la documentación *y* las pruebas de la API |
| `GET /redoc` | lo mismo, en el formato de ReDoc |
| `GET /openapi.json` | el esquema, para generar un cliente |
| `GET /health` | estado de la API **y** del `llama-server` |

`/docs` es Swagger desde que la API es FastAPI. Ahí está la guía de los tres formatos y
un botón para probar cada uno sin escribir una línea de código: se elige un ejemplo, se
cambia el texto y se lanza. La lista de endpoints que había antes en JSON no la usaba
nadie, y esta hace lo mismo y además ejecuta.

## Cuando algo va mal

Nunca devuelve un 200 con basura dentro. Cada fallo tiene su código:

| código | cuándo |
|---|---|
| `400` | el cuerpo no es JSON, falta el campo del formato, o el formato no existe |
| `404` | la ruta no es `/ask` |
| `502` | el `llama-server` contestó con error |
| `503` | el `llama-server` no está levantado (lo dice `GET /health`) |

## Probarlo a mano

```bash
# el estado
curl -s localhost:8100/health

# el formato natural, con un caso del repositorio
python -c "import json;print(json.dumps({'formato':'natural','entrada':open('ejemplos/5_correo_soporte.txt',encoding='utf-8').read()}))" > p.json
curl -s -X POST localhost:8100/ask -H "Content-Type: application/json" --data-binary @p.json
```
