# Métricas consolidadas

Generado por `reports.py` a partir de los artefactos de `results/`. **Ninguna cifra de este documento está escrita a mano.**

## Resumen

| medición | valor | ¿informa? |
|---|---|---|
| Acierto, set adversario (IoT) | 89% | **sí** — el dataset base está saturado |
| Acierto balanceado, WANLI (público) | 0.678 | **sí** — etiquetas de terceros |
| Calibración (ECE), WANLI | 0.2495 | **sí** — sobreconfiado |
| Acierto macro, S1MB (102 suites) | 47.3% | indicativo |
| **Task Avg S1MB, oficial** | **34.05/100** | **sí** — fórmulas y unidad oficiales, cobertura parcial |
| Calibración (ECE), IoT | 0.0163 | **débil** — tarea saturada |
| Latencia | 93.0 ms | sí |

## Métricas internas (catálogo IoT propio)

Artefacto: `results/internos.json` · regenerar con `python snapshot.py`

- Latencia: **93.0 ms** (desv 10.4), p50 93.6 ms, p95 112.1 ms — 20 repeticiones
- Coste del esquema: **6 nodos** puntuados, **1 rondas** por consulta
- Acierto dataset base: 265/265 — **saturado, no informa**
- **Acierto set adversario: 33/37 (89%)** ← la cifra que informa
- Calibración interna: ECE **0.0163** (bien calibrado), Brier 0.0026

| categoría adversaria | acierto |
|---|---|
| `distractor` | 10/12 (83%) |
| `fuera_cat` | 3/3 (100%) |
| `fuera_rango` | 6/7 (86%) |
| `implicito` | 9/10 (90%) |
| `multi_predio` | 1/1 (100%) |
| `negacion` | 4/4 (100%) |
| `no_resp` | (sin campos evaluables) |

## WANLI — dataset público (inferencia en lenguaje natural)

Artefacto: `results/wanli.json` · regenerar con `python bench_public.py wanli --n 256`

Dataset público `alisawuffles/WANLI`, primeras 5000 filas del split de test, 3 clases (entailment / neutral / contradiction). **Es la primera cifra nuestra comparable con la industria**, porque las etiquetas no son nuestras.

- Exactitud: **67.7%** (3385/5000) IC95% [66.4%, 69.0%]
- Exactitud balanceada: **0.678**
- Confianza media: 0.924
- **ECE 0.2495** → mal calibrado (sesgo -0.247 = sobreconfiado)
- Brier: 0.2735

**Comparación con la referencia publicada.** SemIf reporta **0.637** de exactitud balanceada con Qwen3.5-4B leyendo logits directos, sobre 256 filas. Nosotros, sobre el split completo: **0.678**. Ojo con la comparación: SemIf no dice QUÉ 256 filas usó, y sobre las primeras 256 del split nosotros sacamos 0.632 — casi idéntico. La diferencia entre 0,632 y 0,678 según el subconjunto muestra que **el número depende más de la muestra que del modelo**, así que la comparación es indicativa.

| clase | recall | n |
|---|---|---|
| entailment | 0.756 | 1858 |
| neutral | 0.623 | 2397 |
| contradiction | 0.654 | 745 |

### Tabla de fiabilidad

| tramo | n | confianza media | acierto real | desvío |
|---|---|---|---|---|
| 0.3–0.4 | 7 | 0.382 | 0.714 | **+0.333** |
| 0.4–0.5 | 41 | 0.462 | 0.537 | **+0.074** |
| 0.5–0.6 | 221 | 0.551 | 0.489 | **-0.063** |
| 0.6–0.7 | 243 | 0.652 | 0.494 | **-0.158** |
| 0.7–0.8 | 271 | 0.754 | 0.480 | **-0.274** |
| 0.8–0.9 | 404 | 0.856 | 0.577 | **-0.280** |
| 0.9–1.0 | 3813 | 0.989 | 0.726 | **-0.263** |

