# Arrancarlo tú mismo, de cero

Todo se ejecuta **en tu equipo**, sin nube. Esta es la ruta completa: el modelo, el
servidor, el cliente de consola, la API y la interfaz web.

Lo que hace falta, y para qué:

| | para qué |
|---|---|
| **Python 3.10+** | el cliente. **Sin dependencias**: solo la biblioteca estándar. |
| **Una GPU con Vulkan** | el servidor. Sin GPU funciona, pero en CPU tarda mucho más. |
| **El fork de llama.cpp** | el endpoint `/v1/decision`. **Es el requisito duro**: sin él no hay modo decisión. |
| **El modelo** | 4,1 GB en disco, ~9 GB en VRAM con `-ngl 99`. |

## Paso 1 — El modelo

El que se usó aquí es **Spark-X2.5-4B, cuantización Q8_0**:

- Página del modelo: <https://huggingface.co/XHToken/Spark-X2.5-4B>
- El GGUF que se descargó: `end000/Spark-X2.5-4B-Q8_0-GGUF`

El fichero tiene que dar exactamente esto:

```
fichero : Spark-X2.5-4B-Q8_0.gguf
tamano  : 4375021152 bytes  (4,07 GiB)
sha256  : 5c2c3c190e4337e1016b8593ca8e26e8b18c972200b107385d4ec61a25d9dea2
```

> **Por qué el SHA256 y no solo el nombre:** de este modelo existen **al menos cinco
> conversiones distintas** a GGUF, hechas por gente distinta. Se llaman igual y no son lo
> mismo. El hash es lo único que identifica la que se midió aquí. El resto de
> procedencias, en [`../CREDITOS.md`](../CREDITOS.md).

Colócalo donde quieras y apunta la ruta: la vas a necesitar en el paso 3.

## Paso 2 — Compilar el servidor

