# Estado del arte — modelos de decisión

Investigación sobre la familia de modelos que AIOM imita: quién es quién, por qué
son rápidos, cuán certeros son y con qué benchmarks medirse.

**Cómo leer este documento.** Las cifras de los fabricantes están marcadas como
tales; son afirmaciones de marketing hasta que un tercero las mide. Donde hay
medición independiente se dice quién la hizo. Nuestros propios números son de un
dataset propio, así que la comparación con el mercado es **indicativa, no
rigurosa** — para ser riguroso hay que adoptar un benchmark estándar (§6).

---

## 1. Qué es un modelo de decisión

Le das un **estado** (un correo, un ticket, un JSON) y **preguntas tipadas**, y en
vez de escribir devuelve **una probabilidad por cada respuesta posible** en una
sola pasada. El software consume el número, no un texto que hay que interpretar.[1]

Tres primitivas, definidas por Jev y ya de facto estándar:[1][12]

| primitiva | qué hace | ejemplo |
|---|---|---|
| `noul` | sí/no, devuelve P(falso) y P(verdadero) | «¿pide un reembolso?» |
| `choice` | elige de tu lista de opciones | «¿qué cola: facturación, envío, soporte?» |
| `score` | puntúa contra una rúbrica 0–5 | «¿cuánta urgencia tiene?» |

---

## 2. Quién es quién

### Jev — TypeSafe AI (cerrado, alojado)

Lanzado el 15 de septiembre de 2026. El que puso el nombre a la categoría. No
publica pesos: se llama su API.[1]

- Latencia publicada: **70–500 ms**; contexto 64k; hasta 255 opciones por elección.[1]
- Precio: **$0.042–0.084 por millón de tokens de entrada, salida gratis**. La salida
  es gratis porque no hay salida que facturar: cero tokens generados.[1]
- Entrenado con **RLCD** (Reinforcement Learning for Calibrated Decisions), no con
  RLHF: premia que la probabilidad sea honesta, no que el texto guste a un
  evaluador humano.[1]

Medición **independiente** (MLflow, 30 ejemplos etiquetados a mano):[2]

| Juez | Acuerdo con humano | Latencia mediana | p95 | Coste /1.000 juicios |
|---|---|---|---|---|
| Jev 1.13.0 | 30/30 (100%) | **369 ms** | **411 ms** | **$0.0247** |
| GPT-5.6 Terra | 30/30 (100%) | 1.091 ms | 1.924 ms | $0.8960 |
| GPT-5.6 Luna | 30/30 (100%) | 947 ms | 1.435 ms | $0.0896 |
| Claude Sonnet 4.6 | 27/30 (90%) | 1.610 ms | 3.546 ms | $1.6721 |
| Claude Opus 4.8 | 28/30 (93.3%) | 1.966 ms | 9.279 ms | $3.7750 |
| DeepSeek-V4.1-Flash | 29/30 (96.6%) | 910 ms | 1.188 ms | $0.0624 |

Misma precisión que los mejores, **2,6–5,3x menos latencia** y hasta **36x más
barato**.[2]

### La familia JEV/GEV — AutoTrust AI (abierta, Apache 2.0)

> **Aquí está tu GEV.** Es `GEV-26B-Decide`, de AutoTrust AI, construido sobre
> **Gemma 4 26B-A4B** (MoE, ~4B activos). Renombrado el 2 de octubre; antes se llamó
> `JEV-Gemma4-26B-A4B`. **No está afiliado a TypeSafe.**[5]

Los cuatro modelos, al 6 de octubre de 2026:[5]

| Modelo | Base | Descarga | Visión | Fuerte en |
|---|---|---|---|---|
| JEV-9B | Qwen3.5-9B | ~18 GB | sí | velocidad; el más rápido |
| JEV-27B | Qwen3.8-27B | ~54 GB | no | lo más cercano a Jev |
| JEV-27B-VL | Qwen3.8-27B + visión | ~54 GB | sí | capturas, 256K tokens |
| **GEV-26B-Decide** | **Gemma 4 26B-A4B** | **~49,5 GB (18 GB en NVFP4)** | sí | pensamiento adaptativo |

