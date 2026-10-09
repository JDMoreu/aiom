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
| elegir de una lista | **choice** | `Opciones:` | la opción elegida + probabilidad de cada una |
| poner algo en una escala | **score** | `Niveles de puntuación:` | **el nivel** (y, si lo quieres, una puntuación ponderada) |
| un sí o un no | **boolean** | `Qué significa no o sí:` | `true` o `false`, con su probabilidad |

*(El tipo `boolean` es el que Jev llama **noul**, y es el que el programa muestra por
pantalla como **PROBABILITY**.)*

---

## Quién decide de qué tipo es la pregunta

Esto es importante, y es fácil de confundir: **el modelo no lo decide.**

El modelo **solo puntúa las opciones que le das**. Quien mira tu texto y decide «esto
es un choice» es **`preguntar.py`**, leyendo **la cabecera** que has escrito:

| si ve esta cabecera… | …monta un campo de tipo |
|---|---|
| `Opciones:` | `enum` → **choice** |
| `Niveles de puntuación:` | `number` → **score** |
| `Qué significa no o sí:` | `boolean` → **boolean** |

Después traduce eso al esquema del endpoint y el modelo responde dentro de ese esquema.
**Por eso funciona sin declarar nada:** la cabecera es la declaración.

Y si no escribes ninguna de las tres, el sistema no se queda sin responder: lo trata
como un sí o un no. (Si la pregunta es de texto libre, es el relevo al modo chat, ver
apartado 8.)

---

## 2. Opciones (elegir de una lista)

Se escribe la cabecera `Opciones:` y debajo, una por línea, con el formato
`clave: descripción`. **La clave es lo que te va a devolver**; la descripción es para
que el modelo entienda cuál toca.

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas
```

Guardado eso como `caso.txt` y ejecutado, sale **esto de verdad**:

```
$ python preguntar.py caso.txt

1 pregunta(s), una sola peticion  (138 ms, 0 tokens)

--------------------------------------------------------------
CHOICE  ·  ¿Qué equipo debe atenderlo? 'billing' = Pagos y reembolsos
--------------------------------------------------------------
  billing         1.000  ##############################  <-
  technical       0.000  ..............................
  general         0.000  ..............................

  confianza = 1.000
```

Qué leer:

- **La flecha `<‑` marca lo que eligió.** Aquí `billing`.
- Los números son **probabilidad**, y suman 1. `billing` 1.000 significa que no dudó.
- **`confianza`** es otra cosa: mide **lo concentrada** que está la probabilidad, no la
  probabilidad de acertar. 1.000 = una sola barra llena. Cerca de 0 = empate.
- **`0 tokens`**: aquí no se escribió texto. Por eso es rápido.

> Si escribes **solo la clave** (una línea `billing`, sin descripción) también
> funciona. La descripción ayuda al modelo, pero no es obligatoria.

---

## 3. Niveles (poner algo en una escala)

Cabecera `Niveles de puntuación:` y debajo los niveles **de menor a mayor**. El
sistema los numera solo: el primero es 0.

```
Entrada: Búsqueda: zapatillas de senderismo ligeras para días de lluvia.
Resultado: una ficha de zapatillas de trail impermeables con guía de tallas.

Pregunta: ¿Qué relevancia tiene este elemento para la solicitud?
Niveles de puntuación:
  No relevante
  Algo relevante
  Muy relevante
```

Salida real:

```
SCORE  ·  ¿Qué relevancia tiene este elemento para la solicitud?
--------------------------------------------------------------
  No relevante    0.000  ..............................
  Algo relevante  0.005  ..............................
  Muy relevante   0.995  ##############################  <-

  puntuacion = 1.99
  confianza = 0.969
