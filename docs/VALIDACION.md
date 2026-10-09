# Validación — qué está medido y qué no

Todo número de este documento sale de una ejecución real en la máquina objetivo y
es reproducible con los scripts del repo. Donde una cifra es débil, se dice.

**Máquina:** Windows 11, Radeon RX 9070 (16 GB) por Vulkan, backend
`parallel-decision` de llama.cpp, modelo Spark-X2.5-4B Q8_0.

---

## 1. Resumen

| Medición | Resultado | ¿Informa? |
|---|---|---|
| Acierto, dataset base (26 consultas) | **53/53 (100%)** | **No** — saturado |
| Acierto, set adversario (24 casos) | **33/37 (89%)** | **Sí** |
| Latencia (20 reps × 26 consultas) | **93,8 ms** (desv 9,6) | Sí |
| Calibración ECE | **0,0196** | Débil — sobre tarea saturada |
| Nodos puntuados / rondas | 5,0 / 1,0 | Sí |

**El titular honesto no es 100%.** El dataset base está saturado: acierta todo, así
que no puede medir nada más. La cifra que informa es el **89% del set adversario**.

---

## 2. Acierto con intervalos de confianza

`exp_stats.py 10` — 10 repeticiones sobre el dataset base, intervalo de Wilson:

| Campo | Acierto | IC95% |
|---|---|---|
| magnitud | 200/200 (100%) | [98,1%, 100,0%] |
| predio | 200/200 (100%) | [98,1%, 100,0%] |
| urgencia | 130/130 (100%) | [97,1%, 100,0%] |

Variación **entre corridas: 0,00 pp** de desviación → estable.

El intervalo inferior de 98,1% es lo que dice el dato: no podemos afirmar 100%
exacto con 200 muestras, sino «al menos 98%». Es la diferencia entre un número y
una cifra validada.

## 3. Set adversario — dónde se rompe

`exp_stress.py`. 24 casos deliberadamente difíciles, por categoría:

| Categoría | Casos | Acierto | IC95% |
|---|---|---|---|
| `negacion` | 2 | 4/4 (100%) | [51%, 100%] |
| `fuera_cat` | 3 | 3/3 (100%) | [44%, 100%] |
| `multi_predio` | 1 | 1/1 (100%) | [21%, 100%] |
| `implicito` | 5 | 9/10 (90%) | [60%, 98%] |
| `fuera_rango` | 4 | 6/7 (86%) | [49%, 97%] |
| **`distractor`** | **6** | **10/12 (83%)** | **[55%, 95%]** |

**El punto débil es `distractor`**: cuando otro número compite con el predio
(«el **nodo 4** del predio 9»), acierta 10 de 12. Los intervalos son anchos porque
las muestras son pocas — con 6 casos no se puede afirmar mucho más.

---

## 4. El fallo que encontré (y que yo mismo introduje)

Al acotar `predio` a 1–12 para arreglar el redondeo a la decena, apareció un modo
de fallo peor que el original: **un predio inexistente no se rechaza, se recorta a
un valor válido.**

```
"el predio 30 ... sin reportar humedad"  ->  predio=12
"revisen la temperatura del predio 45"   ->  predio=4
"el predio 99 manda datos raros"         ->  predio=9
"alerta de bateria en el predio 18"      ->  predio=12
"el sensor del predio 57 no responde"    ->  predio=5
```

La probabilidad que declara el campo va de **0,60 a 0,94** — no siempre 1,0 como
dije en una medición previa, donde estaba promediando la confianza de *todos* los
campos en lugar de la del `predio` solo. El fallo es real, pero era menos grave de
lo que reporté primero.

Por qué importa: en un sistema automatizado, una alerta de un predio inexistente se
enruta al predio 12 sin que nadie se entere. **Mentir con seguridad es peor que
fallar visiblemente.**

### El arreglo, y su coste medido

`exp_rango.py`. Un campo booleano explícito que declara la validez en vez de
disimularla:

| | Resultado |
|---|---|
| Detección de fuera de rango | **4/5 (80%)** |
| Falsos positivos sobre predios válidos | **0/5** |
| Coste en latencia | **+2,3 ms (+2,5%)** |
| Coste en nodos puntuados | **+1,0** |

A/B controlado, 20 repeticiones × 26 consultas:

```
sin predio_valido :  93,8 ms (desv 9,6)   5,0 nodos
con predio_valido :  96,1 ms (desv 8,6)   6,0 nodos
```

Un booleano extra cuesta ~2,5% de latencia. Es barato para el fallo que evita.

**Y sigue recortando.** El arreglo no impide que `predio` devuelva 12; añade una
señal paralela que dice que no es de fiar. **El llamante tiene que comprobarla.** Si
tu código lee `predio` e ignora `predio_valido`, no has arreglado nada.

El caso que se le escapa es «predio 45», que devuelve `predio_valido=true`.

---

## 5. Latencia

| Métrica | Valor |
|---|---|
| media | 99,7 ms, IC95% [95,1, 104,2] (10 reps del set base) |
| media | 93,8 ms, desv 9,6 (A/B de 20 reps × 26 consultas) |
| p50 | 96,1 ms |
| p95 | 114,9 ms |
| min / max | 71,7 / 161,8 ms |

El A/B a 20 repeticiones es la cifra más sólida: **93,8 ms** con desviación 9,6.
La media de 99,7 ms sale de otra corrida y cae dentro del intervalo.

Coste del esquema, medido: **5,0 nodos puntuados y 1,0 rondas** por consulta. La
ronda bajó de 3 a 1 al acotar `predio` de 1–99 a 1–12. Ese cambio fue gratis y
además subió la confianza de 0,57 a 1,000.

---

## 6. Calibración

`exp_stats.py`. 530 decisiones de campo, verdad de referencia conocida.

| Métrica | Valor | Referencia |
|---|---|---|
| **ECE** | **0,0196** | SemIf reporta 0,038–0,208 crudo [4] |
| Brier | 0,0032 | — |

Tabla de fiabilidad:

| Tramo | n | Confianza media | Acierto real | Desvío |
|---|---|---|---|---|
| 0,7–0,8 | 20 | 0,747 | 1,000 | **+0,253** |
| 0,8–0,9 | 10 | 0,885 | 1,000 | +0,115 |
| 0,9–1,0 | 500 | 0,992 | 1,000 | +0,008 |

Se equivoca **por prudencia**: cuando dice 0,75 acierta el 100%. En el tramo alto
es casi exacto (+0,008). El sentido del error es el seguro, pero significa que
**usar los umbrales de confianza tal cual pierde precisión**: descartarías casos
que son correctos.

**Y aquí está la trampa**: un ECE bajo sobre una tarea donde todo se acierta no
distingue buena calibración de simplemente estar en lo correcto. Con 500 de 530
decisiones en el tramo alto y 100% de acierto, este número es **evidencia débil**.
Para calibrar de verdad hace falta una tarea con errores que repartir.

---

## 7. Lo que NO está validado

Lo digo explícito para que nadie lo tome por bueno:

1. **No hemos corrido ningún benchmark estándar.** Los 89% y 93,8 ms son sobre
   datasets propios, así que **no son comparables con el mercado**. Ver
   [`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md) §6.
2. **El set adversario lo escribí yo**, con mis sesgos sobre qué es difícil. Y tiene
   37 campos: los intervalos son anchos y la mayoría incluye el extremo bajo.
3. **Una máquina, un modelo, una configuración.** Nada de esto se ha replicado en
   otro hardware.
4. **Sin promediar sobre días.** Las cifras vienen de sesiones de minutos; no se ha
   medido si el rendimiento deriva.
5. **Sin comparación con un LLM de frontera en el mismo hardware** — no tenemos
   ninguno corriendo localmente.
6. **Un solo núcleo de verdad de referencia**: mis etiquetas. Un benchmark estándar
   trae etiquetas de terceros, que es la diferencia entre «acierta lo que yo creo»
   y «acierta lo que dice el estándar».

## 8. Reproducir

```bash
python exp_stats.py 10     # acierto con IC, latencia, calibracion
python exp_stress.py       # set adversario por categoria
python exp_rango.py        # el recorte silencioso y el coste del arreglo
```

## Sources

[4] https://github.com/TheoLeeCJ/SemIf — SemIf (formerly OpenJev) - typed decisions from open models
[5] https://www.logeshwaran.org/2026/10/open-source-jev-models-jev-27b-gev-26b.html — Open-Source Jev AI Models: JEV-9B, JEV-27B-VL and GEV-26B-Decide (the GGUF trap)
