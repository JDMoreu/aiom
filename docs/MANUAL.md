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
Entrada: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un
error 500 cada vez que intento iniciar sesión. Ya probé a reinstalarla y sigue igual.

Pregunta: ¿A qué área hay que enviar este correo?
Opciones:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas y planes
  otros: Todo lo demás
```

Guardado eso como `caso.txt` y ejecutado, sale **esto de verdad**:

```
$ python preguntar.py caso.txt

1 pregunta(s), una sola peticion  (135 ms, 0 tokens)

--------------------------------------------------------------
CHOICE  ·  ¿A qué área hay que enviar este correo?
--------------------------------------------------------------
  soporte         1.000  ##############################  <-
  otros           0.000  ..............................
  facturacion     0.000  ..............................
  comercial       0.000  ..............................

  confianza = 1.000
```

Qué leer:

- **La flecha `<‑` marca lo que eligió.** Aquí `soporte`.
- Los números son **probabilidad**, y suman 1. `soporte` 1.000 significa que no dudó.
- **`confianza`** es otra cosa: mide **lo concentrada** que está la probabilidad, no la
  probabilidad de acertar. 1.000 = una sola barra llena. Cerca de 0 = empate.
- **`0 tokens`**: aquí no se escribió texto. Por eso es rápido.
- La cabecera dice **solo la pregunta**. Las opciones van debajo, en su lista, para que
  no se confunda una opción con la respuesta.

> Si escribes **solo la clave** (una línea `soporte`, sin descripción) también
> funciona. La descripción ayuda al modelo, pero no es obligatoria.

---

## 3. Niveles (poner algo en una escala)

Cabecera `Niveles de puntuación:` y debajo los niveles **de menor a mayor**. El
sistema los numera solo: el primero es 0.

```
Entrada: Aviso del sistema de monitorización: la aplicación completa lleva una hora
sin responder. Ningún usuario puede entrar ni usar ninguna función.

Pregunta: ¿Qué gravedad tiene el incidente?
Niveles de puntuación:
  Aviso: no afecta al servicio
  Menor: afecta a unos pocos usuarios
  Grave: afecta a la mayoría
  Crítico: el servicio está caído del todo
```

Salida real:

```
SCORE  ·  ¿Qué gravedad tiene el incidente?
--------------------------------------------------------------
  Aviso: no afecta al servicio             0.009  ..........
  Menor: afecta a unos pocos usuarios      0.009  ..........
  Grave: afecta a la mayoría               0.165  #####.....
  Crítico: el servicio está caído del todo 0.817  ##########  <-

  puntuacion = 2.79
  confianza = 0.605
```

**Fíjate en `puntuacion = 2.79`.** Con cuatro niveles, «Crítico» es el 3. Devuelve
**2,79 y no 3,00** porque la puntuación es la **media ponderada**: reparte 0.817 en el
nivel 3, 0.165 en el 2 y un poco en los otros dos, y
`0×0.009 + 1×0.009 + 2×0.165 + 3×0.817 = 2,79`.

**Pero para decidir, eso no hace falta.** Hay dos números y son cosas distintas:

| número | qué es | valor | ¿para qué? |
|---|---|---|---|
| `value` | **el nivel elegido** (el de mayor probabilidad) | `3.0` | **esto es la decisión** |
| `puntuacion` | **la media ponderada**, que puede caer entre niveles | `2.79` | ordenar casos finamente |

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
Entrada: Un cliente escribe diciendo que han entrado en su cuenta desde otro país
y que no reconoce dos compras hechas esta madrugada.

Pregunta: ¿Hay indicios de que la cuenta esté comprometida?
Qué significa no o sí:
  false: No hay indicios de acceso no autorizado
  true: Hay indicios de acceso no autorizado
```

Salida real:

```
PROBABILITY  ·  ¿Hay indicios de que la cuenta esté comprometida?
--------------------------------------------------------------
  sí              0.800  ########################......
  no              0.200  ######........................

  probabilidad de que sí = 0.800
  confianza = 0.277
```

**Qué ha pasado aquí.** El caso sí da para decidir: hay un acceso desde otro país y dos
compras que el cliente no reconoce, así que el modelo dice que **sí** (0.800) con una
confianza razonable (0.277) — ni un empate ni un exceso de seguridad.

**Y ahora compáralo con un caso que NO da para decidir.** El mismo tipo de pregunta,
pero con la entrada sin la información que hace falta:

```
Entrada: Son las 22:30. Una aplicación de calendario quiere recordar una comida
de equipo el viernes. El usuario tiene activado el horario de descanso hasta las 07:00.

Pregunta: ¿Debe esperar esta notificación hasta que termine el horario de descanso?
Qué significa no o sí:
  false: El recordatorio es urgente y debe enviarse ahora
  true: Puede enviarse después sin perjudicar al usuario
```

