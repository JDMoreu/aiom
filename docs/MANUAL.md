# Manual de uso

Cómo escribir una decisión, ejecutarla y leer la respuesta. **Empieza por el
apartado 1 y sigue en orden**: cada uno se apoya en el anterior.

No hace falta saber nada de modelos ni de programación. Si sabes escribir un correo,
sabes escribir esto.

---

## 1. La idea: dos partes que siempre están

Toda consulta tiene **dos partes**:

| parte | qué es | ejemplo |
|---|---|---|
| **Entrada** | el texto que el modelo debe evaluar | el mensaje de un cliente |
| **Pregunta** | lo que quieres saber sobre esa entrada | ¿de qué equipo es? |

Y la pregunta termina en **una de estas tres formas**, según lo que quieras de vuelta.
Estos son los nombres de verdad, los que usa el código:

| quiero… | tipo | cabecera que escribo | me devuelve |
|---|---|---|---|
| elegir de una lista | **choice** | `choice:` | la opción elegida + probabilidad de cada una |
| poner algo en una escala | **score** | `score:` | **el nivel** (y, si lo quieres, una puntuación ponderada) |
| verdadero o falso | **noul** | `noul:` | `true` o `false`, con su probabilidad |

*(`noul` es la primitiva que define Jev. Dentro del programa el campo se llama
`boolean`, que es el tipo que entiende el motor — es el mismo concepto con el nombre
de cada capa.)*

---

## Quién decide de qué tipo es la pregunta

Esto es importante, y es fácil de confundir: **el modelo no lo decide.**

El modelo **solo puntúa las opciones que le das**. Quien mira tu texto y decide qué tipo
de pregunta es —**`choice`, `score` o `noul`**— es **`preguntar.py`**, leyendo la
**cabecera** que has escrito:

| si ve esta cabecera… | …monta un campo de tipo |
|---|---|
| `choice:` | **choice** — elegir una de una lista |
| `score:` | **score** — una escala |
| `noul:` | **noul** — verdadero o falso |

**La cabecera que escribes ES el tipo del campo.** No hay que declararlo además, y las
tres palabras son las mismas en todo el proyecto: en esta cabecera, en el formato tipado,
en los catálogos y en lo que devuelve la API.

Y si no escribes ninguna de las tres, el sistema no se queda sin responder: lo trata
como un verdadero o falso. (Si la pregunta es de texto libre, lo que quieres es el formato
`chat`, ver
apartado 8.)

---

## 2. Opciones (elegir de una lista)

Se escribe la cabecera `choice:` y debajo, una por línea, con el formato
`clave: descripción`. **La clave es lo que te va a devolver**; la descripción es para
que el modelo entienda cuál toca.

```
input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un
error 500 cada vez que intento iniciar sesión. Ya probé a reinstalarla y sigue igual.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas y planes
  otros: Todo lo demás
```

Ese texto se pega en el cliente web, o se manda a la API en el campo `entrada`. Preguntado
de verdad, `POST /ask` devuelve **esto**:

```json
{
  "resultados": [
    {
      "campo": "decision",
      "tipo": "choice",
      "pregunta": "¿A qué área hay que enviar este correo?",
      "value": "soporte",
      "probability": 1.0,
      "probabilities": {"soporte": 1.0, "facturacion": 0.0, "comercial": 0.0, "otros": 0.0},
      "confidence": 1.0
    }
  ],
  "tiempo_ms": 133.8,
  "tokens": 0,
  "n_preguntas": 1,
  "formato": "natural"
}
```

Qué leer:

- **`value` marca lo que eligió.** Aquí `soporte`.
- **`probabilities`** es la probabilidad de **cada** opción, y suman 1. `soporte` 1.0
  significa que no dudó; **`probability`** es la de la opción elegida.
- **`confidence`** es otra cosa: mide **lo concentrada** que está la probabilidad, no la
  probabilidad de acertar. 1.0 = todo en una opción. Cerca de 0 = empate.
