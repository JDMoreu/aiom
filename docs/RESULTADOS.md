# Resultados del benchmark

Generado por `report.py` a partir de `results/bench.json`. Todo numero de este documento sale de una ejecucion real; reproducelo con `python bench.py`.

## Configuracion

- Servidor: `http://127.0.0.1:8096`
- Modelo: `preset del servidor`
- Estado: `n/d`
- Dataset: 26 consultas etiquetadas (20 respondibles, 6 no respondibles)

## Caudal

**Consultas por segundo**

| consultas en paralelo | modo decision (pregunta, 0 tokens) | modo chat (escribe texto) |
|---|---|---|
| 1 | 10.57 q/s | 2.16 q/s |
| 2 | 12.82 q/s | 2.51 q/s |
| 4 | 13.48 q/s | 2.40 q/s |
| 8 | 12.80 q/s | 2.89 q/s |
| 16 | 13.12 q/s | 2.95 q/s |

## Latencia p50

**Mediana de latencia**

| consultas en paralelo | modo decision (pregunta, 0 tokens) | modo chat (escribe texto) |
|---|---|---|
| 1 | 93.8 ms | 470.1 ms |
| 2 | 152.1 ms | 833.2 ms |
| 4 | 294.2 ms | 1522.0 ms |
| 8 | 622.8 ms | 2342.8 ms |
| 16 | 994.6 ms | 4843.5 ms |

## Latencia p95

**Cola p95**

| consultas en paralelo | modo decision (pregunta, 0 tokens) | modo chat (escribe texto) |
|---|---|---|
| 1 | 112.7 ms | 510.9 ms |
| 2 | 174.6 ms | 880.6 ms |
| 4 | 309.1 ms | 2606.0 ms |
| 8 | 639.3 ms | 3667.5 ms |
| 16 | 1213.4 ms | 6169.5 ms |

## Tokens

**Tokens generados por consulta**

| consultas en paralelo | modo decision (pregunta, 0 tokens) | modo chat (escribe texto) |
|---|---|---|
| 1 | 0.0 tok | 33.2 tok |
| 2 | 0.0 tok | 34.4 tok |
| 4 | 0.0 tok | 33.7 tok |
| 8 | 0.0 tok | 33.7 tok |
| 16 | 0.0 tok | 33.7 tok |

## Acierto

| consultas en paralelo | modo decision (pregunta, 0 tokens) | modo chat (escribe texto) |
|---|---|---|
| 1 | 53/53 | 49/53 |
| 2 | 53/53 | 49/53 |
| 4 | 53/53 | 49/53 |
| 8 | 53/53 | 49/53 |
| 16 | 53/53 | 49/53 |
