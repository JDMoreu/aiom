# Un modelo, dos modos — guía completa

**Un solo modelo cargado en memoria que responde de dos maneras.** No hay un modelo
para decidir y otro para conversar: hay **uno**, y se le pregunta de dos formas.

| modo | qué le das | qué te devuelve | ¿escribe texto? |
|---|---|---|---|
| `decision` | un caso escrito en lenguaje natural | valores, con probabilidades y confianza | **no — 0 tokens** |
| `chat` | una pregunta | prosa | sí |
| `ask` | una pregunta | **solo el valor**, o prosa si no cabe | según el caso |

---

## 1. La idea: escribes normal, el sistema deduce el tipo

**No hay que tipar nada.** No escribes JSON ni declaras si es un valor, un sí/no o una
puntuación. Escribes el caso como se lo contarías a una persona, y el sistema mira qué
has puesto para saber qué tipo de pregunta es.

Los tres casos de esta página son los mismos que usa TypeSafe (Jev) en
[su playground](https://jevai.dev/es/playground/).

### Escribes esto

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas
```

### Y contesta esto

```
CHOICE  ·  ¿Qué equipo debe atenderlo?
--------------------------------------------------------------
  billing         1.000  ##############################  <-
  technical       0.000  ..............................
  general         0.000  ..............................
  confianza = 1.000
```

---

## 2. Los tres formatos que reconoce

Lo único que cambia entre los tres es **la cabecera** que pones después de la pregunta.

### CHOICE — pones `Opciones:`

```
Entrada: Búsqueda: zapatillas de senderismo ligeras para días de lluvia.
         Resultado: una ficha de zapatillas de trail impermeables con guía de
         tallas y reseñas.

Pregunta: ¿Qué relevancia tiene este elemento para la solicitud?
Opciones:
  nada: No viene al caso
  algo: Se acerca a lo que busca
  mucho: Responde exactamente a lo que busca
```

### SCORE — pones `Niveles de puntuación:`

Los niveles van **de menor a mayor**, sin numerarlos. El primero vale 0.

```
Entrada: Búsqueda: zapatillas de senderismo ligeras para días de lluvia.
         Resultado: una ficha de zapatillas de trail impermeables con guía de
         tallas y reseñas.

Pregunta: ¿Qué relevancia tiene este elemento para la solicitud?
Niveles de puntuación:
  No relevante
  Algo relevante
  Muy relevante
```

```
SCORE  ·  ¿Qué relevancia tiene este elemento para la solicitud?
--------------------------------------------------------------
  No relevante     0.000  ..............................
  Algo relevante   0.006  ..............................
  Muy relevante    0.994  ##############################  <-

  puntuacion = 1.99      confianza = 0.965
```

> **La puntuación la calcula el cliente, no el servidor.** La definición es la de
> TypeSafe: «cada número de nivel multiplicado por su probabilidad, sumado». Aquí:
> `0×0.000 + 1×0.006 + 2×0.994 = 1.99`.

### PROBABILITY — pones `Qué significa no o sí:`

```
Entrada: Son las 22:30. Una aplicación de calendario quiere recordar una comida de
         equipo prevista para el próximo viernes. El usuario tiene activado el
         horario de descanso hasta las 07:00.

Pregunta: ¿Debe esperar esta notificación hasta que termine el horario de descanso?
Qué significa no o sí:
  false: El recordatorio es urgente y debe enviarse ahora
  true: Puede enviarse después sin perjudicar al usuario
```

```
PROBABILITY  ·  ¿Debe esperar esta notificación hasta que termine el horario de descanso?
--------------------------------------------------------------
  no              0.458  ##############................
  sí              0.542  ################..............  <-

  probabilidad de que sí = 0.542     confianza = 0.005
```

> **Fíjate en la confianza: 0,005.** El modelo reparte casi al 50% y **admite que no lo
> sabe**: la comida es el viernes (no corre prisa), pero se avisa a las 22:30, dentro
> del horario de descanso. Es una duda real, y el número la delata. Sin la confianza,
> este caso pasaría como una respuesta más.

---

## 3. Una o varias preguntas, en un solo viaje

Separa las preguntas con una línea de `---` y **se mandan todas en una sola petición**.

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

---
Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas

---
Pregunta: ¿Qué urgencia tiene el caso?
Niveles de puntuación:
  Puede esperar sin problema
  Conviene atenderlo hoy
  Necesita acción inmediata

---
Pregunta: ¿Debe revisarlo una persona antes de actuar?
Qué significa no o sí:
  false: Puede resolverse de forma automática
  true: Conviene que lo revise una persona
```

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

3 pregunta(s), una sola peticion  (162 ms, 0 tokens)

CHOICE       billing 1.000 ...................................... confianza 1.000
SCORE        Conviene atenderlo hoy 0.662 ......... puntuacion 1.19  confianza 0.256
PROBABILITY  no 0.655 vs sí 0.345 ................. confianza 0.071
```

**Tres preguntas, 162 ms y cero tokens.** Y lo importante: aunque las tres se evalúan
sobre el mismo caso, cada una es independiente — la respuesta de una no contamina a
las otras.

### Clasificar por varios ejes a la vez

Aquí está la gracia de encadenar. Con la entrada «una manzana roja» se pregunta todo
de golpe, cada pregunta de un tipo distinto:

```
Entrada: una manzana roja

---
Pregunta: ¿Qué sabor tiene?
Opciones:
  citrico: Ácido, como el limón
  dulce: Dulce, como el azúcar
  insipido: Sin sabor apreciable

---
Pregunta: ¿Qué forma tiene?
Opciones:
  redonda: Esférica o casi esférica
  alargada: Más larga que ancha
  irregular: Sin forma definida

---
Pregunta: ¿De qué color es?
Opciones:
  rojo: Rojo
  amarillo: Amarillo
  verde: Verde
  naranja: Naranja

---
Pregunta: ¿Su color es uniforme, de un solo tono?
Qué significa no o sí:
  true: Un solo tono en toda la superficie
  false: Varios tonos o manchas

---
Pregunta: ¿Qué tamaño tiene?
Niveles de puntuación:
  Pequeño
  Mediano
  Grande
```

Cinco preguntas, tres tipos distintos, **una sola petición**. Y fíjate en lo que
cuesta añadirlas, que es lo que hace esto viable:

| | 1 pregunta | 5 preguntas |
|---|---|---|
| tiempo por caso | 72 ms | **91 ms** |

**Cinco preguntas cuestan un 26% más que una.** Eso es lo que permite clasificar por
sabor, forma, color, uniformidad y tamaño sin que el coste se dispare — y es
exactamente donde el modo chat se cae: con varias respuestas que devolver en un solo
texto baja del 75% al 61% de acierto. Está medido en [`ESTUDIO.md`](ESTUDIO.md).

---

## 4. Cómo se usa

```bash
cd ~/Documents/aiom

python preguntar.py ejemplos/1_opciones.txt   # desde un fichero
python preguntar.py --texto "Entrada: ... Pregunta: ... Opciones: ..."
python preguntar.py --json                          # la respuesta cruda
```

Y el catálogo fijo, cuando las preguntas son siempre las mismas y quieres velocidad:

```bash
python aiom.py --catalog catalogs/soporte.json ask "me cobraron dos veces la suscripcion"
```

```
department=billing  requested_resolution=refund  tone=calm  ...
```

### Como API HTTP

```bash
python aiom.py serve --port 8100
curl -X POST localhost:8100/ask -H 'Content-Type: application/json' \
     -d '{"question": "me cobraron dos veces"}'
```

---

## 5. Por qué el modo decisión no gasta tokens

No es un envoltorio de Python. `/v1/decision` **es un endpoint del servidor** (añadido
por el fork `parallel-decision`). El servidor traduce el esquema a un grafo de
restricciones y **lee los logits en los nodos de restricción**: no hay bucle de
decodificación, así que no hay tokens. No se puede bajar de cero porque ya está en cero.

### La comparativa con el modo chat

Las mismas consultas, el mismo modelo, **los mismos pesos**: solo cambia cómo se le
pregunta.

| | `decision` | `chat` | |
|---|---|---|---|
| latencia p50 | **93,8 ms** | 470,1 ms | **5,0x** |
| latencia p95 | **112,7 ms** | 510,9 ms | 4,5x |
| caudal | **10,57 q/s** | 2,16 q/s | **4,9x** |
| acierto en los campos | **53/53** | 49/53 | — |

Con un caso de arriba, en el mismo servidor:

```
decision   100 ms    0 tokens    -> department=billing
chat      1014 ms   90 tokens    -> "¡Claro que sí! Podemos realizar el cambio..."
```

### Dónde se va el tiempo

```
prefill  111,7 ms   <- meter TU caso en el modelo. Es el suelo irreductible
scoring  118,2 ms   <- puntuar las opciones. Esto SI depende del esquema
```

El `prefill` no baja optimizando el esquema: hay que leer el texto. El `scoring` sí.

### Por qué el tipo de pregunta importa tanto

El servidor traduce cada pregunta a un árbol de decisión y lee los logits en los nodos.
Cuantas más opciones, más nodos y menos confianza. Medido:

| definición | aciertos | confianza | nodos puntuados |
|---|---|---|---|
| entero 1..99 | 3/5 | 0.570 | 10 |
| entero 1..12 | **5/5** | **1.000** | **2** |
| enum de 12 valores | **5/5** | **1.000** | **2** |

Por eso CHOICE (lista corta) y PROBABILITY (dos opciones) salen tan limpios, y por eso
un rango numérico ancho sale mal: **acota siempre**.

---

## 6. Los dos modos a la vez

Lo que los une es **una pregunta más**: la que decide si el caso cabe en el catálogo o
hay que redactar prosa.

```python
def ask(question, catalog, cfg):
    d = decide(question, catalog, cfg)          # 1 peticion, 0 tokens
    if not d["decision"]["respondible"]:
        return chat(question, catalog, cfg)     # relevo al MISMO modelo
    return {k: v for k, v in d["decision"].items() if k != "respondible"}
```

```
"me cobraron dos veces la suscripcion"    [decision]   119 ms   0 tok
  -> department=billing

"redactame la respuesta para el cliente"  [chat]      1014 ms  90 tok
  -> ¡Claro que sí! Podemos realizar el cambio...
```

**El mismo modelo sirve las dos**, y decidir cuál toca **cuesta cero tokens**, porque
va dentro de la misma decisión.

### Enrutar por confianza: el caso que lo justifica

Como hay `confidence`, el código puede tener una segunda vía: no solo *qué* contestar,
sino *si actuar*. Y no es teoría — esta frase

> «I have asked three times now. Can I please just talk to a real person?»

hace que la pregunta de enrutado conteste `false` con probabilidad 0,528 frente a 0,472
— y **confianza 0,0023**. Una moneda al aire. Sin la confianza, ese caso se relevaría a
`chat` en silencio y nadie se enteraría:

```python
g = d["fields"]["respondible"]
if g["confidence"] < 0.3:
    enviar_a_revision_humana(caso)      # no esta claro: que decida una persona
elif not g["value"]:
    responder_en_prosa(caso)
else:
    usar_los_valores(d)
```

Es el patrón que TypeSafe llama *confidence routing*: **la respuesta dice qué, la
confianza dice si actuar**.

### Cuándo usar cada modo

- **`decision`** — clasificar, enrutar, puntuar, extraer. Alto volumen, necesitas el
  dato, no una explicación. Es donde está la ganancia: 5x más rápido y gratis.
- **`chat`** — redactar, explicar, resumir. Cuando el texto **es** el entregable.
- **`ask`** — no sabes cuál de las dos toca. Deja que el catálogo lo decida.

---

## 7. Cómo replicarlo con cualquier otro modelo

**Requisito previo, y es la trampa gorda:**

> El modelo tiene que correr en un servidor con el endpoint **`/v1/decision`**. Eso no
> es estándar de llama.cpp: lo añade el fork
> [`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision).
> Con un llama.cpp normal, `preguntar.py` no funciona — no existe el endpoint.