El endpoint de decisión **no está en llama.cpp de serie**: lo añade el backend
[`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision).
Hay que compilar ese fork. Se hace **una sola vez**.

### Las herramientas

```bash
winget install Kitware.CMake Ninja-build.Ninja BrechtSanders.WinLibs.POSIX.UCRT
```

Eso deja CMake, Ninja y un **GCC de MinGW-w64 con UCRT**. Después hace falta el **SDK de
Vulkan** (<https://vulkan.lunarg.com/sdk/home>): el runtime del driver no basta, porque
compilar los shaders necesita `glslc`.

### El fork

```bash
git clone https://github.com/thecodacus/llama.cpp llama-decision
cd llama-decision
git checkout parallel-decision
```

### Configurar y compilar

```bash
cmake -B build-vulkan -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON \
      -D_WIN32_WINNT=0x0A00
cmake --build build-vulkan -j
```

Dos cosas de esas líneas que **no** son opcionales en Windows:

- **`-D_WIN32_WINNT=0x0A00`** — llama.cpp no define por su cuenta la versión de Windows,
  y con MinGW se queda en una API vieja y falla al compilar. Esto lo arregla.
- **Que CMake encuentre el SDK de Vulkan** — por la variable de entorno `VULKAN_SDK`
  apuntando a la carpeta del SDK, o pasándole `-DVULKAN_SDK=<ruta>`.

### Las cuatro DLL, junto al `.exe`

Un binario hecho con MinGW **no arranca solo**. Hay que copiar estas cuatro junto a
`llama-server.exe`:

```
libgcc_s_seh-1.dll   libstdc++-6.dll   libgomp-1.dll   libwinpthread-1.dll
```

Están en la carpeta `bin` del compilador. Si falta una, el programa **se cierra sin decir
nada**: no hay error, no hay salida. Es el fallo más confuso de todo el montaje, y por eso
está aquí escrito.

## Paso 3 — Arrancar el servidor

```bash
cd <ruta>\llama-decision\build-vulkan\bin
llama-server.exe -m <ruta>\Spark-X2.5-4B-Q8_0.gguf ^
  -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
```

| opción | para qué |
|---|---|
| `-m <ruta>` | el modelo, el fichero de 4,1 GB del paso 1. |
| `-ngl 99` | manda todas las capas a la tarjeta gráfica. Si lo bajas, va a CPU y tarda mucho más. |
| `-fa on` | atención rápida. |
| `-c 32768` | el contexto. Si te da error de memoria, bájalo. |
| `--decision-seqs 64` | **imprescindible**: reserva las ramas que necesita el endpoint de decisión. Sin esto, `/v1/decision` no funciona. |
| `--port 8096` | el puerto. Los scripts apuntan ahí; si lo cambias, exporta `AIOM_SERVER`. |

**Tarda un rato** en cargar. Sabrás que está listo cuando aparezca:

```
srv  llama_server: listening on http://127.0.0.1:8096
```

**No cierres esa ventana.** El servidor vive mientras esa ventana esté abierta.

## Paso 4 — Comprobar que responde

En **otra** terminal:

```bash
curl http://127.0.0.1:8096/health
```

Tiene que contestar `{"status":"ok"}`. Si dice `"Loading model"`, espera un poco más.

## Paso 5 — Preguntar: las dos puertas

Con el servidor arriba hay **dos formas de entrar**, y las dos acaban en el mismo sitio.
Ninguna carga el modelo: se conectan al servidor del paso 3.

### La puerta humana: por consola

```bash
cd <ruta>\aiom
python preguntar.py ejemplos\5_correo_soporte.txt
```

```
1 pregunta(s), una sola peticion  (135 ms, 0 tokens)

CHOICE  ·  ¿A qué área hay que enviar este correo?
  facturacion     0.665  ##############################  <-
  soporte         0.295  ############.........
  comercial       0.040  ##...................
  otros           0.000  .....................
```

Hay un ejemplo por tipo, para probarlos todos:

```bash
python preguntar.py ejemplos\1_opciones.txt        elegir de una lista
python preguntar.py ejemplos\2_niveles.txt         poner algo en una escala
python preguntar.py ejemplos\3_booleano.txt        un sí o un no
python preguntar.py ejemplos\4_tres_preguntas.txt  las tres de golpe
python preguntar.py ejemplos\5_correo_soporte.txt  un correo real, con las tres
```

Y no hace falta tocar código para escribir los tuyos: mira [`MANUAL.md`](MANUAL.md).

### La puerta de programa: la API y la interfaz web

```bash
python api.py --ui        # abre http://127.0.0.1:8100/
```

`api.py` levanta la API **y sirve la interfaz web en el mismo proceso**, así que no hay un
segundo servidor ni un paso de compilación. Desde ahí:

- **La interfaz**, en el navegador, con los tres modos (bloques, lenguaje natural, JSON
  tipado) y la comparación de las dos vías. Está explicada en [`CLIENTE.md`](CLIENTE.md).
- **La API**, para cualquier programa que hable HTTP. Está en [`API.md`](API.md).

Lo mismo desde la línea de comandos, sin navegador:

```bash
curl -X POST localhost:8100/ask -H "Content-Type: application/json" ^
  -d "{\"formato\":\"natural\",\"entrada\":\"input: ... / ask: ... / choice: ...\"}"
```

**Los dos modos —decisión y chat— se piden en la misma petición** con `"comparar":true`, y
vuelven juntos para que los tiempos sean de la misma corrida.

## Paso 6 — Parar

Vuelve a la ventana del servidor y pulsa **Ctrl + C**. O desde otra terminal:

```bash
taskkill /IM llama-server.exe /F
taskkill /IM python.exe /F
```

## Si cambias el código, reinicia

`api.py` carga `preguntar.py`, `aiom.py` y `documento.py` **una vez, al arrancar**. Si
editas esos ficheros, el proceso que sigue vivo trabaja con los viejos y da errores que no
corresponden con lo que hay en el disco — por ejemplo, un mensaje que ya no existe. Se nota
rápido: el texto del error no coincide con el del fichero.

Lo mismo vale para `llama-server`: si cambias el modelo o los argumentos, hay que pararlo y
arrancarlo otra vez.

> `web/index.html` es la excepción: la API lo lee **del disco en cada petición**, así que
> basta con recargar el navegador.

## El Python

Aquí hay un problema que conviene resolver: **no tienes un Python propio instalado en el
sistema.** El `python` que hay en el PATH pertenece a Hermes, y el `python3` es el atajo
vacío de la Microsoft Store.

Para que esto te funcione de forma independiente, instálalo tú:

```bash
winget install Python.Python.3.13
```

Y comprueba con `python --version` en una terminal **nueva**.

**El cliente no necesita instalar nada más**: todos los scripts usan solo la biblioteca
estándar. Lo único opcional es `pymupdf`, y solo si vas a usar un **PDF** como caso:

```bash
pip install pymupdf
```

Un `.docx`, un `.txt` o un `.md` se leen sin instalar nada.

---

## Y ya está

Con eso tienes el montaje entero: **el servidor arriba, el cliente de consola, la API y la
interfaz**. Lo único que queda por medir es la comparación de las dos vías, y esa se mide
en vivo con tus propias preguntas —desde la interfaz, o con `comparar:true` en la API—.