Receta «Blocks of Experts»: **no reentrenan la base**. Añaden un bloque separable
entrenado solo para decisiones — 40,2 M de parámetros en JEV-9B (**0,5% del
backbone**), entrenado en ~3 h en una B200. Mantenerlo separable tiene premio
medible: JEV-9B conserva HumanEval 70,7% con el bloque puesto, idéntico a la base,
y las 164 respuestas son byte a byte iguales. Fundirlo en el backbone habría
costado 9 puntos (61,6%).[5]

**GEV añade pensamiento adaptativo:** con `"thinking": "auto"` responde al instante
si su confianza supera un umbral (0,8 por defecto) y se detiene a razonar si no.
Razonar cuesta ~1 s por cada 250 tokens de pensamiento.[5]

Velocidad en una B200 (hardware del fabricante): JEV-9B ~90 ms mediana, ~340
decisiones/s; JEV-27B ~137 ms; **GEV System 1 ~45 ms, ~257 decisiones/s con 64
clientes**.[5]

### Laya — convaiinnovations (abierta, Apache 2.0) — **la más rápida**

Modelo multilingüe no autoregresivo, **backbone ModernBERT**. Devuelve
probabilidades calibradas en una sola pasada: **~33 ms**, más de 100 idiomas.[6][11]

Medición **independiente** de Red Hat contra guardarraíles tradicionales:[6]

| Método | Exactitud | Latencia media | Mediana | p95 |
|---|---|---|---|---|
| **Laya** | 0.8544 | 134,7 ms | **119,3 ms** | **216,9 ms** |
| DiffusionGemma | 0.8772 | 552,9 ms | 561,7 ms | 630,8 ms |
| Jev | 0.8635 | 366,7 ms | 348,1 ms | 478,4 ms |

**Laya es 2,9x más rápida que Jev con casi la misma exactitud.** No es magia: es un
**encoder**, no un decoder. Un encoder procesa la secuencia entera en una pasada;
un decoder autoregresivo paga un forward por token.

### SemIf (antes OpenJev) — TheoLeeCJ (MIT) — **el más cercano a lo que hacemos**

No es un modelo: es un **runtime**. Coge un modelo abierto **congelado** (Qwen3.5-4B
por defecto) y **lee los logits de las opciones declaradas** en una sola pasada. Ni
fine-tuning ni cambio de pesos.[4]

Es el proyecto que valida directamente nuestro enfoque, y su comparación de
velocidad es prácticamente idéntica a la nuestra:

| Ruta de salida | Tiempo | Tokens de salida |
|---|---|---|
| Logits tipados directos | **1,023 s** | **0** |
| Array JSON autoregresivo | 5,332 s | 111 |

**5,21x más rápido, cero tokens.**[4] Nuestra medición independiente dio **5,0x,
cero tokens** (§5). Dos implementaciones distintas, misma cifra: el efecto es real
y reproducible.

### OpenJev-27B — ojo con la licencia

Es el 27B que llama.cpp soporta vía `/v1/systemone`, pero está bajo
**CC BY-NC 4.0**: **prohíbe uso comercial**. Para un producto o un cliente, la ruta
legal son los modelos de la familia JEV (Apache 2.0).[5]

---

## 3. Por qué son rápidos — el mecanismo, no el marketing

Todo se reduce a **una** diferencia estructural:[1][3][4]

> Un LLM genera su respuesta **token a token**: cada token es un forward completo.
> Un modelo de decisión **no genera**: hace **un** forward y lee los logits en las
> posiciones de las opciones declaradas.

Consecuencias medibles:

1. **Cero tokens generados.** No es «menos tokens»: es ninguno. La latencia deja de
   escalar con la longitud de la respuesta.[3][4]
2. **Preguntas en paralelo.** Todas las preguntas sobre un mismo estado se evalúan
   en la misma pasada. Añadir preguntas casi no cuesta latencia.[1][3]
3. **La latencia apenas se mueve** con el tamaño de la entrada, el ancho del
   contrato o el catálogo de opciones.[3]
4. **Salida tipo-segura por construcción.** El espacio de salida está prefijado: el
   modelo **no puede** inventar un valor fuera del conjunto. La «alucinación» deja
   de ser probable y pasa a ser imposible.[1]

El paper de edge orchestration lo cuantifica: Jev reduce la **latencia mediana de
decisión un 22,7–64,5%** frente al LLM más rápido, y en 7 de 8 condiciones iguala el
número de respuestas correctas de DeepSeek (en 1 lo supera).[3]

