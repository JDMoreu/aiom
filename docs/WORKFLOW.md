# Workflow — cómo se construyó y cómo se midió

Registro del proceso real: qué se intentó, qué falló, qué se midió y qué se
concluyó. Está aquí porque los errores valen tanto como los aciertos, y porque
cualquiera que reproduzca esto se va a topar con los mismos obstáculos.

---

## 1. Entorno

Windows 11, **Radeon RX 9070** (16 GB, `vulkan-1.dll` del driver AMD presente en
`System32`). Objetivo: compilar el backend `parallel-decision` de llama.cpp con
aceleración Vulkan.

Toolchain instalado vía winget:

| pieza | versión | por qué |
|---|---|---|
| CMake | 4.4.4 | build system |
| GCC (MinGW-w64 UCRT) | 16.2.0 | compilador |
| Ninja | — | generador |
| Python | 3.10+ | cliente AIOM, sin dependencias |

**Decisión:** Visual Studio Build Tools se descartó porque su instalador no se puede
automatizar sin consola interactiva. MinGW-w64 no tiene ese problema y produce
binarios autocontenidos.

---

## 2. Compilación

```bash
git clone -b parallel-decision https://github.com/thecodacus/llama.cpp llama-decision
cd llama-decision
cmake -B build-vulkan -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
      -DCMAKE_C_FLAGS="-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00" \
      -DCMAKE_CXX_FLAGS="-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00"
cmake --build build-vulkan -j
```

### Obstáculo 1 — `::CreateFile2` no declarado

```
vendor/cpp-httplib/httplib.cpp:1582: error: '::CreateFile2' has not been declared
```

`CreateFile2` es API de Windows 8, guardada tras `#if _WIN32_WINNT >= 0x0602`.
MinGW no define `_WIN32_WINNT` por defecto, así que la declaración queda oculta.

**Arreglo:** `-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00` (Windows 10).

### Obstáculo 2 — el instalador del Vulkan SDK exige administrador

```
installationError: Cannot elevate access rights while running from command line.
```

El instalador aborta y **revierte** todo. Pero el log revela algo útil: ya había
extraído `Include.7z`, `Bin.7z` (con `glslc`), `Lib.7z` y el resto correctamente —
la elevación solo hacía falta para ejecutar el redistribuible de VC++.

**Arreglo:** extraer los payloads del propio instalador, sin ejecutarlo. Un
instalador Qt IFW guarda cada componente como un archivo **7z concatenado** dentro
del `.exe`, y la cabecera 7z (32 bytes) declara el tamaño total exacto del archivo:

```
firma (6) + versión (2) + CRC cabecera (4)
        + offset cabecera siguiente (8) + tamaño (8) + CRC (4)
```

Escaneando el binario por la firma `37 7A BC AF 27 1C` y leyendo esos dos campos,
se recuperan los archivos con su longitud exacta. Salieron 8 payloads válidos
(256 MB); de ahí `Include/vulkan/`, `Bin/glslc.exe` y `Lib/vulkan-1.lib` a
`C:\Users\JDMoreu\VulkanSDK`.

Verificación: `glslc --version` → shaderc v2026.4, glslang 11.1.0.

CMake lo encontró y lo confirmó:

```
Found Vulkan: .../Lib/vulkan-1.lib (found version "1.4.363")
  found components: glslc glslangValidator
-- Including Vulkan backend
```

### Obstáculo 3 — el binario no arrancaba (`exit 127`)

Los ejecutables de MinGW enlazan dinámicamente contra su runtime
(`libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libgomp-1.dll`, `libwinpthread-1.dll`),
que no está en `System32`. Sin él, el cargador de Windows falla y bash reporta
`127` con la salida vacía — un síntoma que no dice nada del problema real.

**Arreglo:** copiar esas cuatro DLLs junto a los ejecutables. Además deja el build
distribuible sin depender del `PATH`.

Diagnóstico que llevó hasta ahí:

```bash
objdump -p build-vulkan/bin/llama-server.exe | grep -i "DLL Name" | sort -u
```

### Resultado

585 pasos, `EXITCODE=0`. Un riesgo que no se materializó: `vulkan-1.lib` es formato
MSVC y el enlazador de MinGW **lo aceptó** sin necesidad de generar un `libvulkan-1.a`
con `dlltool`.

`llama-server --list-devices` confirmó:

```
Vulkan0: AMD Radeon RX 9070 (16304 MiB, 15416 MiB free)
```

---

## 3. Arranque del servidor

```bash
llama-server -m Spark-X2.5-4B-Q8_0.gguf -ngl 99 -fa on -c 32768 \
             --decision-seqs 16 --host 127.0.0.1 --port 8096
```

El log confirma que el modo decisión queda activo:

```
init: initializing, n_slots = 4, n_ctx_slot = 32768, kv_unified = 'true'
```

`kv_unified = 'true'` es la clave: la caché KV unificada permite que las ramas de
una decisión compartan las celdas del prefijo común.

---

## 4. Registro de mediciones

Cada entrada: hipótesis, medición, conclusión. Los números están en
[`../docs/RESULTADOS.md`](RESULTADOS.md) y el crudo en [`../results/`](../results/).

### 4.1 ¿Funciona el modo decisión?