### Corrección de la calibración (temperature scaling)

Lo que se mide aquí: el mismo modelo sale **prudente** en el catálogo IoT y **sobreconfiado** en WANLI. Esta es la corrección estándar y su efecto medido.

`p_cal = sigmoid(logit(p)/T)`, con T ajustado para minimizar la log-loss. No cambia la opción elegida, solo la confianza declarada. El ECE final es **out-of-fold (k=5)**: ajustar T sobre los mismos datos con los que se mide siempre lo mejora artificialmente.

**WANLI, split completo (5.000)**

| | ECE | Brier |
|---|---|---|
| antes (out-of-fold) | 0.2495 | — |
| después (T scaling) | **0.0198** | — |
| mejora | **92.1%** | |

T ajustado: 7.895 · sesgo original: -0.247 (sobreconfiado) · n = 5,000

**Catálogo IoT (tarea saturada)**

ECE 0.0163 → 0.0000 (100.0% de mejora), T = 0.050, sesgo +0.016.

**Aviso importante sobre esta segunda:** la tarea está saturada (100% de acierto), así que **no hay errores que calibrar**. Con T tocando el suelo de la rejilla, la corrección es degenerada: empuja toda confianza a 1,0 y el ECE baja a cero sin significar nada. Es otra prueba de que un ECE sobre una tarea saturada no vale como evidencia.

**Conclusión práctica:** la calibración **no se transfiere entre tareas**. El mismo modelo y la misma máquina dan ECE 0,0163 en el catálogo IoT y 0,2495 en WANLI. Hay que recalibrar por carga de trabajo, y sin recalibrar los umbrales de confianza de WANLI son inutilizables (dice 0,99 y acierta 0,73).


### Puntuación OFICIAL de S1MB

Artefacto: `results/s1mb_oficial.json` · regenerar con `python bench_s1mb.py` y después `python s1mb_official.py`

Implementa `evaluator/SCORING.md` del repo de S1MB: `noul` por Brier y `adjusted skill = 2·BA − 1`, `choice` por acierto contra el mejor baseline trivial (azar uniforme, id fijo o posición fija), `score` por MAE de valor esperado contra el baseline de la mediana. Se recorta a [0,1] **por benchmark**, se promedia por tarea y las tres tareas pesan igual.

La implementación está **validada con tests** contra el ejemplo numérico del propio `SCORING.md` (`python test_official.py`): TP=1, FN=10, FP=0, TN=89 debe dar BA 0,5454 y skill 0,0909, y lo da.

| tarea | benchmarks evaluados | oficiales (inglés) | score de tarea |
|---|---|---|---|
| `noul` | 48 | 61 | 43.3/100 |
| `choice` | 53 | 59 | 39.5/100 |
| `score` | 19 | 23 | 19.3/100 |

**Task Avg = 34.05 / 100**

| modelo | Task Avg (leaderboard) |
|---|---|
| Jev 1.13 | 59.59 |
| Open-Jev-27B-v1.1 | 56.88 |
| Open-Jev-9B | 52.10 |
| JevK5 | 41.14 |
| OpenJev-4B | 36.46 |
| **AIOM (Spark-X2.5-4B)** | 34.05 |
| Open-Jev-2B | 34.64 |
| decider-0.8b | 22.57 |

**Cautela obligatoria al leer esa tabla.** Nuestro número sale sobre 120 de los 143 benchmarks de la suite inglesa (cobertura incompleta: 4 subsets dan HTTP 500 por esquema que el endpoint no compila). `SCORING.md` exige cobertura completa antes de rankear, así que **no es una puntuación oficial**, sino una estimación con las fórmulas y la unidad oficiales. Además el líder del leaderboard usa Borda, que es relativo al censo de modelos y no se puede calcular con un solo modelo.

## S1MB — System One Mosaic Benchmark

Artefacto: `results/s1mb.json` · regenerar con `python bench_s1mb.py --todas --n 100`