---

## 4. Cuán certeros son, y por qué

### El truco del entrenamiento: RLCD

RLCD premia **probabilidades honestas**, no texto que agrade. Un modelo cuya
confianza es 0.8 debe acertar ~80% de las veces en ese tramo. Se apoya en
**reglas de puntuación propias** (proper scoring rules) de la teoría de pronóstico
probabilístico.[1]

Por qué importa: un clasificador que acierta el 90% pero dice «99% seguro» en todo
es inservible para decidir, porque todos los casos parecen iguales a tu
`if`. RLCD gobierna cuánto puedes fiarte del número, no solo la exactitud.[1]

Ojo con la distinción: **la exactitud es la frecuencia con que acierta; la
calibración es cuánto vale su probabilidad.** Son ejes distintos.[1]

### Exactitud medida por terceros

**S1MB** (System One Mosaic Benchmark, 100+ benchmarks, media de tareas tipo
Borda):[7]

| Modelo | Borda | Task Avg | Noul | Choice | Score |
|---|---|---|---|---|---|
| Jev 1.13 | **86,51** | 59,59 | 64,63 | 67,22 | 46,92 |
| Open-Jev-9B | 72,54 | 52,10 | 55,76 | 55,51 | 45,04 |
| Open-Jev-27B-v1.1 | 72,35 | 56,88 | 51,48 | 66,91 | 52,26 |
| JevK5 | 67,49 | 41,14 | 48,93 | 52,84 | 21,65 |

En generalización, la brecha se cierra bastante: Jev 97,73 vs Open-Jev-9B 88,26.[7]

**SemIf** (exactitud balanceada, 4B congelado, solo leyendo logits):[4]

| Sistema | Autoría propia | Perturbado | Acuerdo con Jev |
|---|---|---|---|
| Qwen3-0.6B | 0.440 | 0.528 | 0.407 |
| MiniCPM5-2B | 0.686 | 0.693 | 0.637 |
| **Qwen3.5-4B** | **0.813** | **0.766** | **0.845** |
| Jev publicado | — | — | 0.883 |

**Un modelo abierto de 4B congelado queda a 4 puntos de Jev.** No hace falta
entrenar nada para tener un modelo de decisión decente.

**Calibración** (ECE, error de calibración esperado — más bajo es mejor):[4]

| Carga | ECE crudo | ECE calibrado | Temperatura |
|---|---|---|---|
| Decisiones propias | 0.068 | **0.038** | 1.23 |
| WANLI | 0.208 | **0.069** | 2.50 |
| Every judgments | 0.050 | 0.047 | 1.71 |

Se arregla con **temperature scaling** ajustado sobre datos etiquetados. La
calibración no cambia la opción elegida, solo la confianza que declaras.[4]

---

## 5. Cómo nos comparamos

Nuestras cifras (`docs/ESTUDIO.md`, medido en una RX 9070 por Vulkan):

| | AIOM `decision` | AIOM `chat` |
|---|---|---|
| latencia p50 | 93,8 ms | 470,1 ms |
| latencia p95 | 112,7 ms | 510,9 ms |
| caudal | 10,57 q/s | 2,16 q/s |
| tokens | 0 | 33,2 / consulta |
| acierto | 53/53 (100%) | 49/53 (92,5%) |

Y comparado con el mercado:

| Sistema | Latencia | Hardware | Fuente |
|---|---|---|---|
| GEV System 1 | ~45 ms | B200 | fabricante [5] |
| Laya | 33 ms (mediana 119 ms) | — / medido por Red Hat [6] | [6][11] |
| JEV-9B | ~90 ms | B200 | fabricante [5] |
| **AIOM (Spark-X2.5-4B)** | **93,8 ms** | **RX 9070 (consumo)** | propia [§5] |
| JEV-27B | ~137 ms | B200 | fabricante [5] |
| Jev | 369 ms | alojado | MLflow [2] |

**Estamos en el pelotón de cabeza**, y en hardware de consumo (la RX 9070 no es una
B200). El matiz honesto: los 45–90 ms son System 1 puro en tarjetas de centro de
datos con clientes en paralelo; nuestros 93,8 ms son una consulta sola en una
tarjeta de escritorio.