### Paso a paso

**1. Compila el fork y arranca el servidor.**

```bash
llama-server --list-devices          # debe ver la GPU
llama-server -m modelo.gguf -ngl 99 -fa on \
             -c 32768 --decision-seqs 64 --port 8096
```

`--decision-seqs` **no es opcional**: reserva las ramas que el motor necesita, una por
contexto del lote. Demasiado pocas y verás
`no free KV cache space for the decision branches`.

**2. Escribe un caso y ejecútalo.** No hay que configurar nada más:

```bash
python preguntar.py --texto "Entrada: ... Pregunta: ... Opciones: ..."
```

**3. Comprueba que el modelo responde con sentido.** Señales de alarma:

- Si la confianza sale muy baja en **todos** los casos, tus opciones se solapan.
- Si el tipo no es el que esperabas, revisa la cabecera (`Opciones:` / `Niveles de
  puntuación:` / `Qué significa no o sí:`).
- Si `rounds` es mayor que 1–2, la pregunta es cara: acota o usa listas cortas.

**4. Mide.** No te fíes de que «va bien»:

```bash
python bench.py --concurrency 1,4,16   # decision vs chat, misma tarea
python snapshot.py 20                  # latencia con desviacion + set adversario
```

**5. Construye un set adversario desde el principio.** Si tu dataset base da 100%, está
saturado y no informa. El nuestro daba 100% y el adversario **89%**, con `distractor`
como punto débil. Ese 89% es el número útil.