- **`tokens: 0`**: aquí no se escribió texto. Por eso es rápido.
- La cabecera dice **solo la pregunta**. Las opciones van debajo, en su lista, para que
  no se confunda una opción con la respuesta.

> Si escribes **solo la clave** (una línea `soporte`, sin descripción) también
> funciona. La descripción ayuda al modelo, pero no es obligatoria.

---

## 3. Niveles (poner algo en una escala)

Cabecera `score:` y debajo los niveles **de menor a mayor**. El
sistema los numera solo: el primero es 0.

```
input: Aviso del sistema de monitorización: la aplicación completa lleva una hora
sin responder. Ningún usuario puede entrar ni usar ninguna función.

ask: ¿Qué gravedad tiene el incidente?
score:
  Aviso: no afecta al servicio
  Menor: afecta a unos pocos usuarios
  Grave: afecta a la mayoría
  Crítico: el servicio está caído del todo
```

Salida real (el JSON de `POST /ask`):

```json
{
  "resultados": [
    {
      "campo": "decision",
      "tipo": "score",
      "pregunta": "¿Qué gravedad tiene el incidente?",
      "value": 3.0,
      "probability": 0.8291,
      "probabilities": {"0.0": 0.0088, "1.0": 0.008, "2.0": 0.1541, "3.0": 0.8291},
      "confidence": 0.6221,
      "niveles": ["Aviso: no afecta al servicio",
                  "Menor: afecta a unos pocos usuarios",
                  "Grave: afecta a la mayoría",
                  "Crítico: el servicio está caído del todo"]
    }
  ],
  "tiempo_ms": 124.4,
  "tokens": 0,
  "n_preguntas": 1,
  "formato": "natural"
}
```

**Fíjate en `value: 3.0`.** Con cuatro niveles, «Crítico» es el 3, y ahí está la decisión.
Debajo tienes el reparto entero: 0.8291 en el nivel 3, 0.1541 en el 2 y un poco en los
otros dos.

**La API devuelve `value`, no una media.** Si quieres la **media ponderada** —que puede
caer entre dos niveles— se calcula desde `probabilities`:
`0×0.0088 + 1×0.008 + 2×0.1541 + 3×0.8291 = 2,80`. Sale 2,80 y no 3,00 porque reparte la
probabilidad entre los cuatro niveles.

**Pero para decidir, eso no hace falta.** Hay dos números y son cosas distintas:

| número | qué es | valor | ¿para qué? |
|---|---|---|---|
| `value` | **el nivel elegido** (el de mayor probabilidad), el que devuelve la API | `3.0` | **esto es la decisión** |
| la media ponderada | **la media**, que puede caer entre niveles; se calcula desde `probabilities` | `2.80` | ordenar casos finamente |

**Usa `value` por defecto.** Es el nivel y es lo que casi siempre quieres.

**La media solo aporta en dos casos**, y conviene saberlos antes de molestarse en
calcula­rla:

1. **Ordenar muchos casos.** Con `value`, todos los «nivel 2» empatan. La media
   distingue el 1.99 del 1.51 — útil para clasificar una lista.
2. **Detectar cuándo el modelo duda.** Si la media se aleja mucho del nivel elegido, es
   que había mezcla.

**Y seamos honestos con cuánto aporta**, medido sobre los 30 casos de score:

```
la media coincide con el nivel elegido (±0.05)   18 de 30   ← no aporta nada
se separan más de 0.25 niveles                    6 de 30
se separan más de 0.50 niveles                    1 de 30   ← aquí sí cambia el nivel
separación media                                  0.106 niveles
```

**En 6 de cada 10 casos da exactamente lo mismo que coger el mayor.** Es un matiz, no
el resultado. Si dudas, quédate con `value`.

---

## 4. Boolean (verdadero o falso, con su probabilidad)

Cabecera `noul:` y debajo qué significa cada uno. **Aquí es obligatorio poner `true:` y
`false:`**, porque si no, el modelo no sabe qué estás preguntando.

