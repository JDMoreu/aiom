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
input: Son las 22:30. Una aplicación de calendario quiere recordar una comida
de equipo el viernes. El usuario tiene activado el horario de descanso hasta las 07:00.

ask: ¿Debe esperar esta notificación hasta que termine el horario de descanso?
noul:
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

Se puede comprobar a mano, con dos comandos. El caso es
`ejemplos/5_correo_soporte.txt` (una queja con cortes de conexión y un cobro duplicado).

**1. En la vía de decisión** — las tres preguntas de una vez:

```bash
python preguntar.py ejemplos/5_correo_soporte.txt
```

**2. En la vía de chat** — la misma pregunta, en prosa. Con `--comparar` salen las dos vías en
la **misma corrida**, que es lo que hace que los dos tiempos se puedan comparar:

```bash
python ejemplos/integrar.py --comparar
```

Las dos vías van sobre el mismo caso y con una sola petición cada una: la decisión resuelve
todas las preguntas de golpe y el chat contesta todo en una respuesta. Por la API es
`"comparar": true`, y está explicado en [`API.md`](API.md).

Lo que sale, medido aquí:

**Decisión** — 1 petición, 211 ms, **0 tokens**:

```
CHOICE  ·  ¿A qué área hay que enviar este correo?
  facturacion     0.683  <-
  soporte         0.280
  comercial       0.036
  otros           0.000
  confianza = 0.467
```

**Chat** — 1 petición, 2423 ms, 146 tokens, y en prosa:

> **soporte: Fallos y errores del producto**
>
> **Explicación:** El cliente está quejándose principalmente de un problema técnico grave
> con su servicio (cortes de conexión casi todas las noches) y de que no ha recibido
> soluciones de su equipo. Aunque también menciona problemas de cobro (facturas dobles),
> el núcleo de su queja es el fallo del servicio.

**Y aquí está lo que merece la pena mirar: no coinciden.** La decisión dice `facturacion`
(0.683) y el chat dice `soporte`. Los dos tienen su argumento —el correo habla de cortes
**y** de un cobro duplicado—, pero solo uno de los dos da **un número con el que decidir**.

**La diferencia no es el tiempo, es la forma.** Decisión da **un valor y el reparto
entero**: se ve que dudaba (0.683 no es 1.000) y se le puede poner un umbral. El chat da
una respuesta **y un párrafo justificándola** — hay que leerlo, decidir a mano si vale, y un
programa no puede hacerlo.

Esa es la diferencia de fondo: **las dos responden, pero solo una es comparable.**

*(En el chat la redacción cambia de una corrida a otra; la de decisión es estable.)*

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

```bash
# desde un fichero (lo recomendado: el caso y las preguntas, con sus saltos de línea)
python preguntar.py caso.txt

# escribiéndolo en la línea de comandos. Los saltos de línea van con $'...': si no,
# todo cae en la primera línea y no hay ningún 'ask:' que valga.
python preguntar.py --texto $'input: Llevo desde ayer sin poder entrar: me sale un error 500.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás'

# con el caso sacado de un documento: el fichero trae solo las preguntas
# (ejemplos/6_preguntas_sobre_un_documento.txt es uno de esos, listo para probar)
python preguntar.py mis_preguntas.txt --documento carta.pdf

# doce preguntas de golpe sobre un curriculum, para medir velocidad y acierto
python preguntar.py ejemplos/7_preguntas_curriculum.txt --documento mi_cv.pdf

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

**noul** → da un **`true` o `false`**, con su probabilidad

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

Y esto deja en su sitio lo de `puntuacion` del apartado 3: **es una operación derivada,
igual que `value`, `probability` y `interval_p10_p90`.** La diferencia no es que unas
sean «de más» y otras no, sino cuál necesitas: `value` casi siempre, la media casi
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