```
PROBABILITY  ·  ¿Debe esperar esta notificación hasta que termine el horario de descanso?
--------------------------------------------------------------
  no              0.486  ##############................
  sí              0.514  ###############...............

  probabilidad de que sí = 0.514
  confianza = 0.001
```

**Ahí está el detalle que engancha.** Salió **0.514**, un empate técnico: el modelo no
sabe qué hacer con esta. Pero lo revelador es la **confianza: 0.001**. No está «poco
seguro» — está diciendo que las dos opciones son **indistinguibles** para él.

Esa es la diferencia entre **probabilidad** y **confianza**, y es la razón de que valga
la pena mirar las dos:

| caso | probabilidad | confianza | qué significa |
|---|---|---|---|
| el de la cuenta | 0.800 | 0.277 | lo tengo bastante claro |
| el del calendario | 0.514 | **0.001** | **no tengo ni idea** |

**Fíjate en que una probabilidad alta puede no significar nada sin la confianza.** Un
0.514 con confianza 0.001 es una moneda al aire; un 0.514 con confianza 0.8 sería una
preferencia débil pero real.

**Si usas esto en un programa**, la receta es: actúa solo si la probabilidad pasa de tu
umbral **y** la confianza pasa del suyo. Lo demás, a revisión humana.

> **Y aquí hay una lección de escritura de preguntas.** La del calendario se redactó con
> las dos opciones explicadas («el recordatorio es urgente» / «puede enviarse después»),
> y el modelo sigue sin poder decidir: la entrada no dice si la comida de equipo es
> mañana o el viernes que viene. **El empate es información**: a este caso le falta
> contexto para contestarse. Es exactamente el tipo de sitio donde una recuperación de
> contexto (RAG) sí ayudaría — porque falta información, no sobra.

> **Y una advertencia medida en este mismo repositorio:** en `boolean`, el orden en que
> escribes `true:` y `false:` pesa. El mismo caso, con las dos opciones **intercambiadas**
> de sitio, pasó de 0.463 (confianza 0.004) a 0.953 (confianza 0.728) para la misma
> respuesta semántica. Si te importa el resultado, **prueba las dos redacciones**.

---

## 5. Varias preguntas de una vez

Aquí está lo bueno. Se ponen **varias preguntas sobre la misma entrada**, separadas por
una línea con `---`. Se mandan **en una sola petición** y el modelo las evalúa todas.

```
Entrada: Hola, el viernes pagué el plan anual y desde entonces la aplicación se cierra
sola cada vez que intento subir una foto. Necesito subir las fotos de un evento este
fin de semana.

Pregunta: ¿A qué área hay que enviar este correo?
Opciones:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas y planes
  otros: Todo lo demás

---

Pregunta: ¿Qué urgencia tiene?
Niveles de puntuación:
  Baja: puede esperar
  Media: conviene atenderlo esta semana
  Alta: hay una fecha límite encima

---

Pregunta: ¿El cliente ya pagó el plan anual?
Qué significa no o sí:
  false: No ha pagado todavía
  true: Sí, ya lo pagó
```

Salida real:

```
3 pregunta(s), una sola peticion  (157 ms, 0 tokens)

--------------------------------------------------------------
CHOICE  ·  ¿A qué área hay que enviar este correo?
--------------------------------------------------------------
  soporte         0.439  #############.................  <-
  comercial       0.351  ###########...................
  facturacion     0.198  ######........................
  otros           0.012  ..............................
  confianza = 0.204

--------------------------------------------------------------
SCORE  ·  ¿Qué urgencia tiene?
--------------------------------------------------------------
  Baja: puede esperar                    0.051  ##............
  Media: conviene atenderlo esta semana  0.321  ##########....
  Alta: hay una fecha límite encima      0.628  ###################...  <-
  puntuacion = 1.58
  confianza = 0.264

--------------------------------------------------------------
PROBABILITY  ·  ¿El cliente ya pagó el plan anual?
--------------------------------------------------------------
  sí              0.999  ##############################
  no              0.001  ..............................
  confianza = 0.985
```

**Fíjate: 157 ms para tres preguntas, frente a 135 ms para una.** Tres preguntas
costaron un **16% más**, no el triple. Porque el motor las puntúa **todas en la misma
pasada**. Y siguen siendo **0 tokens**.

**Y esto enseña lo más útil del manual: no todas las preguntas salen igual de bien.**

- La tercera («¿ya pagó?») sale **limpia**: 0.999 con confianza 0.985. El dato está en
  el texto y el modelo lo encuentra sin dudar. **Esta se usa tal cual.**