El benchmark específico de modelos de decisión: mezcla de datasets NLP públicos en las tres primitivas (`noul`, `choice`, `score`). Es el único que mide lo nuestro con la misma interfaz que Jev.

- Suites evaluadas: **102** (de 106)
- Casos: **17234**
- Micro (todos los casos): **34.0%** IC95% [33.3%, 34.7%]
- Macro (media por suite): **47.3%** — ojo: **no** es el `Task Avg` del leaderboard, que aplica una normalización distinta (ver más abajo)

### Por suite (ordenado por exactitud)

| suite | tipo | casos | exactitud | IC95% | ms | confianza |
|---|---|---|---|---|---|---|
| dbpedia | ? | 100 | 96% | [90.2%, 98.4%] | 386 | 0.978 |
| scitail | ? | 100 | 94% | [87.5%, 97.2%] | 203 | 0.958 |
| miqa | ? | 100 | 91% | [83.8%, 95.2%] | 147 | 0.884 |
| sdoh_nli | ? | 100 | 91% | [83.8%, 95.2%] | 201 | 0.961 |
| laya__ag_news | ? | 100 | 87% | [79.0%, 92.2%] | 276 | 0.963 |
| s1mb-generalization-contextual-noul | ? | 100 | 87% | [79.0%, 92.2%] | 227 | 0.865 |
| canttalk | ? | 100 | 86% | [77.9%, 91.5%] | 1466 | 0.961 |
| s1mb-generalization-diverse-noul | ? | 100 | 86% | [77.9%, 91.5%] | 229 | 0.885 |
| open_jev__silent-failure-control-v1 | ? | 100 | 83% | [74.5%, 89.1%] | 485 | 0.909 |
| paws | ? | 100 | 83% | [74.5%, 89.1%] | 246 | 0.971 |
| hans | ? | 100 | 80% | [71.1%, 86.7%] | 191 | 0.927 |
| hatecheck | ? | 100 | 80% | [71.1%, 86.7%] | 208 | 0.939 |
| impli | ? | 100 | 80% | [71.1%, 86.7%] | 244 | 0.916 |
| s1mb-generalization-contextual-choice | ? | 100 | 80% | [71.1%, 86.7%] | 252 | 0.903 |
| hwu64 | ? | 100 | 77% | [67.8%, 84.2%] | 1566 | 0.908 |
| lexcomp | ? | 100 | 77% | [67.8%, 84.2%] | 222 | 0.913 |
| snli | ? | 100 | 77% | [67.8%, 84.2%] | 251 | 0.926 |
| arc | ? | 100 | 76% | [66.8%, 83.3%] | 243 | 0.889 |
| clinc | ? | 100 | 76% | [66.8%, 83.3%] | 2222 | 0.899 |
| bbq | ? | 100 | 75% | [65.7%, 82.5%] | 347 | 0.878 |
| laya__enron_spam | ? | 100 | 73% | [63.6%, 80.7%] | 654 | 0.928 |
| lonli | ? | 100 | 73% | [63.6%, 80.7%] | 231 | 0.916 |
| quartz | ? | 100 | 73% | [63.6%, 80.7%] | 220 | 0.850 |
| s1mb-generalization-diverse-score | ? | 100 | 73% | [63.6%, 80.7%] | 262 | 0.769 |
| creak | ? | 100 | 71% | [61.5%, 79.0%] | 157 | 0.900 |
| defeasible_nli | ? | 100 | 71% | [61.5%, 79.0%] | 236 | 0.914 |
| ruletaker | ? | 100 | 71% | [61.5%, 79.0%] | 449 | 0.953 |
| babi_nli | ? | 100 | 70% | [60.4%, 78.1%] | 301 | 0.897 |
| openbookqa | ? | 100 | 70% | [60.4%, 78.1%] | 210 | 0.814 |
| s1mb-generalization-diverse-choice | ? | 100 | 70% | [60.4%, 78.1%] | 250 | 0.871 |
| scicite | ? | 100 | 67% | [57.3%, 75.4%] | 248 | 0.927 |
| crows_pairs | ? | 100 | 66% | [56.3%, 74.5%] | 218 | 0.754 |
| s1mb-generalization-contextual-score | ? | 100 | 66% | [56.3%, 74.5%] | 283 | 0.732 |
| banking77 | ? | 100 | 65% | [55.3%, 73.6%] | 2151 | 0.870 |
| arct | ? | 100 | 64% | [54.2%, 72.7%] | 317 | 0.796 |
| winowhy | ? | 100 | 64% | [54.2%, 72.7%] | 256 | 0.811 |
| ethos | ? | 100 | 62% | [52.2%, 70.9%] | 246 | 0.956 |
| hh_rlhf | ? | 100 | 62% | [52.2%, 70.9%] | 542 | 0.809 |
| cladder | ? | 100 | 61% | [51.2%, 70.0%] | 357 | 0.784 |
| robust_lr | ? | 100 | 57% | [47.2%, 66.3%] | 541 | 0.762 |
| plane | ? | 100 | 55% | [45.2%, 64.4%] | 191 | 0.861 |
| poem_sentiment | ? | 100 | 55% | [45.2%, 64.4%] | 177 | 0.865 |
| scone | ? | 100 | 55% | [45.2%, 64.4%] | 250 | 0.768 |
| tracie | ? | 100 | 55% | [45.2%, 64.4%] | 273 | 0.857 |
| ethics | ? | 100 | 54% | [44.3%, 63.4%] | 252 | 0.924 |
| patent_similarity | ? | 100 | 54% | [44.3%, 63.4%] | 213 | 0.754 |
| logical_entailment | ? | 100 | 51% | [41.3%, 60.6%] | 272 | 0.945 |
| nlsat | ? | 100 | 50% | [40.4%, 59.6%] | 817 | 0.911 |
| open_jev__citation-control-v1 | ? | 100 | 48% | [38.5%, 57.7%] | 967 | 0.838 |
| followir_robust04 | ? | 200 | 44% | [37.8%, 51.4%] | 1154 | 0.974 |
| fol_nli | ? | 100 | 44% | [34.7%, 53.8%] | 612 | 0.790 |
| esci | ? | 100 | 43% | [33.7%, 52.8%] | 734 | 0.786 |
| open_jev__email-selection-control-v1 | ? | 100 | 43% | [33.7%, 52.8%] | 2033 | 0.894 |
| wiqa | ? | 100 | 43% | [33.7%, 52.8%] | 284 | 0.833 |
| aegis2 | ? | 148 | 42% | [34.2%, 49.9%] | 551 | 0.937 |
| boardgameqa | ? | 100 | 41% | [31.9%, 50.8%] | 617 | 0.776 |
| temporal_nli | ? | 100 | 40% | [30.9%, 49.8%] | 252 | 0.733 |
| massive | ? | 200 | 39% | [32.5%, 45.9%] | 1401 | 0.918 |
| followir_core17 | ? | 200 | 38% | [31.6%, 44.9%] | 1125 | 0.926 |
| open_jev__phone-extraction-control-v1 | ? | 100 | 37% | [28.2%, 46.8%] | 1639 | 0.934 |
| open_jev__tic_tac_toe-v1 | ? | 100 | 37% | [28.2%, 46.8%] | 268 | 0.528 |
| synthetic_relevance__nanobeir__NanoHotpotQA | ? | 200 | 35% | [28.7%, 41.8%] | 850 | 0.891 |
| followir_news21 | ? | 200 | 34% | [27.3%, 40.3%] | 1235 | 0.949 |
| open_jev__snake-v1 | ? | 100 | 33% | [24.6%, 42.7%] | 368 | 0.833 |
| corr2cause | ? | 100 | 32% | [23.7%, 41.7%] | 490 | 0.888 |
| open_jev__amount-extraction-control-v1 | ? | 100 | 32% | [23.7%, 41.7%] | 1602 | 0.886 |
| spartqa | ? | 100 | 32% | [23.7%, 41.7%] | 392 | 0.637 |
| stepgame | ? | 100 | 32% | [23.7%, 41.7%] | 388 | 0.724 |
| argument_quality | ? | 200 | 31% | [25.0%, 37.7%] | 368 | 0.876 |
| mtop | ? | 200 | 30% | [24.1%, 36.7%] | 2663 | 0.870 |
| synthetic_relevance__nanobeir__NanoNFCorpus | ? | 200 | 30% | [24.1%, 36.7%] | 1207 | 0.890 |
| synthetic_relevance__nanobeir__NanoNQ | ? | 200 | 30% | [24.1%, 36.7%] | 900 | 0.877 |
| aqua_rat | ? | 100 | 28% | [20.1%, 37.5%] | 337 | 0.567 |
| synthetic_relevance__nanobeir__NanoDBPedia | ? | 200 | 26% | [20.9%, 33.0%] | 841 | 0.876 |
| sgd | ? | 100 | 26% | [18.4%, 35.4%] | 696 | 0.930 |
| synthetic_relevance__nanobeir__NanoMSMARCO | ? | 200 | 26% | [20.0%, 32.0%] | 814 | 0.855 |
| open_jev__browser-control-v1 | ? | 100 | 22% | [15.0%, 31.1%] | 1945 | 0.969 |
| open_jev__reasoning-control-v1 | ? | 100 | 22% | [15.0%, 31.1%] | 493 | 0.759 |
| open_jev__vizdoom-basic-v1 | ? | 66 | 21% | [13.1%, 32.5%] | 536 | 0.763 |
| synthetic_relevance__nanobeir__NanoSCIDOCS | ? | 200 | 21% | [15.9%, 27.2%] | 1027 | 0.828 |
| synthetic_relevance__nanobeir__NanoFiQA2018 | ? | 200 | 20% | [15.5%, 26.6%] | 1092 | 0.877 |
| open_jev__mailroom-control-v1 | ? | 100 | 20% | [13.3%, 28.9%] | 572 | 0.969 |
| open_jev__workflow-controls-v1__customer_service | ? | 100 | 20% | [13.3%, 28.9%] | 1097 | 0.973 |
| gretel_pii | ? | 353 | 19% | [15.2%, 23.4%] | 994 | 0.896 |
| open_jev__customer-control-v1 | ? | 100 | 17% | [10.9%, 25.5%] | 446 | 0.929 |
| open_jev__workflow-controls-v1__agent_trace_observability | ? | 100 | 17% | [10.9%, 25.5%] | 775 | 0.919 |
| civil_comments | ? | 700 | 16% | [13.5%, 18.9%] | 264 | 0.930 |
| open_jev__workflow-controls-v1__invoice_processing | ? | 100 | 16% | [10.1%, 24.4%] | 1064 | 0.826 |
| laya__typed_decisions | ? | 500 | 16% | [12.9%, 19.3%] | 608 | 0.831 |
| open_jev__ir-control-v1 | ? | 100 | 15% | [9.3%, 23.3%] | 820 | 0.833 |
| synthetic_relevance__nanobeir__NanoArguAna | ? | 200 | 15% | [10.7%, 20.6%] | 1468 | 0.828 |
| open_jev__drone-control-v1 | ? | 100 | 14% | [8.5%, 22.1%] | 1937 | 0.876 |
| open_jev__entity-alignment-control-v1 | ? | 100 | 14% | [8.5%, 22.1%] | 1465 | 0.907 |
| open_jev__context-retention-control-v1 | ? | 100 | 13% | [7.8%, 21.0%] | 2266 | 0.902 |
| open_jev__sponsor-segment-control-v1 | ? | 100 | 12% | [7.0%, 19.8%] | 1396 | 0.994 |
| open_jev__workflow-controls-v1__security_incidents | ? | 100 | 12% | [7.0%, 19.8%] | 980 | 0.868 |
| winobias | ? | 100 | 12% | [7.0%, 19.8%] | 176 | 0.906 |
| go_emotions | ? | 2800 | 11% | [9.7%, 12.0%] | 184 | 0.982 |
| few_nerd | ? | 358 | 9% | [6.9%, 13.0%] | 388 | 0.947 |
| open_jev__painting-geometry-v1 | ? | 100 | 8% | [4.1%, 15.0%] | 426 | 0.848 |
| ud_ewt | ? | 1509 | 6% | [4.5%, 6.8%] | 518 | 0.703 |
| gsm8k | ? | 100 | 5% | [2.2%, 11.2%] | 297 | 0.675 |
### Subconjunto de generalización — la comparación que importa