```

**Fíjate en `puntuacion = 1.99`.** Con tres niveles, «Muy relevante» es el 2. Devuelve
**1,99 y no 2,00** porque la puntuación es la **media ponderada**: reparte 0.995 en el
nivel 2 y 0.005 en el nivel 1, y `0×0.000 + 1×0.005 + 2×0.995 = 1,99`.

**Pero para decidir, eso no hace falta.** Hay dos números y son cosas distintas:

| número | qué es | valor | ¿para qué? |
|---|---|---|---|
| `value` | **el nivel elegido** (el de mayor probabilidad) | `2.0` | **esto es la decisión** |
| `puntuacion` | **la media ponderada**, que puede caer entre niveles | `1.99` | ordenar casos finamente |

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

## 4. Boolean (un sí o un no, con su probabilidad)

Cabecera `Qué significa no o sí:` y debajo qué significa cada uno. **Aquí sí o sí hay
que poner `true:` y `false:`**, porque si no, el modelo no sabe qué estás preguntando.

```
Entrada: Son las 22:30. Una aplicación de calendario quiere recordar una comida
de equipo el viernes. El usuario tiene activado el horario de descanso hasta las 07:00.

Pregunta: ¿Debe esperar esta notificación hasta que termine el horario de descanso?
Qué significa no o sí:
  false: El recordatorio es urgente y debe enviarse ahora
  true: Puede enviarse después sin perjudicar al usuario
```

Salida real:

```
PROBABILITY  ·  ¿Debe esperar esta notificación hasta que termine el horario de descanso?
--------------------------------------------------------------
  no              0.486  ##############................
  sí              0.514  ###############...............

  probabilidad de que sí = 0.514
  confianza = 0.001
```

**Y aquí está el detalle que engancha.** Salió **0.514**, un empate técnico: el modelo
no sabe qué hacer con esta. Pero lo revelador es la **confianza: 0.001**. No está
«poco seguro» — está diciendo que las dos opciones son **indistinguibles** para él.

Esa es la diferencia entre **probabilidad** y **confianza**, y es la razón de que valga
la pena mirar las dos:

| caso | probabilidad | confianza | qué significa |
|---|---|---|---|
| ejemplo 2 | 0.995 | 0.969 | lo tengo claro y además no dudo |
| este | 0.514 | **0.001** | **no tengo ni idea** |

**Fíjate en que una probabilidad alta puede no significar nada sin la confianza.** Un
0.514 con confianza 0.001 es una moneda al aire; un 0.514 con confianza 0.8 sería una
preferencia débil pero real.

**Si usas esto en un programa**, la receta es: actúa solo si la probabilidad pasa de tu
umbral **y** la confianza pasa del suyo. Lo demás, a revisión humana.

> **Y aquí hay una lección de escritura de preguntas.** Esta pregunta se redactó con las
> dos opciones explicadas («el recordatorio es urgente» / «puede enviarse después»), y
> el modelo sigue sin poder decidir: la entrada no dice si la comida de equipo es
> mañana o el viernes que viene. **El empate es información**: a este caso le falta
> contexto para contestarse. Es exactamente el tipo de sitio donde una recuperación de
> contexto (RAG) sí ayudaría — porque falta información, no sobra.

---

## 5. Varias preguntas de una vez

Aquí está lo bueno. Se ponen **varias preguntas sobre la misma entrada**, separadas por
una línea con `---`. Se mandan **en una sola petición** y el modelo las evalúa todas.

```
Entrada: Un cliente escribe: llevo tres días sin poder entrar a la aplicación
y ya me cobraron la renovación.

Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas

---

Pregunta: ¿Qué urgencia tiene?
Niveles de puntuación:
  Baja
  Media
  Alta

---

Pregunta: ¿Hay que responder al cliente hoy?
Qué significa no o sí:
  false: Puede esperar sin perjudicarle
  true: Necesita respuesta hoy