```
input: Un cliente escribe diciendo que han entrado en su cuenta desde otro país
y que no reconoce dos compras hechas esta madrugada.

ask: ¿Hay indicios de que la cuenta esté comprometida?
noul:
  false: No hay indicios de acceso no autorizado
  true: Hay indicios de acceso no autorizado
```

Salida real (el JSON de `POST /ask`):

```json
{
  "resultados": [
    {
      "campo": "decision",
      "tipo": "noul",
      "pregunta": "¿Hay indicios de que la cuenta esté comprometida?",
      "value": true,
      "probability": 0.8057,
      "probabilities": {"true": 0.8057, "false": 0.1943},
      "confidence": 0.2897
    }
  ],
  "tiempo_ms": 91.3,
  "tokens": 0,
  "n_preguntas": 1,
  "formato": "natural"
}
```

**Qué ha pasado aquí.** El caso sí da para decidir: hay un acceso desde otro país y dos
compras que el cliente no reconoce, así que el modelo dice que **sí** (0.8057), con una
confianza de 0.2897.

**Y ahora, un caso que en el papel no da para decidir.** El mismo tipo de pregunta,
pero con la entrada sin la información que hace falta:

```
input: Son las 22:30. Una aplicación de calendario quiere recordar una comida
de equipo el viernes. El usuario tiene activado el horario de descanso hasta las 07:00.

ask: ¿Debe esperar esta notificación hasta que termine el horario de descanso?
noul:
  false: El recordatorio es urgente y debe enviarse ahora
  true: Puede enviarse después sin perjudicar al usuario
```

Salida real:

```json
{
  "resultados": [
    {
      "campo": "decision",
      "tipo": "noul",
      "pregunta": "¿Debe esperar esta notificación hasta que termine el horario de descanso?",
      "value": false,
      "probability": 0.8202,
      "probabilities": {"true": 0.1798, "false": 0.8202},
      "confidence": 0.3203
    }
  ],
  "tiempo_ms": 113.0,
  "tokens": 0,
  "n_preguntas": 1,
  "formato": "natural"
}
```

**Qué ha pasado aquí.** El modelo también se decide —el «no», con 0.8202—, pero se lo
cree poco: la **confianza es 0.3203**. Y esa es la diferencia entre **probabilidad** y
**confianza**, la razón de que valga la pena mirar las dos:

| caso | probabilidad | confianza | qué significa |
|---|---|---|---|
| el de la cuenta | 0.8057 | 0.2897 | una preferencia, no una certeza |
| el del calendario | 0.8202 | 0.3203 | lo mismo: decide, pero sin aplomo |

**Fíjate en que una probabilidad alta no lo es todo.** Las dos pasan de 0.8 y las dos
confianzas se quedan cerca de 0.3: el reparto no está concentrado. 1.0 de confianza es
todo en una opción; cerca de 0 es un empate.

> **Nota de medición.** Este caso se redactó para que el modelo dudara, y la versión
> anterior de este manual traía un empate —0.514 con confianza 0.001—. En la corrida de
> hoy no empata: se decide por el «no» con 0.8202. Aquí queda lo que devuelve la API hoy,
> que es lo que se mide; el motor no da siempre el mismo reparto.

**Si usas esto en un programa**, la receta es: actúa solo si la probabilidad pasa de tu
umbral **y** la confianza pasa del suyo. Lo demás, a revisión humana.

> **Y aquí hay una lección de escritura de preguntas.** La del calendario se redactó con
> las dos opciones explicadas («el recordatorio es urgente» / «puede enviarse después»),
> y la entrada no dice si la comida de equipo es mañana o el viernes que viene: le falta
> contexto para contestarse sin adivinar. Es el tipo de sitio donde una recuperación de
> contexto (RAG) sí ayudaría — porque falta información, no sobra.

> **Y una advertencia medida en este mismo repositorio:** en `noul`, el orden en que
> escribes `true:` y `false:` pesa. El mismo caso, con las dos opciones **intercambiadas**
> de sitio, pasó de 0.463 (confianza 0.004) a 0.953 (confianza 0.728) para la misma
> respuesta semántica. Si te importa el resultado, **prueba las dos redacciones**.