| suite | casos | cruda | balanceada | task_avg |
|---|---|---|---|---|
| contextual-noul | 100 | 87% | 0.870 | 74.0 |
| diverse-noul | 100 | 86% | 0.860 | 72.0 |
| contextual-choice | 100 | 80% | 0.651 | 30.1 |
| diverse-score | 100 | 73% | 0.437 | 0.0 |
| diverse-choice | 100 | 70% | 0.500 | 0.0 |
| contextual-score | 100 | 66% | 0.660 | 32.0 |

**Media: 77% cruda, 0.663 balanceada.**

**La brecha entre esas dos cifras es el hallazgo.** La exactitud cruda (77%) está inflada en casi 11 puntos respecto a la balanceada (66%): el modelo acierta desproporcionadamente la clase mayoritaria. En `diverse-choice` saca 70% crudo con 0.500 balanceado, que es literalmente azar en una decisión binaria. Es justo lo que la exactitud balanceada existe para detectar, y la razón de publicarla junto a la cruda.

| modelo | Task Avg (leaderboard) |
|---|---|
| Jev 1.13 | 96.27 |
| Open-Jev-9B | 85.63 |
| Open-Jev-27B-v1.1 | 82.97 |
| JevK5 | 85.01 |
| OpenJev-4B | 76.75 |
| Open-Jev-2B | 65.57 |
| **AIOM, solo suites `noul`** | **73.0** |