```

Salida real (recortada):

```
3 pregunta(s), una sola peticion  (168 ms, 0 tokens)
```

**Fíjate: 168 ms para tres preguntas, frente a 138 ms para una.** Tres preguntas
costaron un **22% más**, no el triple. Porque el motor las puntúa **todas en la misma
pasada**. Y siguen siendo **0 tokens**.

Y este caso tiene una lectura que conviene entender: el cliente menciona **dos** cosas
—no puede entrar **y** le cobraron—. La pregunta «¿qué equipo debe atenderlo?» se
contestó **`billing`** (las cinco veces que se probó), porque pesa más lo del cobro. Es
**una respuesta legítima y estable**, pero enseña dos cosas:

- **Si la entrada trae dos problemas, la pregunta tiene que decir cuál te importa.**
  Con «¿qué equipo debe atenderlo?» el modelo elige uno y no avisa de que había otro.
- **La confianza avisa cuando hay mezcla.** En esta misma consulta, la tercera pregunta
  («¿hay que responder hoy?») salió con probabilidad 0.435 y confianza **0.012** — un
  empate casi perfecto. Eso es el modelo diciendo *«aquí no me mojo»*, y es la señal de
  que esa pregunta necesita más contexto o está mal planteada.

Es el patrón que hay que interiorizar: **la respuesta que sale limpia se usa; la que
sale con confianza baja, se revisa.**

---

## 6. Lo mismo, pero tipado

Todo lo anterior se puede escribir también en **JSON estructurado**, que es el formato
de TypeSafe/Jev. Es para cuando un programa genera la consulta en vez de una persona.

Las equivalencias son estas:

| lenguaje natural | JSON |
|---|---|
| `Pregunta:` | `instructions` |
| `Opciones:` + `clave: descripción` | `type: "choice"` + `criteria: {clave: descripción}` |
| `Niveles de puntuación:` | `type: "score"` + `criteria: [lista]` |
| `Qué significa no o sí:` | `type: "noul"` + `criteria: {true:…, false:…}` |

El ejemplo 2, tipado:

```json
{
  "model": "typesafe/jev-1.13",
  "state": {
    "input": "Me cobraron dos veces la suscripción. ¿Pueden ayudarme?"
  },
  "questions": {
    "decision": {
      "type": "choice",
      "instructions": "¿Qué equipo debe atenderlo?",
      "criteria": {
        "billing": "Pagos y reembolsos",
        "technical": "Errores e integraciones",
        "general": "Otras consultas"
      }
    }
  }
}
```

**Y aquí está el punto del repositorio:** ese JSON y el texto del apartado 2 **son la
misma consulta y dan el mismo resultado**. Medido sobre 90 casos: **85,6% de acierto y
76 ms en las dos formas**.

*Entonces, ¿para qué el JSON?* Para cuando lo escribe un programa. *¿Y por qué el
lenguaje natural?* Porque **cualquiera puede escribirlo sin conocer el esquema**, y eso
hace que se experimente mucho más. Por eso la puerta de entrada de este repositorio es
el lenguaje natural.

---

## 7. Las cabeceras que acepta cada sección

No hace falta memorizar una forma exacta. El sistema reconoce varias:

| sección | formas que valen |
|---|---|
| **entrada** | `Entrada:`, `Estado:`, `Input:`, `State:`, `Contexto:` |
| **pregunta** | `Pregunta:`, `Instrucciones:`, `Question:` |
| **opciones** | `Opciones:`, `Choices:`, `Criterios:` |
| **niveles** | `Niveles de puntuación:`, `Escala:`, `Score:`, `Niveles de score:` |
| **boolean** | `Qué significa no o sí:`, `No o sí:`, `Noul:`, `Sí o no:`, `Significado:` |

Dos reglas que conviene conocer:

1. **La cabecera empieza en la columna cero.** Lo que va debajo va sangrado (con
   espacios delante). Así una opción llamada `pregunta:` no se confunde con la cabecera.
2. **La entrada va antes de la primera cabecera**, y solo cuenta la del primer bloque.

---

## 8. Qué pasa si la pregunta no es de estos tres tipos

Se puede preguntar algo que no sea ni una lista, ni una escala, ni un sí/no — por
ejemplo «redáctame un resumen». Eso **no es una decisión**: es texto libre.

En ese caso el sistema **releva la pregunta al modo chat** sobre el mismo modelo. No
hay que hacer nada especial: es automático. Y es la razón de que existan los dos modos.

---

## 9. Ejecutarlo

```bash
# desde un fichero
python preguntar.py caso.txt

# escribiéndolo en la línea de comandos
python preguntar.py --texto "Entrada: ... Pregunta: ... Opciones: ..."