**Hipótesis:** el endpoint puntúa opciones sin generar tokens.
**Medición:** 6 decisiones en una pasada, 95.3 ms, `tokens_generados = 0`. Las 6
clasificaciones correctas, incluidos los números de predio.
**Conclusión:** sí. Los campos nativos del servidor lo confirman:
`prefill_ms`, `scoring_ms`, `rounds`, `scored_rows`, `per_decision_ms`.

### 4.2 ¿Cuánto más rápido que el chat?

**Hipótesis:** el chat genera tokens y por tanto es más lento.
**Medición (primera, inválida):** 27x. El lado del chat devolvía contenido vacío.
**Diagnóstico:** el servidor avisa al arrancar —
*"chat template supports preserving reasoning, it is enabled by default (may use
more tokens, disable via --no-reasoning-preserve)"*. El modelo gastaba los 256
tokens de presupuesto razonando y nunca escribía el JSON.
**Arreglo:** `chat_template_kwargs: {"enable_thinking": false}` y `max_tokens=1024`,
más extracción del primer objeto JSON del texto.
**Medición corregida:** 4.9x (93.8 vs 470.1 ms), 100% vs 92.5% de acierto.
**Conclusión:** el 27x era un artefacto del baseline roto. El número honesto es 4.9x.
Un baseline mal montado no mide al modelo, mide el arnés.

### 4.3 ¿Cómo se define bien un campo entero?

**Hipótesis:** `predio` como entero 1–99 obliga a puntuar demasiadas ramas.
**Medición:**

| definición | aciertos | confianza media | nodos puntuados |
|---|---|---|---|
| entero 1..99 | 3/5 | 0.570 | 10.0 |
| entero 1..12 | 5/5 | 1.000 | 2.0 |
| enum de 12 valores | 5/5 | 1.000 | 2.0 |

Los fallos eran redondeos a la decena: `predio 3` → 33, `predio 2` → 20.
**Conclusión:** acotar el rango o enumerar los valores reales. Entero 1–12 y enum
empatan; el entero es más simple de escribir.

### 4.4 ¿Dónde se va el tiempo?

**Hipótesis:** el prefijo cacheado hace que una decisión cueste casi nada.
**Medición:** `prefill 111.7 ms + scoring 118.2 ms = 229.9 ms` para 6 contextos,
`rounds: 3`, `per_decision: 38.3 ms`. Prefijo cacheado: 355 tokens.
**Conclusión:** el coste está partido ~50/50 y el **prefill es el suelo**: meter la
pregunta en el modelo no se puede esquivar. El `scoring` sí depende del catálogo.

### 4.5 El benchmark completo

**Hipótesis:** el modo decisión escala mejor que el chat al paralelizar.
**Medición:** 26 consultas etiquetadas × 2 modos × 5 niveles de concurrencia.
Resultado completo en [`RESULTADOS.md`](RESULTADOS.md).

```
decision  conc=1    93.8 ms p50   10.57 q/s   0 tok     53/53
decision  conc=4   294.2 ms p50   13.48 q/s   0 tok     53/53
decision  conc=16  994.6 ms p50   13.12 q/s   0 tok     53/53

chat      conc=1   470.1 ms p50    2.16 q/s   33.2 tok/q  49/53
chat      conc=16 4843.5 ms p50    2.95 q/s   33.7 tok/q  49/53
```

**Conclusión:** `decision` gana en latencia, caudal, tokens **y acierto**. Pero los
dos modos **se saturan**: más concurrencia no da caudal, solo multiplica la latencia.
El servidor es el cuello de botella, no el cliente.

### 4.6 ¿Se puede hacer más rápido?

**Hipótesis:** si el servidor se satura con peticiones sueltas, agrupar consultas en
una sola petición aprovecha el batching del endpoint.

| forma | pared | por consulta |
|---|---|---|
| 16 peticiones HTTP en paralelo | 1566 ms | 60.2 ms |
| 1 petición con las 26 consultas | **1249 ms** | **48.0 ms** |

Monótono con el tamaño del lote: 1→74.5 ms, 4→52.9, 8→51.8, 16→49.1, 26→48.0.

**Error cometido en este experimento:** la primera versión emparejaba cada respuesta
con la lista completa de consultas en lugar de con su subconjunto, y reportaba
"aciertos" de 20/53 en tandas que iban perfectas. Corregido, 53/53 en todas las
formas. Lección: si un número sale raro, sospecha del arnés antes que del modelo.

**Conclusión:** agrupar da 1.25x y escala monótonamente; el paralelismo HTTP no.
Además simplifica el cliente: no hace falta pool de hilos.

---

## 5. Índice de evidencia

| artefacto | qué prueba |
|---|---|
| `results/bench.json` | crudo completo del benchmark, con las respuestas de cada consulta |
| `results/bench.csv` | mismas métricas en plano, para graficar |
| `results/bench.html` | caudal, latencia p50/p95 y tokens frente a concurrencia |
| `docs/RESULTADOS.md` | tablas del informe, generadas desde `bench.json` |
| `dataset.py` | las 26 consultas con su verdad de referencia |
| `exp_batch.py` | paralelismo HTTP contra agrupación |

Todo lo que aparece en `results/` y `docs/RESULTADOS.md` es generado. Ningún número
del README está escrito a mano.

---

## 6. Reproducir

```bash
# 1. servidor con el endpoint de decisión
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 16 --port 8096

# 2. el benchmark
python bench.py --concurrency 1,2,4,8,16

# 3. el informe y las gráficas
python report.py
```

Para repetir el experimento de agrupación: `python exp_batch.py`.