**6. Calibra por carga de trabajo.** La calibración **no se transfiere**: el mismo
modelo y la misma máquina dieron ECE 0,0163 en un dominio y 0,2495 en otro. Sin
recalibrar, los umbrales de confianza no valen.

```bash
python calibrate.py --fuente wanli_full    # ECE 0,2495 -> 0,0198, out-of-fold
```

### Qué cambia según el modelo

| factor | qué mirar |
|---|---|
| **tamaño** | el `prefill` crece con los parámetros; el `scoring` casi no |
| **arquitectura** | ventana deslizante acota la KV; un encoder sería más rápido (Laya: 33 ms) |
| **cuantización** | Q8_0 pierde 1% de decisiones; **Q4_K_M pierde 7%** — una de cada catorce |
| **punto de partida** | ¿trae cabeza de decisión? Casi ningún modelo abierto la trae |

### La trampa del GGUF, si usas modelos de la familia JEV

Los GGUF populares de `JEV-9B`, `JEV-27B` y `GEV-26B-Decide` **no contienen la parte de
decisión**: son Qwen y Gemma planos con etiqueta Jev. El adaptador, la cabeza y la
calibración viven en archivos aparte que la conversión deja fuera. Cómo distinguirlos:
busca `head.safetensors`, `adapter/` y `calibration.json`. Si solo hay `.gguf`, no decide.