> **Y otra, si el caso es un documento largo:** `noul` tiene un sesgo hacia el «no».
> Sobre un currículum de 3910 caracteres, con nueve preguntas del tipo «¿aparece *una
> fecha* en el documento?», acertó **4 de 9** — y en cinco de los seis casos donde la
> respuesta era sí dijo `False`, tres veces con probabilidad **0.99**. La confianza no
> avisa. Con `choice` y las opciones `si` / `no` acertó **7 de 9**.
>
> Para preguntar si algo aparece en un documento, usa `choice`. O pregunta por el dato
> concreto («¿en qué fechas trabajó en X?»), que así sí acertó.

---

## 5. Varias preguntas de una vez

Aquí está lo bueno. Se ponen **varias preguntas sobre la misma entrada**, separadas por
una línea con `---`. Se mandan **en una sola petición** y el modelo las evalúa todas.

```
input: Hola, el viernes pagué el plan anual y desde entonces la aplicación se cierra
sola cada vez que intento subir una foto. Necesito subir las fotos de un evento este
fin de semana.

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
  true: Sí, ya lo pagó
```

Salida real (el JSON de `POST /ask`):

```json
{
  "resultados": [
    {
      "campo": "q1", "tipo": "choice",
      "pregunta": "¿A qué área hay que enviar este correo?",
      "value": "soporte", "probability": 0.9597,
      "probabilities": {"soporte": 0.9597, "facturacion": 0.007, "comercial": 0.0115, "otros": 0.0218},
      "confidence": 0.8493
    },
    {
      "campo": "q2", "tipo": "score",
      "pregunta": "¿Qué urgencia tiene?",
      "value": 2.0, "probability": 0.8199,
      "probabilities": {"0.0": 0.0342, "1.0": 0.1459, "2.0": 0.8199},
      "confidence": 0.4911,
      "niveles": ["Baja: puede esperar",
                  "Media: conviene atenderlo esta semana",
                  "Alta: hay una fecha límite encima"]
    },
    {
      "campo": "q3", "tipo": "noul",
      "pregunta": "¿El cliente ya pagó el plan anual?",
      "value": true, "probability": 0.9495,
      "probabilities": {"true": 0.9495, "false": 0.0505},
      "confidence": 0.7114
    }
  ],
  "tiempo_ms": 145.7,
  "tokens": 0,
  "n_preguntas": 3,
  "formato": "natural"
}
```

**Fíjate: 145.7 ms para tres preguntas, frente a 133.8 ms para una.** Tres preguntas
costaron un **9% más**, no el triple. Porque el motor las puntúa **todas en la misma
pasada**. Y siguen siendo **0 tokens**.

**Y esto enseña lo más útil del manual: no todas las preguntas salen igual de bien.**

- La primera («¿a qué área?») sale **limpia**: `soporte` gana con 0.9597 y la confianza
  es 0.8493. **Esta se usa tal cual.**
- La tercera («¿ya pagó?») también sale limpia: `true` con 0.9495 y confianza 0.7114. El
  dato está en el texto y el modelo lo encuentra sin dudar.
- La segunda («¿qué urgencia?»), que es un `score`, es la que sale **más floja**: `value`
  2.0 con 0.8199 y confianza 0.4911. La escala tiene tres niveles y el modelo reparte más.

Es el patrón que hay que interiorizar: **la respuesta que sale limpia se usa; la que
sale con confianza baja, se revisa.**

> **Y ojo con el caso, no solo con la pregunta.** Si la entrada trae dos problemas, la
> pregunta tiene que decir cuál te importa. Con «¿a qué área hay que enviar este correo?»
> el modelo elige uno y no avisa de que había otro. Con «¿qué área corresponde al
> **fallo**?» la respuesta se habría separado.

### Y esto es lo que se gana frente al chat

