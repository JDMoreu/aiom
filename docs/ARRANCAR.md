# Arrancarlo tú mismo

Todo lo de este repositorio se ejecuta **en tu equipo**, sin nube. Aquí están los pasos
para levantar el modelo y hacer las pruebas tú.

## Antes de nada: el servidor tiene que estar arriba

Los scripts de este repositorio **no cargan el modelo**: se conectan a un servidor que
ya está corriendo. Si no está, verás errores de conexión (`WinError 10061`, «no se puede
establecer una conexión») — no es un fallo del código, es que falta encenderlo.

## Paso 1 — Arrancar el servidor

Abre una terminal (PowerShell o CMD) y pega esto **en una sola línea**:

```
cd C:\Users\JDMoreu\Documents\llm-local\llama-decision\build-vulkan\bin
llama-server.exe -m C:\Users\JDMoreu\Documents\llm-local\Spark-X2.5-4B\Spark-X2.5-4B-Q8_0.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096
```

Qué hace cada opción, por si quieres cambiarla:

| opción | para qué |
|---|---|
| `-m <ruta>` | el modelo. Es el fichero de 4,1 GB. |
| `-ngl 99` | manda todas las capas a la tarjeta gráfica. Si lo bajas, va a CPU y tarda mucho más. |
| `-fa on` | atención rápida. |
| `-c 32768` | el contexto. Si te da error de memoria, bájalo. |
| `--decision-seqs 64` | **imprescindible**: reserva las ramas que necesita el endpoint de decisión. Sin esto, `/v1/decision` no funciona. |
| `--port 8096` | el puerto. Los scripts apuntan ahí; si lo cambias, exporta `AIOM_SERVER`. |

**Tarda un rato** en cargar: el modelo son 4,1 GB. Sabrás que está listo cuando
aparezca esta línea:

```
srv  llama_server: listening on http://127.0.0.1:8096
```

**No cierres esa ventana.** El servidor vive mientras esa ventana esté abierta.

> Si te da error y no arranca, suele ser porque falta alguno de los cuatro `.dll` que
> van al lado del `.exe` (`libgcc_s_seh-1`, `libgomp-1`, `libstdc++-6`,
> `libwinpthread-1`). Están en esa misma carpeta; si falta uno, el programa se cierra
> sin decir nada.

## Paso 2 — Comprobar que responde

En **otra** terminal:

```
curl http://127.0.0.1:8096/health
```

Tiene que contestar `{"status":"ok"}`. Si dice `"Loading model"`, espera un poco más.

## Paso 3 — Preguntar

```
cd C:\Users\JDMoreu\Documents\aiom
python preguntar.py ejemplos\1_opciones.txt
```

Y verás:

```
1 pregunta(s), una sola peticion  (122 ms, 0 tokens)

CHOICE  ·  ¿Qué equipo debe atenderlo? 'billing' = Pagos y reembolsos
  billing         1.000  ##############################  <-
  technical       0.000  ..............................
  general         0.000  ..............................

  confianza = 1.000
```

Hay un ejemplo por tipo, para probarlos todos:

```
python preguntar.py ejemplos\1_opciones.txt        elegir de una lista
python preguntar.py ejemplos\2_niveles.txt         poner algo en una escala
python preguntar.py ejemplos\3_si_o_no.txt         preguntar si o no
python preguntar.py ejemplos\4_tres_preguntas.txt  las tres de golpe
```

Todo esto está explicado paso a paso en [`MANUAL.md`](MANUAL.md).

## Paso 4 — Tus propias preguntas

No hace falta tocar código. Crea un fichero `.txt` con este formato y pásaselo:

```
Entrada: Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

Pregunta: ¿Qué equipo debe atenderlo?
Opciones:
  billing: Pagos y reembolsos
  technical: Errores e integraciones
  general: Otras consultas
```

```
python preguntar.py mi_caso.txt
python preguntar.py --texto "Entrada: ... / Pregunta: ... / Opciones: ..."
python preguntar.py --json mi_caso.txt      las probabilidades completas
```

## Paso 5 — Repetir las pruebas del estudio

Cada una tarda unos minutos y **escribe en `results/`**:

```
python bench_modos.py       los 3 modos sobre 90 casos
python bench_multi.py       preguntas encadenadas
python bench_cascada.py     el escalado de 1 a 15 preguntas (con candado anti-duplicados)
python verificar.py         comprueba que las cifras de los documentos sigan cuadrando
```

Si vuelves a medir y alguna cifra de los documentos deja de coincidir con `results/`,
`verificar.py` te lo dice.

> **Un aviso de esta máquina:** el terminal lanza cada comando **dos veces**, así que
> dos benchmarks pueden correr a la vez y contaminarse los tiempos entre ellos.
> `bench_cascada.py` lo evita con un candado. Si lanzas los otros dos a la vez,
> los números no valen.

## Paso 6 — Parar el servidor

Vuelve a la ventana del servidor y pulsa **Ctrl + C**. O desde otra terminal:

```
taskkill /IM llama-server.exe /F
```

## El Python

Aquí hay un problema que conviene resolver: **no tienes un Python propio instalado en
el sistema.** El `python` que hay en el PATH pertenece a Hermes, y el `python3`
es el atajo vacío de la Microsoft Store.

Para que esto te funcione de forma independiente, instálalo tú:

```
winget install Python.Python.3.13
```

Y comprueba con `python --version` en una terminal **nueva**.

**El cliente no necesita instalar nada más**: todos los scripts usan solo la biblioteca
estándar de Python. Lo único que pide dependencias es `graficos.py` (matplotlib), y solo
si quieres **regenerar los gráficos** — ya están generados en `results/graf/`.

Si quieres regenerarlos:

```
pip install matplotlib
python rendimiento.py
```