**Pero eso no te afecta con este enfoque**: no necesitas una cabeza de decisión.
`/v1/decision` funciona sobre **cualquier** modelo del fork, porque lee los logits de
las opciones que tú escribes. Por eso replicarlo es escribir un caso, no entrenar nada.

---

## 8. Estado y límites

**Verificado:** los dos modos funcionando sobre un modelo, la comparativa medida
(5,0x, 0 tokens), los tres tipos de pregunta reproducidos con los casos de TypeSafe,
la puntuación oficial de S1MB con tests contra la especificación, la calibración con
validación cruzada.

**Medido y no favorable, y por eso está aquí:** el acierto real no es 100% sino **89%**
sobre casos adversarios; en S1MB la exactitud cruda (77%) está inflada ~11 puntos
respecto a la balanceada (0,663), o sea que parte del acierto es elegir la clase
mayoritaria. La pregunta de enrutado tiene un caso medido donde es ruido (confianza
0,0023).

**No verificado:** una sola máquina (RX 9070 por Vulkan), un solo modelo, una
configuración. El techo de ~13 q/s es de esta configuración. La palanca del encoder
(como Laya, 33 ms con backbone ModernBERT) y el ajuste fino de `--decision-seqs` no
están explorados.

**Documentos:** [`WORKFLOW.md`](WORKFLOW.md) el proceso con los errores;
[`VALIDACION.md`](VALIDACION.md) qué está medido y qué no;
[`METRICAS.md`](METRICAS.md) todas las cifras con sus fuentes;
[`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md) el mercado y con qué compararse.
