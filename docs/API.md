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