Se puede comprobar a mano, con una sola petición. El caso es
`ejemplos/5_correo_soporte.txt` (una queja con cortes de conexión y un cobro duplicado).

Se manda a la API con `"comparar": true`, que corre las dos vías en la **misma corrida** —
que es lo que hace que los dos tiempos se puedan comparar—. Desde el cliente web se hace
con la casilla «Comparar»; desde la línea de comandos, con el contenido del fichero en
`entrada`:

```bash
python -c "import json;print(json.dumps({'formato':'natural','comparar':True,'entrada':open('ejemplos/5_correo_soporte.txt',encoding='utf-8').read()}))" > p.json
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" --data-binary @p.json
```

Las dos vías van sobre el mismo caso y con una sola petición cada una: la decisión resuelve
todas las preguntas de golpe y el chat contesta todo en una respuesta. Está explicado en
[`API.md`](API.md).

Lo que sale, medido aquí:

**Decisión** — 1 petición, 148 ms, **0 tokens**:

```json
{
  "resultados": [
    {"campo": "q1", "tipo": "choice", "pregunta": "¿A qué área hay que enviar este correo?",
     "value": "facturacion", "probability": 0.6844,
     "probabilities": {"soporte": 0.2664, "facturacion": 0.6844, "comercial": 0.0488, "otros": 0.0003},
     "confidence": 0.4505},
    {"campo": "q2", "tipo": "score", "pregunta": "¿Qué urgencia tiene?",
     "value": 2.0, "probability": 0.893,
     "probabilities": {"0.0": 0.0279, "1.0": 0.0791, "2.0": 0.893},
     "confidence": 0.6345,
     "niveles": ["Baja: puede esperar", "Media: conviene atenderlo esta semana", "Alta: hay una fecha límite encima"]},
    {"campo": "q3", "tipo": "noul", "pregunta": "¿Amenaza el cliente con darse de baja?",
     "value": true, "probability": 0.9513,
     "probabilities": {"true": 0.9513, "false": 0.0487},
     "confidence": 0.7194}
  ],
  "tiempo_ms": 148.0,
  "tokens": 0,
  "n_preguntas": 3
}
```

**Chat** — 1 petición, 1549 ms, 152 tokens, y en prosa:

> Aquí tienes las respuestas a tus preguntas:
>
> 1. **Área:** `facturacion` (El cliente menciona cortes de conexión, cobro de facturas y
>    la intención de darse de baja, lo que se enmarca principalmente en cobros y facturas).
> 2. **Urgencia:** `1` (Media: conviene atenderlo esta semana, ya que el cliente ha pasado
>    una semana sin solución y está a punto de cancelar el servicio).
> 3. **Amenaza con darse de baja:** `true` (El cliente lo menciona explícitamente al final
>    de su mensaje).

**Y aquí está lo que merece la pena mirar.** Las dos reciben el mismo caso y las mismas
reglas —las opciones y los niveles—, así que la diferencia no es *qué* contestan: coinciden
en el área (`facturacion`) y en la amenaza de baja (`true`). En la urgencia discrepan —la
decisión da `2` (Alta) y el chat `1` (Media)—, y eso también es información: el chat, al
redactar, se apoya en matices del texto.

**La diferencia es la forma.** La decisión da **el valor y el reparto entero**, y eso un
programa lo lee y decide con un umbral. El chat da **el valor con una justificación de tres
líneas**, y para usarlo habría que leerlo y sacarle el dato con expresiones regulares. Esa
es la diferencia de fondo: **las dos responden, pero solo una se puede consumir.**

*(La redacción del chat cambia de una corrida a otra. En la decisión el **ganador** es
estable —el mismo valor—, pero las probabilidades se mueven unas centésimas, así que los
números de arriba son los de la corrida en la que se midieron.)*

---

## 6. Lo mismo, pero tipado

Todo lo anterior se puede escribir también en **JSON estructurado**, que es el formato
de TypeSafe/Jev. Es para cuando un programa genera la consulta en vez de una persona.