El dato que más nos avala no es nuestro: es que **SemIf obtuvo 5,21x y nosotros
5,0x**, con implementaciones independientes.[4] Y nuestro escalado al agrupar
(796 → 29,9 ms por decisión) supera el de SemIf (2,33 → 20,03 decisiones/s, 8,6x),
aunque sobre cargas distintas, así que no es comparable de forma estricta.

---

## 6. Benchmarks estándar con los que medirnos

Esta es la parte que nos falta: hoy medimos con un dataset propio de 26 consultas,
así que **ningún número nuestro es comparable con la industria**. Los candidatos,
por idoneidad:

### 6.1 S1MB — System One Mosaic Benchmark ← el más adecuado

El benchmark específico de modelos de decisión. Compara más de 100 benchmarks y
publica **Borda Score + Task Avg** con desglose por primitiva (Noul / Choice /
Score), y además un subconjunto de generalización.[7]

Es el único que mide exactamente lo nuestro con la misma interfaz (`noul`/`choice`/
`score`). **Es el que hay que adoptar.**

### 6.2 JevBench

Leaderboard público que ya lista **más de 60 modelos comunitarios estilo Jev**. Es
donde está la comunidad open-source.[10]

### 6.3 Metodología de Red Hat (guardarraíles)

Compara modelos de decisión contra guardarraíles tradicionales con **exactitud,
precisión, recall y F1 por separado para «permitido» y «bloqueado», más media,
mediana y p95 de latencia**.[6] Su tabla es el mejor modelo de cómo hay que
reportar: no una exactitud suelta, sino el desglose completo con colas.

**Adoptar su formato de tabla para nuestro informe.**

### 6.4 El fixture de SemIf

144 filas de decisiones propias + 256 de **WANLI** (dataset público de inferencia en
lenguaje natural) + calibración con ECE.[4] WANLI es la parte valiosa: es un
**dataset público externo**, así que da una cifra comparable. Incluye ECE, que
nosotros no medimos y deberíamos.

### 6.5 JSONSchemaBench

10.000 esquemas JSON reales; mide **eficiencia, cobertura y calidad** del decoding
restringido. Incluye **MaskBench**, centrado en el tiempo de cómputo de máscaras —
justo el coste que nosotros vemos como `scoring_ms`.[8][13]

Útil para la parte de esquema: responde «qué formas de esquema son caras», que es
lo que ya intuimos con el campo entero 1–99.

### 6.6 BFCL v4

El estándar de *function calling*, con columnas de **Coste y Latencia** ya en el
leaderboard.[9] Menos específico para nosotros (nosotros no elegimos herramientas),
pero es el lenguaje común que la industria entiende.

---

## 7. Cómo mejorar nuestros tiempos

Ordenado por relación mejora/esfuerzo, con la evidencia de cada uno.

| # | Palanca | Ganancia medida | Estado |
|---|---|---|---|
| 1 | **Agrupar consultas en una petición** | 1,25x vs 16 HTTP; monótono con el lote | **hecho** |
| 2 | **Reutilizar el prefijo + ramas paralelas** | SemIf: 2,33 → 20,03 dec/s (8,6x) | **hecho** (nuestro 796→29,9 ms) |
| 3 | **Ajustar el esquema** (menos `rounds`) | entero 1–99 → 1–12: confianza 0.57→1.000, nodos 10→2 | **hecho** |
| 4 | **Backbone encoder en vez de decoder** | Laya: 33 ms con ModernBERT | pendiente |
| 5 | **Modelo más pequeño** | JEV-9B 2,6x más rápido que JEV-27B | pendiente |
| 6 | **Ajustar `--decision-seqs` y `-np` del servidor** | sin medir | pendiente |
| 7 | **Calibración post-hoc** (temperature scaling) | ECE 0.208 → 0.069 en WANLI | pendiente |
| 8 | **Destilar un bloque de decisión** | 0,5% de parámetros extra, 3 h en una B200 | no aplica (ya usamos el endpoint) |
| 9 | **Evitar 4-bit** | Q4_K_M: 92,9% de acuerdo = 1 de cada 14 decisiones cambia | **hecho** (usamos Q8_0) |

Las tres palancas grandes ya están explotadas. Lo que queda con más recorrido es la
**4** (encoder) y la **6** (configuración del servidor), y ninguna de las dos la he
medido — así que no afirmo nada sobre ellas.

---

