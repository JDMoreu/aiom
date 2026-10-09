# La API

El `.txt` es la puerta **humana**: escribir una pregunta sin saber JSON. Esto es la
puerta **de programa**: otro sistema manda la pregunta por HTTP y recibe JSON.

## Desplegarla

Necesita un `llama-server` con el endpoint `/v1/decision` ya levantado (ver
[`ARRANCAR.md`](ARRANCAR.md)); ella **no carga el modelo**, se conecta al que hay.

```bash
python api.py                 # escucha en 127.0.0.1:8100
python api.py --port 9000     # otro puerto
python api.py --ui            # además abre el navegador en la interfaz
python api.py --catalog catalogs/soporte.json   # cambia la persona de la vía de chat
```

Es un servidor HTTP de la biblioteca estándar de Python: **sin dependencias, sin
`requirements`, sin nada que instalar**. Escucha solo en `127.0.0.1`, así que no se
expone a la red. Y sirve también la interfaz web en el mismo proceso, así que no hay un
segundo servidor que arrancar.

| | |
|---|---|
| `AIOM_SERVER` | dónde está el `llama-server` (por defecto `http://127.0.0.1:8096`) |
| `AIOM_CATALOG` | qué catálogo usar, si no se pasa `--catalog` |
| `GET /docs` | la documentación de los endpoints, en JSON, desde la propia API |

## Consumirla

Se pregunta siempre al mismo endpoint, **declarando el formato**:

```bash
curl -X POST localhost:8100/ask -H "Content-Type: application/json" \
  -d '{"formato":"natural","entrada":"input: ...\n\nask: ...\nchoice:\n  si: ..."}'
```

Y desde Python, con la biblioteca estándar y sin instalar nada:

```python
import json, urllib.request

cuerpo = {"formato": "natural", "entrada": "input: ... / ask: ... / choice: ...",
          "comparar": True}
req = urllib.request.Request("http://127.0.0.1:8100/ask",
                             data=json.dumps(cuerpo).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.loads(r.read().decode())

print(d["decision"]["tiempo_ms"], d["decision"]["tokens"])   # 178.0  0
print(d["chat"]["tiempo_ms"], d["chat"]["tokens"])           # 2182.0 126
```

**Las cabeceras CORS van abiertas**, a propósito: es una herramienta local que solo
escucha en `127.0.0.1`, y así el fichero `web/index.html` se puede servir desde otro sitio
si hiciera falta.

> **Una cosa que conviene saber antes de meterle carga:** hay **un solo modelo y un solo
> proceso**, así que las peticiones se atienden de una en una. Si le mandas diez a la vez
> no van más rápido: hacen cola. Para medir tiempos, de una en una.

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

## Qué es el catálogo, y qué no

El catálogo (`catalogs/*.json`, se elige con `--catalog` o la variable `AIOM_CATALOG`) es
**un juego de campos preparado**. Tiene cuatro claves, y no todas se usan igual:

| clave | para qué | quién la usa |
|---|---|---|
| `chat_system` | la persona del chat | **todas** las llamadas de chat, en cualquier formato |
| `fields` | los campos del esquema | **solo** el formato `texto` |
| `instructions` | el prompt del modo decisión | **solo** el formato `texto` |
| `gate_field` | qué campo decide «¿es respondible?» | **solo** el formato `texto` |

**Si usas `natural` o `tipado` —que es lo que hace la interfaz— el catálogo no decide
nada**: tú traes el esquema en el cuerpo de la petición. Lo único que se sigue usando es
`chat_system`, la persona con la que contesta la vía de chat. Por eso se puede cambiar de
catálogo y ver cómo el chat cambia de registro sin tocar las preguntas.

Los dos que hay son **dos ejemplos** de juego de campos, para que el formato `texto` tenga
contra qué responder sin que escribas un esquema. `GET /catalog` devuelve el que esté
cargado.

### El formato de un campo

Cada campo del esquema se declara así:

```json
"magnitud": {
  "type": "enum",
  "choices": ["temperatura", "humedad", "bateria", "senal", "riego", "ninguna"],
  "description": "Sobre que variable pregunta el operador? Usa 'ninguna' si no menciona una."
}
```

| clave | cuándo | qué es |
|---|---|---|
| `type` | siempre | `boolean`, `enum`, `integer` o `number` |
| `description` | siempre | el enunciado de la pregunta: **es lo que el modelo lee** |
| `choices` | en `enum` | las opciones, en orden |
| `minimum` / `maximum` / `step` | en `integer` y `number` | el rango y el salto de la rejilla |
| `aggregate` | opcional | cómo se resume el campo cuando hay varios |

**No hay clave `examples`.** La hubo —consultas de ejemplo para calibrar dónde está la
frontera del `gate_field`— y **se midió: no sirve**. Alargar el enunciado con ellas no
ayuda: con ejemplos largos el `gate_field` empeora (3 de 5 casos se vuelven «no
respondible»), y con ejemplos cortos queda exactamente igual que sin ellos. Es la misma
lección que está en el README, comprobada aquí: **el texto de más diluye la pregunta**.

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

Agrupar es lo que hace rápida a la decisión: **N preguntas en una sola petición**, cuando
el chat necesita una por pregunta.

Pero hay un pero, y es importante. **Las preguntas se estorban entre sí**, y no todas
igual. Se separan solas en dos grupos:

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

El del chat es **la suma** de sus N peticiones, porque van una por pregunta: es lo que
se tarda en tener las N respuestas, que es justo lo que se compara.

## La interfaz

`GET /` sirve `web/index.html`: un solo fichero, sin dependencias ni compilación, que
usa esta misma API.

El caso y las preguntas se escriben **una sola vez**, y hay tres formas de hacerlo —
**por bloques**, en **lenguaje natural** o en **JSON tipado**— que son tres vistas del
mismo contenido, no tres sitios donde teclear por separado. Se cambia de pestaña y lo
escrito aparece en la otra forma. Con «Comparar» activado se pregunta lo mismo por las
dos vías y se ven juntas.

El **caso** puede ser un documento: se sube, se extrae su texto en el servidor y se
enseña una vista previa con lo que se extrajo (caracteres, palabras, páginas y el texto),
que es exactamente lo que recibe el modelo.

La **medida** —los números de las dos vías— vive **con la respuesta**, no en una banda
pegada arriba: son los números de esto que acabas de leer, y separarlos obligaba a mirar
en dos sitios para juntar el dato con su tiempo.

El **catálogo** no se enseña en la interfaz, pero sigue importando: la vía de chat usa su
*persona*. Con el catálogo de IoT por defecto, un caso de facturación hace que el chat
conteste como agente de campo. Para eso está `--catalog catalogs/soporte.json`.

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