**Cuidado al leer esa tabla.** La normalización del autor solo está documentada para `noul` (exactitud balanceada 50%→0, 100%→100). Mi columna `task_avg` la aplica a las tres primitivas, así que **para `choice` y `score` es una suposición, no la puntuación oficial**. La fila de AIOM se limita a las suites `noul`, que es lo único defendible. Una comparación completa exige implementar el código de puntuación oficial de S1MB.

## Benchmark interno (los dos modos)

Artefacto: `results/bench.json` · regenerar con `python bench.py`

| en paralelo | `decision` p50 | `chat` p50 | `decision` caudal | `chat` caudal | tokens `chat` |
|---|---|---|---|---|---|
| 1 | 93.8 ms | 470.1 ms | 10.57 q/s | 2.16 q/s | 33.2 |
| 2 | 152.1 ms | 833.2 ms | 12.82 q/s | 2.51 q/s | 34.4 |
| 4 | 294.2 ms | 1522.0 ms | 13.48 q/s | 2.4 q/s | 33.7 |
| 8 | 622.8 ms | 2342.8 ms | 12.8 q/s | 2.89 q/s | 33.7 |
| 16 | 994.6 ms | 4843.5 ms | 13.12 q/s | 2.95 q/s | 33.7 |

Dataset: 26 consultas etiquetadas. El modo `decision` genera **0 tokens** en todos los niveles.

