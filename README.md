# AIOM — un modelo, dos formas de preguntar

**La idea, en una frase:** un modelo de decisión como Jev no es un modelo distinto de
un LLM. **Es el mismo.** Lo que cambia es **cómo le haces la pregunta** y **qué le pides
de vuelta**: prosa, o un valor de un conjunto cerrado con sus probabilidades.

Este repositorio demuestra que eso se consigue con **un modelo corriente en tu propio
equipo**, sin entrenar nada y sin cargar un segundo modelo.

## Cómo funciona

![Arquitectura de AIOM: un modelo, dos formas de preguntar](docs/arquitectura.png)

Los gráficos del estudio se generan con **matplotlib** (`graficos.py`) y el diagrama con
`diagrama.py`, todo en SVG con el texto como texto y colores fijos, para que se vea igual
en GitHub en tema claro y en oscuro. Las leyendas van **fuera del área del gráfico**, no
encima de las barras.

La pieza que lo hace posible no es el modelo: es **el endpoint**. llama.cpp de serie
solo sabe generar texto; el backend
[`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision)
añade uno que **puntúa las opciones en lugar de redactar**. Por eso el modo de decisión
no gasta tokens: no es que escriba poco, es que **no pasa por el bucle de generación**.

## Las dos formas de preguntar (y el respaldo)

|  | cómo se escribe | quién puede escribirlo |
|---|---|---|
| **lenguaje natural** | `Pregunta: ...` + `Opciones:` | cualquiera |
| **tipada** | JSON con `questions.decision` y `criteria` | quien conozca el esquema |

**Dan exactamente lo mismo.** Medido sobre 90 casos: **85,6% de acierto y 76 ms en las
dos**, con idéntica confianza. El formato tipado no aporta nada aquí y sí cuesta, así
que la puerta de entrada es el lenguaje natural.

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas
```

La cabecera decide el tipo de pregunta:

| cabecera que escribes | tipo | devuelve |
|---|---|---|
| `Opciones:` | **choice** | la opción elegida + probabilidad de todas + confianza |
| `Niveles de puntuación:` | **score** | posición en la escala (puede caer entre dos niveles) |
| `Qué significa no o sí:` | **boolean** | un valor entre 0 y 1 |

Si la pregunta **no cabe** en ningún campo conocido, se releva al modo chat sobre el
**mismo** modelo. Una sola pasada decide las dos cosas: si era respondible, y cuáles
son los valores.

```bash
python preguntar.py ejemplos/1_opciones.txt     # elegir de una lista
python preguntar.py ejemplos/2_niveles.txt      # poner algo en una escala
python preguntar.py ejemplos/3_si_o_no.txt      # preguntar sí o no
python preguntar.py ejemplos/4_tres_preguntas.txt   # las tres de golpe
```

Los cuatro están explicados paso a paso, con su salida real, en
[`docs/MANUAL.md`](docs/MANUAL.md).

## Lo que se gana, medido aquí

**Una pregunta suelta** (90 casos, 30 de cada tipo):

| modo | acierto | p50 | confianza |
|---|---|---|---|
| decisión, natural | 85,6% | **76 ms** | 0,82 |
| decisión, tipada | 85,6% | 76 ms | 0,82 |
| chat | 86,7% | 111 ms | — |

Con una pregunta **los tres aciertan igual**. Lo que cambia no es acertar más: es lo que
cuesta. **Un 31% menos de tiempo y sin escribir ni un token.**

**Con varias preguntas encadenadas** (14 casos, 64 preguntas) la brecha se abre:

| modo | acierto | p50 | respuestas ilegibles |
|---|---|---|---|
| decisión | **75,0%** | **93 ms** | 0 |
| chat | 60,9% | 340 ms | **8** |

![Acierto por modo](results/graf/precision.svg)

Y **cuantas más preguntas, mejor sale** el modo de decisión. Con un fondo de 15
preguntas por caso, tomando las primeras N:

| preguntas encadenadas | decisión | chat | ventaja |
|---|---|---|---|
| 1 | 72 ms | 192 ms | 2.7× |
| 5 | 91 ms | 492 ms | 5.4× |
| 10 | 98 ms | 684 ms | 7.0× |
| 15 | **96 ms** | **935 ms** | **9.8×** |

![Tiempo por caso según cuántas preguntas se encadenan](results/graf/escalado.svg)

De 1 a 15 preguntas el modo de decisión sube un **33%**; el chat, un **387%**. El motor
puntúa todas las preguntas **en la misma pasada**, así que añadir una casi no cuesta
nada. Ese es el hallazgo práctico: **cuantas más preguntas por caso, mejor sale el modo
de decisión.**

## Dos cosas que conviene leer antes de tocar el modelo

**El fallo puede ser de la pregunta, no del modelo.** Dos casos fallaban en modo
decisión y el **mismo modelo los acierta cuando se le quita la descripción del campo**
(el idioma del texto: empate a tres con la etiqueta, 0,69 sin ella; la forma de una
fruta: «redonda» 0,64 con etiqueta, «alargada» 0,67 sin ella). Añadir
`'etiqueta' = descripción` a la pregunta **diluye la pregunta**. Un RAG habría empeorado
esos casos: al modelo le sobraba ruido, no le faltaba información.

**Un rango ancho es una trampa.** Un campo numérico de 1 a 99 hacía que acertara 3 de 5
y que la confianza cayera a 0,57. Acotado a 1–12: **5 de 5 y confianza 1,000.** Con 99
valores el modelo debe puntuar muchos nodos y la probabilidad se reparte.

Los dos están medidos y desglosados, con la tabla completa, en
[`docs/ESTUDIO.md`](docs/ESTUDIO.md).

## Lo que este repositorio NO es

- **No compara con Jev ni con ningún modelo del mercado.** Son los resultados medidos
  aquí, con este equipo y este modelo.
- **No reivindica el motor.** El endpoint es de terceros; lo propio es el cliente, el
  traductor de lenguaje natural, la técnica de los dos modos sobre un solo modelo y las
  mediciones. Está todo desglosado, con autoría y licencia de cada pieza, en
  [`CREDITOS.md`](CREDITOS.md).
- **No es un modelo entrenado.** No hay ajuste fino en ninguna parte.

## Probarlo

```bash
# 1. el servidor, con el endpoint de decisión activado
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096

# 2. preguntar en lenguaje natural y recibir solo el valor
python preguntar.py ejemplos/1_opciones.txt

# 3. medirlo tú mismo y comprobar que los documentos cuadran con los datos
python bench_modos.py && python rendimiento.py && python verificar.py --estricto
```

## Documentación

| documento | qué hay |
|---|---|
| **[docs/MANUAL.md](docs/MANUAL.md)** | **empieza aquí**: el manual de uso, de cero, con un ejemplo de cada tipo (opciones, niveles, sí/no), cómo se hacen varias preguntas a la vez y cómo se escribe en formato tipado |
| [docs/ARRANCAR.md](docs/ARRANCAR.md) | cómo levantar el servidor tú mismo, paso a paso, y ejecutar las pruebas |
| [CREDITOS.md](CREDITOS.md) | **de quién es cada pieza**, con commit exacto, licencias y el SHA256 del modelo |
| [docs/GUIA.md](docs/GUIA.md) | la guía del proyecto: cómo se prueba, cómo se estructura un catálogo, cómo mejorarlo |
| [docs/ESTUDIO.md](docs/ESTUDIO.md) | el estudio: con qué hardware se midió, cómo se construyó, los resultados completos, las lecciones y los límites |
| [docs/DETALLE.md](docs/DETALLE.md) | las 154 preguntas una por una: opciones, qué se esperaba, qué eligió cada modo y el reparto de probabilidad |
| [docs/ESTADO-DEL-ARTE.md](docs/ESTADO-DEL-ARTE.md) | de dónde sale la idea, quién es quién y qué es de cada uno |
| [docs/METRICAS.md](docs/METRICAS.md) | todas las métricas consolidadas, con sus definiciones |
| [docs/VALIDACION.md](docs/VALIDACION.md) | qué está medido, qué no, y con qué intervalos de confianza |

## Estructura

```
preguntar.py         LA PUERTA DE ENTRADA: escribes en lenguaje natural y deduce el
                     tipo por la cabecera; una o varias preguntas en una petición
aiom.py              cliente y servidor HTTP (los tres modos)
bench_modos.py       los 3 modos sobre 90 casos, 30 de cada tipo
bench_multi.py       preguntas encadenadas: N preguntas al mismo caso
bench_cascada.py     el escalado 1, 5, 10 y 15 preguntas, con candado anti-duplicados
casos_modos.py       90 casos con verdad de referencia
casos_multi.py       14 casos con 4-5 preguntas encadenadas
casos_cascada.py     fondo de 15 preguntas por caso, para el escalado
detalle.py           -> docs/DETALLE.md
rendimiento.py       -> docs/ESTUDIO.md y los gráficos
graficos.py          los gráficos con matplotlib (estilo único, leyendas fuera del área)
diagrama.py          -> docs/arquitectura.svg y .png: el diagrama de arquitectura
entorno.py           -> la parte de hardware y decisiones de docs/ESTUDIO.md
verificar.py         enlaces, gráficos y cifras: comprueba que los documentos cuadren
                     con results/ (ninguna cifra se queda vieja sin avisar)
metrics.py           toda la estadística en un sitio: Wilson, balanceada, ECE, Brier
reports.py           consolida results/ -> docs/METRICAS.md
report.py            bench.json -> informe y gráficas SVG
depurar.py           encuentra lo que ya no se usa y lo elimina con validación
catalogs/            catálogos de ejemplo (triage de tickets, operación de campo)
ejemplos/            casos de ejemplo para preguntar.py, uno por tipo (los del MANUAL)
docs/                la documentación (ver arriba)
docs/arquitectura.svg  el diagrama de arquitectura (editables) y su PNG para el README
results/             el crudo de todo lo medido (json + csv) y los gráficos
```

## Reproducir

```bash
python bench_modos.py   --out results/modos.json
python bench_multi.py   --out results/multi.json
python bench_cascada.py --reps 10 --out results/cascada.json
python rendimiento.py
python verificar.py --estricto
```

`verificar.py` comprueba que las tablas de este README y de la guía **sigan coincidiendo
con `results/`**: si vuelves a medir y se te olvida actualizar una cifra, lo dice.

> **Antes de medir:** el terminal de esta máquina lanza cada comando **dos veces**, así
> que dos benchmarks pueden correr a la vez, encolarse en el servidor y contaminarse los
> tiempos. `bench_cascada.py` lo evita con un candado atómico (`.cascada.lock`): la
> segunda instancia se retira sola.

## Requisitos

- Python 3.10+ — el cliente **no tiene dependencias**, solo la biblioteca estándar.
- Un `llama-server` con el endpoint `/v1/decision`, del backend
  [`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision).