## 8. La trampa del GGUF — aviso importante

Si alguna vez descargas un «Jev» en GGUF, esto te va a morder:[5]

> **Las versiones GGUF populares de JEV-9B, JEV-27B y GEV-26B-Decide no contienen la
> parte de decisión.** Son Qwen y Gemma planos con una etiqueta Jev, porque el
> adaptador, la cabeza de decisión y los ficheros de calibración viven en archivos
> aparte que la conversión deja fuera.[5]

| Repositorio GGUF | Qué contiene | ¿Decide? |
|---|---|---|
| mradermacher/GEV-26B-Decide-GGUF | solo pesos + visión: Gemma 4 26B-A4B plano | **No** |
| prithivMLmods/JEV-27B-GGUF | Qwen3.8-27B plano | **No** |
| prithivMLmods/JEV-9B-GGUF, mradermacher/JEV-9B-GGUF | solo `.gguf`, sin adaptador ni cabeza | **No** |
| Atlas3D/JEV-27B-VL-GGUF | pesos **con** la lectura de decisión + parche de llama.cpp | **Sí**, con parche |

**Cómo distinguir uno real:** busca `head.safetensors`, una carpeta `adapter/` y
`calibration.json`. Si solo hay `.gguf` y quizá un `mmproj`, no puede decidir.
Prueba definitiva: hazle una pregunta de sí/no. Un System 1 real devuelve números
para `false` y `true`; un modelo hueco escribe párrafos.[5]

Y la cuantización daña las decisiones más que el chat: Q8_0 coincide con precisión
completa en **99,0%** de las decisiones; Q4_K_M en **92,9%** — **una de cada catorce
sale distinta**.[5] En chat eso apenas se nota; en una decisión, cambia la respuesta.
Nosotros corremos Q8_0, que es la elección correcta.

---

## 9. Lo que no he verificado

Digo explícitamente lo que **no** sé, para que nadie lo tome por bueno:

- No he ejecutado Jev, Laya, GEV ni ningún modelo del mercado. Todo lo suyo son
  cifras publicadas o medidas por terceros, citadas como tales.
- No hemos corrido ningún benchmark estándar (§6), así que **la comparación de §5 es
  indicativa**: nuestro 100% es sobre 53 campos de nuestro dataset, no sobre S1MB.
- Las cifras «de fabricante» (45–137 ms en B200) no son independientes.
- El escalado al agrupar se midió en una sola ejecución por nivel y en una sola
  máquina, sin promediar sobre varias corridas.
- La palanca 4 (encoder) y la 6 (configuración del servidor) están sin medir.

## Sources

[1] https://typesafe.ai/blog/introducing-system-one-models-and-jev — TypeSafe AI - Introducing System One Models & Jev
[2] https://mlflow.org/blog/jev-llm-judge — MLflow - Can Jev replace your LLM judge
[3] https://arxiv.org/html/2609.22753v1 — Replacing LLMs with Jev Decision Models for Low-Latency Edge Service Orchestration
[4] https://github.com/TheoLeeCJ/SemIf — SemIf (formerly OpenJev) - typed decisions from open models
[5] https://www.logeshwaran.org/2026/10/open-source-jev-models-jev-27b-gev-26b.html — Open-Source Jev AI Models: JEV-9B, JEV-27B-VL and GEV-26B-Decide (the GGUF trap)
[6] https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails — Red Hat - Benchmarking AI decision models against traditional guardrails
[7] https://huggingface.co/blog/hotchpotch/system-one-mosaic-benchmark — S1MB - comparing System One Decision Models across 100+ benchmarks
[8] https://arxiv.org/abs/2501.10868 — JSONSchemaBench: A Rigorous Benchmark of Structured Outputs
[9] https://gorilla.cs.berkeley.edu/leaderboard.html — Berkeley Function Calling Leaderboard (BFCL) V4
[10] https://arxiv.org/html/2610.02076v2 — LLM-as-Jev: LLMs Are Already Jev-Style Decision Models
[11] https://huggingface.co/convaiinnovations/laya — convaiinnovations/laya - multilingual decision model
[12] https://docs.langchain.com/langsmith/llm-gateway-decision-models — LangChain - Decision models in LangSmith LLM Gateway
[13] https://github.com/guidance-ai/jsonschemabench — guidance-ai/jsonschemabench + MaskBench