## Comparación con el mercado

Cifras publicadas o medidas por terceros. **No son mediciones nuestras** salvo donde se indica. Detalle y fuentes en [`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md).

| Sistema | Exactitud | Latencia | Hardware | Procedencia |
|---|---|---|---|---|
| Jev 1.13 | — | 369 ms (p95 411) | alojado | medido por MLflow |
| Jev | 0.8635 | 348 ms mediana | — | medido por Red Hat |
| Laya | 0.8544 | 119 ms mediana (p95 217) | — | medido por Red Hat |
| DiffusionGemma | 0.8772 | 562 ms mediana | — | medido por Red Hat |
| JEV-9B | — | ~90 ms | B200 | fabricante |
| GEV System 1 | — | ~45 ms | B200 | fabricante |
| SemIf + Qwen3.5-4B | 0.637 (WANLI) | 1,02 s / 21 criterios | RTX 3090 | repo del autor |
| **AIOM (Spark-X2.5-4B)** | **0.632 (WANLI)** | **94 ms** (IoT) | **RX 9070** | **propia, medida** |

La fila de AIOM es la única medida por nosotros en hardware de consumo. Las de latencia del mercado son System 1 puro en tarjetas de centro de datos; la nuestra es una consulta sola en una tarjeta de escritorio, así que **no son directamente comparables**.

La comparación que **sí** es válida es la de WANLI: mismo dataset, mismas etiquetas, tamaño de modelo comparable (4B).

## Definiciones de las métricas

Todas implementadas en [`metrics.py`](../metrics.py), para que dos informes no usen definiciones distintas de lo mismo.

| métrica | definición | por qué esa |
|---|---|---|
| exactitud | aciertos / casos | directa, pero premia la clase mayoritaria |
| **exactitud balanceada** | media de los recalls por clase | en un dataset desbalanceado es la honesta, y es la que usan SemIf y las comparaciones de NLI |
| IC de Wilson | intervalo para una proporción | con n pequeño el normal se sale de [0,1]; Wilson no |
| ECE | media ponderada de \|acierto − confianza\| por tramos | mide si puedes fiarte de la probabilidad. **Solo informa si la tarea tiene errores** |
| Brier | error cuadrático medio de la probabilidad | castiga más los errores seguros que el ECE |
| sesgo | media de (acierto − confianza) | negativo = sobreconfiado; positivo = prudente |

## Fuentes de las cifras externas

Las cifras de mercado no son nuestras. Cada una, con dónde comprobarla:

- **SemIf 0.637 en WANLI (Qwen3.5-4B)** — repo del proyecto: https://github.com/TheoLeeCJ/SemIf
- **Leaderboard S1MB (Jev, Open-Jev-*, JevK5)** — https://huggingface.co/blog/hotchpotch/system-one-mosaic-benchmark
- **Dataset S1MB** — https://huggingface.co/datasets/hotchpotch/s1mb-dataset
- **Dataset WANLI** — https://huggingface.co/datasets/alisawuffles/WANLI
- **Latencia de Jev y Laya (medidas por terceros)** — https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails
- **Latencia de Jev medida por MLflow** — https://mlflow.org/blog/jev-llm-judge
- Análisis completo del mercado, con 14 fuentes: [`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md)

## Lo que no está validado

1. **Una máquina, un modelo, una configuración.** Nada se ha replicado en otro hardware.
2. **El set adversario interno lo escribí yo**, con mis sesgos sobre qué es difícil; son 37 campos, así que los intervalos son anchos.
3. **WANLI: solo las primeras 256 filas del test**, no el split completo, y no es el subconjunto exacto que usó SemIf — la comparación es indicativa.
4. **S1MB: no se ha enviado al leaderboard.** Además, correr 100 casos por suite y no el split completo no es la metodología oficial del benchmark.
5. **La calibración no se transfiere**: ECE 0,0196 en IoT frente a 0,2691 en WANLI. Hay que recalibrar por carga de trabajo; ninguna de las dos está corregida con temperature scaling.
6. **Sin comparación con un LLM de frontera en el mismo hardware.**