Las equivalencias son estas:

| lenguaje natural | JSON |
|---|---|
| `ask:` | `instructions` |
| `choice:` + `clave: descripción` | `type: "choice"` + `criteria: {clave: descripción}` |
| `score:` | `type: "score"` + `criteria: [lista]` |
| `noul:` | `type: "noul"` + `criteria: {true:…, false:…}` |

El ejemplo 2, tipado:

```json
{
  "model": "typesafe/jev-1.13",
  "state": {
    "input": "Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un error 500 cada vez que intento iniciar sesión."
  },
  "questions": {
    "decision": {
      "type": "choice",
      "instructions": "¿A qué área hay que enviar este correo?",
      "criteria": {
        "soporte": "Fallos y errores del producto",
        "facturacion": "Cobros, facturas y reembolsos",
        "comercial": "Ventas y planes",
        "otros": "Todo lo demás"
      }
    }
  }
}
```

**Y aquí está el punto del repositorio:** ese JSON y el texto del apartado 2 **son la
misma consulta y dan el mismo resultado**. Ninguna de las dos formas acierta más que la
otra: son dos maneras de decir lo mismo al mismo modelo.

*Entonces, ¿para qué el JSON?* Para cuando lo escribe un programa. *¿Y por qué el
lenguaje natural?* Porque **cualquiera puede escribirlo sin conocer el esquema**, y eso
hace que se experimente mucho más. Por eso la puerta de entrada de este repositorio es
el lenguaje natural.

---

## 7. Las cabeceras

El estándar son cinco, cortas:

| sección | qué abre |
|---|---|
| `input:` | el caso. Va antes de la primera cabecera |
| `ask:` | la pregunta |
| `choice:` | las opciones, para elegir de una lista |
| `score:` | los niveles, de menor a mayor |
| `noul:` | el significado de `false` y de `true` |

Las tres del medio son las que **declaran el tipo**: `choice` es una elección, `score`
una escala y `noul` un verdadero o falso. No hay que deducirlo, se lee en la cabecera.

Las formas largas en español (`Entrada:`, `Pregunta:`, `Opciones:`,
`Niveles de puntuación:`, `Qué significa no o sí:`) **se siguen aceptando**, pero el
estándar es el corto. Y hay sinónimos sueltos por comodidad: `Estado:`, `Question:`,
`Choices:`, `Escala:`, `Sí o no:`.

Dos reglas que conviene conocer:

1. **La cabecera empieza en la columna cero.** Lo que va debajo va sangrado (con
   espacios delante). Así una opción llamada `pregunta:` no se confunde con la cabecera.
2. **La entrada va antes de la primera cabecera**, y solo cuenta la del primer bloque.

*(Si escribes un `ask:` sin ninguna de las tres, se trata como un verdadero o falso. Es el único
caso en que el tipo no se declara.)*

---

## 8. Qué pasa si la pregunta no es de estos tres tipos

Se puede preguntar algo que no sea ni una lista, ni una escala, ni un verdadero o falso — por
ejemplo «redáctame un resumen». Sin tipo, la pregunta se trata como un **verdadero o falso**:
la vía de decisión necesita un conjunto finito y no puede devolver texto libre.

Para eso está el formato **`chat`**: una pregunta suelta y el modelo escribe la respuesta.
No es una decisión, es prosa, y por eso es el otro camino.

---

## 9. Ejecutarlo

Hay dos formas de preguntar, y ninguna es por consola: **el cliente web** (lo cómodo para
una persona) y la **API** (para un programa).

```bash
# la API y el cliente web, en el mismo proceso. Abre http://127.0.0.1:8100/
pip install fastapi "uvicorn[standard]"
python api.py
```

En el cliente web se escribe el caso y las preguntas —por bloques, en lenguaje natural o en
JSON— y se pregunta. Para mandarlo por la API, con el contenido en el campo `entrada`:

```bash
# el contenido de un fichero, en JSON (con Python, que respeta los acentos)
python -c "import json;print(json.dumps({'formato':'natural','entrada':open('ejemplos/1_opciones.txt',encoding='utf-8').read()}))" > p.json
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" --data-binary @p.json
```

Con el caso sacado de un documento son **dos llamadas**: primero `POST /documento` y luego
`POST /ask` con ese texto en el campo `documento`. Los ficheros
`ejemplos/6_preguntas_sobre_un_documento.txt` y `ejemplos/7_preguntas_curriculum.txt` traen
solo las preguntas, listos para eso; el ejemplo completo está en
[`EJEMPLOS.md`](EJEMPLOS.md).

Antes hace falta el servidor:

```bash
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
```

Para probar tus propias preguntas **no hay que tocar código**: se escribe el texto, se pega
en el cliente web (o se manda a la API) y se pregunta. Los ejemplos de este manual están en
`ejemplos/`.

---

## 10. Resumen: los tres tipos de un vistazo

**Entrada** (siempre la misma, cambia solo la cabecera):

```
input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un
error 500 cada vez que intento iniciar sesión.
```

| tipo | cabecera | lo que escribes debajo |
|---|---|---|
| **choice** | `choice:` | `soporte: Fallos y errores del producto` (una por línea, `clave: descripción`) |
| **score** | `score:` | `Aviso: no afecta al servicio` (una por línea, de menor a mayor) |
| **noul** | `noul:` | `true: ...` y `false: ...` |

**Y esto es lo que devuelve cada uno**, ejecutado de verdad:

**choice** → da una **clave de tu lista**

```json
{"campo": "decision", "tipo": "choice",
 "pregunta": "¿A qué área hay que enviar este correo?",
 "value": "soporte", "probability": 1.0,
 "probabilities": {"soporte": 1.0, "facturacion": 0.0, "comercial": 0.0, "otros": 0.0},
 "confidence": 1.0}
```

**score** → da un **número de nivel** (la media ponderada se calcula desde `probabilities`)

```json
{"campo": "decision", "tipo": "score",
 "pregunta": "¿Qué gravedad tiene el incidente?",
 "value": 3.0, "probability": 0.8291,
 "probabilities": {"0.0": 0.0088, "1.0": 0.008, "2.0": 0.1541, "3.0": 0.8291},
 "confidence": 0.6221,
 "niveles": ["Aviso: no afecta al servicio",
             "Menor: afecta a unos pocos usuarios",
             "Grave: afecta a la mayoría",
             "Crítico: el servicio está caído del todo"]}
```

**noul** → da un **`true` o `false`**, con su probabilidad

```json
{"campo": "decision", "tipo": "noul",
 "pregunta": "¿Hay indicios de que la cuenta esté comprometida?",
 "value": true, "probability": 0.8057,
 "probabilities": {"true": 0.8057, "false": 0.1943},
 "confidence": 0.2897}
```

**Las tres devuelven lo mismo por dentro**: un valor (`value`) y **la probabilidad de
cada opción posible** (`probabilities`). Cambia el tipo del valor — texto, número o
booleano — pero la estructura es idéntica. Eso es lo que permite tratarlas juntas.

---

## 11. Los campos que devuelve, y cuáles se pueden deducir

El servidor devuelve seis o siete campos por pregunta. **Solo uno es el dato; el resto
está calculado a partir de él.** Verificado comparando cada campo con lo que sale de
recalcularlo:

| campo | qué es | ¿aporta algo nuevo? |
|---|---|---|
| **`probabilities`** | la probabilidad de **cada** opción | **sí — es el único dato crudo** |
| `value` | la opción con más probabilidad | no, es el mayor de `probabilities`… **pero es la respuesta** |
| `probability` | la probabilidad de la opción elegida | **no: es `probabilities[value]`, copiado** |
| `confidence` | 1 − H(p)/ln(n) | no, sale de `probabilities` (ver abajo) |
| `interval_p10_p90` | los cuantiles 10%–90% (solo en score) | no, salen de `probabilities` |
| `scored_nodes`, `tree` | detalles internos del motor | no son decisiones |