# con el JSON crudo del servidor (probabilidades completas, tiempos)
python preguntar.py --json
```

Antes hace falta el servidor:

```bash
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
```

Para probar tus propias preguntas **no hay que tocar código**: se escribe el texto, se
guarda y se ejecuta. Los ejemplos de este manual están en `ejemplos/`.

---

## 10. Resumen: los tres tipos de un vistazo

**Entrada** (siempre la misma, cambia solo la cabecera):

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?
```

| tipo | cabecera | lo que escribes debajo |
|---|---|---|
| **choice** | `Opciones:` | `billing: Pagos y reembolsos` (una por línea, `clave: descripción`) |
| **score** | `Niveles de puntuación:` | `No relevante` (una por línea, de menor a mayor) |
| **boolean** | `Qué significa no o sí:` | `true: ...` y `false: ...` |

**Y esto es lo que devuelve cada uno**, ejecutado de verdad:

**choice** → da una **clave de tu lista**

```
CHOICE  ·  ¿Qué equipo debe atenderlo?
  billing         1.000  ##############################  <-
  technical       0.000  ..............................
  general         0.000  ..............................
  confianza = 1.000
```

En JSON: `"value": "billing"`, `"probabilities": {"billing": 0.9999, ...}`

**score** → da un **número de nivel** y una puntuación ponderada

```
SCORE  ·  ¿Qué relevancia tiene este elemento para la solicitud?
  No relevante    0.000  ..............................
  Algo relevante  0.005  ..............................
  Muy relevante   0.995  ##############################  <-

  puntuacion = 1.99
  confianza = 0.969
```

En JSON: `"value": 2.0`, `"probabilities": {"0.0": 0.0001, "1.0": 0.0053, "2.0": 0.9946}`

**boolean** → da un **`true` o `false`**, con su probabilidad

```
PROBABILITY  ·  ¿Debe esperar esta notificación hasta que termine el horario de descanso?
  no              0.486  ##############................
  sí              0.514  ###############...............

  probabilidad de que sí = 0.514
  confianza = 0.001
```

En JSON: `"value": true`, `"probabilities": {"true": 0.5143, "false": 0.4857}`

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

### La confianza: dónde aporta y dónde no

Aquí hay un caso que merece la pena porque **depende del tipo**:

- **En `boolean`, la confianza no aporta NADA.** Con dos opciones, la probabilidad ya
  determina la confianza por completo. Comprobado: con `p = 0.534130` la confianza
  calculada con una fórmula de una línea da `0.003364`, y es exactamente la que devuelve
  el servidor. Si tienes la probabilidad, la confianza es un cálculo de más.
- **En `choice`, sí aporta.** Dos casos con la probabilidad mayor **casi igual** dan
  confianzas distintas, porque el reparto del resto cambia:

```
  probabilidad mayor 0.714  ->  confianza 0.394
  probabilidad mayor 0.722  ->  confianza 0.455
```

  Con solo la probabilidad mayor esos dos casos parecerían el mismo; con la confianza se
  distingue cuál es más de fiar.

**La regla:** en boolean, quédate con la probabilidad. En choice, mira las dos.

Y esto deja en su sitio lo de `puntuacion` del apartado 3: **es una operación derivada,
igual que `value`, `probability` y `interval_p10_p90`.** La diferencia no es que unas
sean «de más» y otras no, sino cuál necesitas: `value` casi siempre, la media casi
nunca.

---

## 12. Las cinco cosas que hay que recordar

1. **Entrada** + **Pregunta** + **una cabecera** que dice qué tipo es. La cabecera es
   lo único que hace falta para declarar el tipo: no hay que escribir JSON.
2. **Choice** devuelve una clave; **score** un número; **boolean** un `true`/`false`.
   Los tres devuelven además **la probabilidad de cada opción y una confianza**.
3. **Probabilidad** es qué prefiere; **confianza** es cuánto se lo cree. Son distintas y
   las dos importan.
4. Varias preguntas se separan con `---` y **cuestan casi lo mismo** que una.
5. Un fallo raro suele ser **de la pregunta**, no del modelo: quitar la descripción de
   un campo lo arregla más veces de las que parece.