- La primera («¿a qué área?») sale **floja**: `soporte` gana con 0.439 y la confianza es
  **0.204**. El caso trae **dos** cosas —pagó **y** se le cierra la app—, así que el
  modelo reparte y no se moja. Es **una respuesta legítima**, pero avisa de que la
  pregunta es ambigua.

**Si la entrada trae dos problemas, la pregunta tiene que decir cuál te importa.** Con
«¿a qué área hay que enviar este correo?» el modelo elige uno y no avisa de que había
otro. Con «¿qué área corresponde al **fallo**?» la respuesta se habría separado.

Es el patrón que hay que interiorizar: **la respuesta que sale limpia se usa; la que
sale con confianza baja, se revisa.**

### Y esto es lo que se gana frente al chat

Para verlo con tus ojos, `comparar.py` coge el mismo caso y lo lanza **en los dos
modos**, uno al lado del otro:

```bash
python comparar.py ejemplos/5_correo_soporte.txt
```

Con ese caso (una queja con cortes de conexión y un cobro duplicado), sale esto:

| | decisión | chat |
|---|---|---|
| peticiones al servidor | **1** | 3 |
| tiempo | **174 ms** | 2192 ms |
| tokens escritos | **0** | 136 |
| salida | valores | prosa |
| ¿se puede comparar? | **sí, son números** | no, hay que leerla |

**Y lo interesante no es el tiempo: es la forma de la respuesta.** A la misma pregunta
«¿a qué área hay que enviar este correo?»:

- **decisión** → `facturacion` 0.665 · `soporte` 0.296 · `comercial` 0.038 · `otros` 0.000
- **chat** → *«Soporte Técnico de Internet. Soporte de Facturación y Cobros.»*

El chat **dio dos respuestas a la vez** y no dijo con cuánta seguridad. La de decisión da
un valor y **el reparto entero**: se ve que dudaba (0.665 no es 1.000) y se puede poner
un umbral. La del chat hay que leerla, interpretarla y decidir a mano cuál de las dos
vale — y si el programa tiene que actuar solo, no puede.

Esa es la diferencia de fondo: **las dos responden, pero solo una es comparable.**

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
Entrada: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un
error 500 cada vez que intento iniciar sesión.
```

| tipo | cabecera | lo que escribes debajo |
|---|---|---|
| **choice** | `Opciones:` | `soporte: Fallos y errores del producto` (una por línea, `clave: descripción`) |
| **score** | `Niveles de puntuación:` | `Aviso: no afecta al servicio` (una por línea, de menor a mayor) |
| **boolean** | `Qué significa no o sí:` | `true: ...` y `false: ...` |

**Y esto es lo que devuelve cada uno**, ejecutado de verdad:

**choice** → da una **clave de tu lista**

```
CHOICE  ·  ¿A qué área hay que enviar este correo?
  soporte         1.000  ##############################  <-
  otros           0.000  ..............................
  facturacion     0.000  ..............................
  comercial       0.000  ..............................
  confianza = 1.000
```

En JSON: `"value": "soporte"`, `"probabilities": {"soporte": 1.0, ...}`

**score** → da un **número de nivel** y una puntuación ponderada

```
SCORE  ·  ¿Qué gravedad tiene el incidente?
  Aviso: no afecta al servicio             0.009  ..........
  Menor: afecta a unos pocos usuarios      0.009  ..........
  Grave: afecta a la mayoría               0.165  #####.....
  Crítico: el servicio está caído del todo 0.817  ##########  <-

  puntuacion = 2.79
  confianza = 0.605
```

En JSON: `"value": 3.0`, `"probabilities": {"0.0": 0.0088, "1.0": 0.0089, "2.0": 0.1651, "3.0": 0.8172}`

**boolean** → da un **`true` o `false`**, con su probabilidad

```
PROBABILITY  ·  ¿Hay indicios de que la cuenta esté comprometida?
  sí              0.800  ########################......
  no              0.200  ######........................

  probabilidad de que sí = 0.800
  confianza = 0.277
```

En JSON: `"value": true`, `"probabilities": {"true": 0.8002, "false": 0.1998}`

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
`0.0088, 0.0089, 0.1651, 0.8172`:

```
H(p)      = −(0.0088·ln0.0088 + 0.0089·ln0.0089 + 0.1651·ln0.1651 + 0.8172·ln0.8172)
          = 0.5460
ln(4)     = 1.3863
H/ln(4)   = 0.3939          ← entropía normalizada: 0 = un pico, 1 = reparto plano
confianza = 1 − 0.3939 = 0.6061
```

*(El manual dice 0.605 y la cuenta da 0.606 porque el JSON publicado lleva las
probabilidades redondeadas a 4 decimales; con las completas sale 0.605.)*

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

- **En `boolean`, la confianza no aporta NADA.** Con dos opciones (n=2, `ln(2)`) la
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