**Todo se calcula desde `probabilities`.** Eso no significa que sobren: `value` es la
respuesta y ahorra tener que buscar el mayor. Pero conviene saber qué es dato y qué es
resumen, para no tratar un resumen como si fuera información nueva.

### Cómo se calcula la confianza (y qué NO es)

**No es «el mayor menos los otros».** Esa operación da otra cosa —el *margen*, cuánto
gana el primero— y no es lo que devuelve el servidor. Lo que devuelve es la **entropía
normalizada**:

```
confidence = 1 − H(p) / ln(n)

H(p) = −Σ pᵢ · ln(pᵢ)     (entropía de Shannon del reparto)
n                          (número de opciones)
```

Con el ejemplo de la gravedad del incidente, cuyas probabilidades son
`0.0088, 0.008, 0.1541, 0.8291`:

```
H(p)      = −(0.0088·ln0.0088 + 0.008·ln0.008 + 0.1541·ln0.1541 + 0.8291·ln0.8291)
          = 0.5238
ln(4)     = 1.3863
H/ln(4)   = 0.3779          ← entropía normalizada: 0 = un pico, 1 = reparto plano
confianza = 1 − 0.3779 = 0.6221
```

*(La cuenta cuadra con la `confidence` que devuelve la API, 0.6221.)*

Se ve mejor en los extremos, que es donde se entiende qué mide:

| reparto | H(p) | confianza | qué significa |
|---|---|---|---|
| todo en una opción | 0 | **1.000** | no dudó nada |
| 70 / 30 | 0.61 | 0.559 | prefiere una, con reservas |
| empate a dos | 0.69 | 0.500 | dos opciones indistinguibles |
| empate a cuatro | 1.39 | **0.000** | no tiene ni idea |

**Y por eso la confianza y la probabilidad son distintas.** La probabilidad dice *qué
prefiere*; la confianza dice *cuánto se lo cree*, mirando **todo** el reparto y no solo
el ganador.

### Dónde aporta y dónde no

Aquí hay un caso que merece la pena porque **depende del tipo**:

- **En `noul`, la confianza no aporta NADA.** Con dos opciones (n=2, `ln(2)`) la
  confianza queda determinada por la probabilidad: no hay información nueva. Comprobado:
  con `p = 0.534130` la fórmula da `0.003364`, y es exactamente lo que devuelve el
  servidor. Si tienes la probabilidad, la confianza es un cálculo de más.
- **En `choice`, sí aporta.** Dos casos con la probabilidad mayor **casi igual** dan
  confianzas distintas, porque el reparto del resto cambia:

```
  probabilidad mayor 0.714  ->  confianza 0.394
  probabilidad mayor 0.722  ->  confianza 0.455
```

  Con solo la probabilidad mayor esos dos casos parecerían el mismo; con la confianza se
  distingue cuál es más de fiar.

**La regla:** en noul, quédate con la probabilidad. En choice, mira las dos.

Y esto deja en su sitio lo de la media ponderada del apartado 3: **es una operación
derivada, igual que `value`, `probability` y `interval_p10_p90`.** La diferencia no es que
unas sean «de más» y otras no, sino cuál necesitas: `value` casi siempre, la media casi
nunca.

---

## 12. Las cinco cosas que hay que recordar

1. **Entrada** + **Pregunta** + **una cabecera** que dice qué tipo es. La cabecera es
   lo único que hace falta para declarar el tipo: no hay que escribir JSON.
2. **Choice** devuelve una clave; **score** un número; **noul** un `true`/`false`.
   Los tres devuelven además **la probabilidad de cada opción y una confianza**.
3. **Probabilidad** es qué prefiere; **confianza** es cuánto se lo cree. Son distintas y
   las dos importan.
4. Varias preguntas se separan con `---` y **cuestan casi lo mismo** que una.
5. Un fallo raro suele ser **de la pregunta**, no del modelo: quitar la descripción de
   un campo lo arregla más veces de las que parece.
