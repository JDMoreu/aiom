# La API

El `.txt` es la puerta **humana**: escribir una pregunta sin saber JSON. Esto es la
puerta **de programa**: otro sistema manda la pregunta por HTTP y recibe JSON.

Se levanta así (una terminal aparte del `llama-server`):

```bash
python api.py                 # escucha en 8100
python api.py --port 9000
```

Y se pregunta siempre al mismo endpoint, **declarando el formato**:

```bash
curl -X POST localhost:8100/ask -H "Content-Type: application/json" -d '{ ... }'
```

## Los tres formatos

El campo `formato` dice qué se manda. **No se adivina**: si falta o no es uno de los
tres, la API contesta con un error y la lista de los que acepta.

### 1. `texto` — una pregunta suelta, contra el catálogo

```json
{"formato": "texto", "question": "El sensor de humedad del predio 7 lleva dos días sin reportar.", "mode": "decision"}
```

Responde contra los campos que declara el **catálogo** (`--catalog`). `mode` es
`auto` (por defecto), `decision` o `chat`. Con `chat` la respuesta viene en prosa.

### 2. `natural` — el contenido de un `.txt`, entero

```json
{"formato": "natural", "entrada": "input: ...\n\nask: ...\nchoice:\n  a: ..."}
```

Trae su propio esquema en el texto, así que **no usa el catálogo**. Admite varias
preguntas separadas por `---`, y las resuelve todas en **una sola petición**.

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

Siempre la misma forma, sea cual sea el formato:

```json
{
  "formato": "natural",
  "n_preguntas": 3,
  "tiempo_ms": 158.0,
  "tokens": 0,
  "resultados": [
    {"campo": "q1", "tipo": "enum", "pregunta": "¿A qué área hay que enviar este correo?",
     "value": "facturacion", "probability": 0.665, "confidence": 0.450,
     "probabilities": {"soporte": 0.295, "facturacion": 0.665,
                       "comercial": 0.040, "otros": 0.000}}
  ]
}
```

En un `score` hay además **`niveles`**, con las etiquetas de la escala:

```json
{"campo": "q2", "tipo": "score", "pregunta": "¿En qué idioma está el documento?",
 "value": 0.0, "probability": 0.960, "confidence": 0.329,
 "niveles": ["espanol: idioma español", "ingles: idioma ingles", "otro: otro idioma"],
 "probabilities": {"0.0": 0.960, "1.0": 0.025, "2.0": 0.015}}
```

Hacen falta porque el motor devuelve un **número** (0, 1, 2…) y un `0` a secas no dice
nada: no hay forma de saber que ese 0 es «espanol». Los niveles van **de menor a
mayor y numerados desde 0**, así que el primero es `0`.

`tokens` es **0** en decisión: el valor sale de puntuar las opciones, no de escribir.
`confidence` no es la probabilidad de acertar, es lo concentrada que está la
distribución (ver el MANUAL, apartado 11).

En modo `chat` el resultado es distinto, porque no hay valores:

```json
{"resultados": [{"modo": "chat", "texto": "..."}], "tokens": 136}
```

## Comparar las dos vías

Con `"comparar": true` se corre **la misma pregunta por las dos vías** y vuelven
juntas. Se hace en el servidor y no en el cliente a propósito: así los dos tiempos son
de la **misma corrida** y se pueden comparar; midiéndolos en dos llamadas separadas
serían de momentos distintos.

```json
{"formato": "natural", "entrada": "input: ... ask: ... choice: ...", "comparar": true}
```

Y devuelve:

```json
{
  "formato": "natural",
  "comparar": true,
  "decision": {"peticiones": 1, "tiempo_ms": 151.0, "tokens": 0, "resultados": [ ... ]},
  "chat":     {"peticiones": 3, "tiempo_ms": 1502.0, "tokens": 119, "resultados": [ ... ]}
}
```

Funciona con los tres formatos: en `texto` la pregunta va al catálogo y al chat; en
`natural` cada pregunta del texto va a las dos vías; en `tipado` igual, usando el
`state.input` y las `instructions`.

## El documento como caso

El caso no tiene por que escribirse: puede ser un documento que ya existe. Se sube y
el texto que sale de él pasa a ser la `entrada`.

```
POST /documento        (el cuerpo en crudo, el nombre en la cabecera X-Nombre)
  -> {"texto": "...", "nombre": "carta.pdf", "tipo": "pdf",
      "caracteres": 3910, "palabras": 587, "lineas": 56}
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

## Por qué la ventaja se encoge con un documento largo

Es contraintuitivo y conviene tenerlo claro: **cuando el caso es un documento, la
diferencia entre las dos vías baja**. Medido aquí, con las mismas tres preguntas:

| caso | decisión | chat | razón |
|---|---|---|---|
| texto corto (128 caracteres) | 190 ms | 1451 ms | **7,6×** |
| documento (6086 caracteres) | 391 ms | 1048 ms | **2,7×** |

Y no es que el chat se vuelva mejor. Es que **cambia en qué se va el tiempo de cada uno**:

- **La decisión no escribe nada**, así que su tiempo es casi todo *leer*. Su prompt pasó
  de 451 a 1812 tokens y ella pasó de 78 a 367 ms — **4,7× más lenta**, en proporción
  al texto que tiene que leer. Es lo esperable: no puede ahorrarse leer el documento.
- **El chat se va en escribir.** Lee el documento también, pero su tiempo lo manda la
  prosa que genera. Y con un documento delante **tiende a escribir menos** (mediana de
  30 a 21 tokens en la misma pregunta), así que no crece — a veces incluso baja.

**El fondo del asunto:** la ventaja de la decisión es *no generar*. Pero leer el
documento no te lo ahorras en ninguna de las dos vías. Cuando el texto es corto, leer
es barato y el «0 tokens» es una ventaja enorme. Cuando el caso es un documento, leer
pasa a ser el grueso del tiempo de la decisión, y ahí la ventaja se estrecha.

**Dos avisos honestos:**

- El chat **no escribe siempre lo mismo**: en cinco corridas de la misma pregunta dio
  entre 18 y 34 tokens. Con un documento, esa variación pesa más en la razón, así que
  el «2,7×» es menos estable que el «7,6×».
- La decisión sigue teniendo lo suyo, y no es solo la velocidad: **devuelve valores con
  su probabilidad**, no prosa que hay que interpretar. Eso no se mide en milisegundos.

## Muchas preguntas a la vez: rápido, pero ojo

Agrupar es lo que hace rápida a la decisión: **doce preguntas en una sola petición**.
Medido sobre un currículum real (3910 caracteres), las mismas doce preguntas:

| | peticiones | tiempo | tokens |
|---|---|---|---|
| decisión | **1** | **510 ms** | **0** |
| chat | 12 | 6717 ms | 541 |

**13,2× menos**, y escala: el chat hace una petición por pregunta, la decisión una sola.

Pero hay un pero, y es importante. **Las preguntas se estorban entre sí**, y no todas
igual. Sobre el mismo currículum:

| pregunta | sola | en el lote de 12 |
|---|---|---|
| ¿Qué tipo de documento es? | curriculum 0.870 | **informe 0.788** |
| ¿Cuánta experiencia declara? | mucha 3.0 | **media 2.0** |
| ¿Cuántos empleos enumera? | 3.0 | **2.0** |
| ¿Menciona nube? | si 1.000 | si 0.990 |
| ¿Menciona hardware? | si 1.000 | si 0.957 |
| ¿Es para un reclutador? | True 0.618 | True 0.824 |

Se separan solas en dos grupos:

- **«¿aparece X?»** (contacto, estudios, nube, IA, publicaciones, hardware) → **no se
  mueven**. Agruparlas no cuesta nada.
- **De juicio** (qué tipo de documento es, cuánta experiencia, cuántos empleos) →
  **cambian** según con cuántas vayan.

No es azar: el lote de doce da exactamente lo mismo en tres corridas seguidas. Es un
efecto sistemático de meterlas juntas, no ruido. *Por qué* pasa no lo he medido — la
explicación que le veo es que los campos de «¿aparece X?» anclan al modelo en el
contenido del documento y los de juicio se dejan arrastrar, pero eso es una hipótesis
mía, no un dato.

**Lo práctico:** agrupa para velocidad y para las de «¿aparece X?»; si una respuesta de
juicio te importa, **pregúntala sola** — una petición de ~40 ms, y da `curriculum` 0.870
en vez de `informe` 0.788.

## Qué mide exactamente `tiempo_ms`

**Lo que tardas en recibir la respuesta: la ida y vuelta completa al modelo**, medida
en el cliente, desde que sale la petición hasta que se lee el cuerpo entero.

Y se mide **con el mismo reloj en las dos vías**, que es lo que hace la comparación
honesta. Esto no es un detalle: el servidor también informa de un `total_ms` propio,
que es lo que tarda por dentro y **no cuenta la red**. Medido en este equipo, `total_ms`
es entre **11 y 29 ms menor** que la ida y vuelta. Si se publicara decisión con
`total_ms` y chat con la ida y vuelta, se le estaría perdonando a una vía un coste que
a la otra se le cobra — y la ventaja saldría inflada.

El del chat es **la suma** de sus N peticiones, porque van una por pregunta: es lo que
se tarda en tener las N respuestas, que es justo lo que se compara.

**Dos avisos honestos sobre los números:**

- El **chat no es determinista** (genera prosa, temperatura 0,2). La misma pregunta dio
  entre 383 y 443 ms en seis corridas, con 33–37 tokens. La cifra de decisión es mucho
  más estable, porque no genera nada.
- Por eso **la razón «N× menos» no es una constante**: es una foto de esa corrida. Sirve
  para ver el orden de magnitud, no para afirmar un factor exacto.

## La interfaz

`GET /` sirve `web/index.html`: un solo fichero, sin dependencias ni compilación, que
usa esta misma API. Se elige el formato de la vía de decisión (natural o tipado), se
activa «Comparar» y se ven las dos respuestas con su tiempo y sus tokens.

En la cabecera aparece **el catálogo cargado**, y no es un adorno: la vía de chat usa
su *persona*. Con el catálogo de IoT por defecto, un caso de facturación hace que el
chat conteste como agente de campo. Para eso está `--catalog catalogs/soporte.json`.

## Los otros endpoints

| | |
|---|---|
| `GET /` | la interfaz |
| `GET /docs` | la documentación, en JSON |
| `GET /health` | estado de la API **y** del `llama-server` |
| `GET /catalog` | el catálogo cargado |

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
