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
1 pregunta(s), una sola peticion  (135 ms, 0 tokens)

CHOICE  ·  ¿A qué área hay que enviar este correo?
  soporte         1.000  ##############################  <-
  otros           0.000  ..............................
  facturacion     0.000  ..............................
  comercial       0.000  ..............................

  confianza = 1.000
```

Hay un ejemplo por tipo, para probarlos todos:

```
python preguntar.py ejemplos\1_opciones.txt        elegir de una lista
python preguntar.py ejemplos\2_niveles.txt         poner algo en una escala
python preguntar.py ejemplos\3_booleano.txt        un si o un no
python preguntar.py ejemplos\4_tres_preguntas.txt  las tres de golpe
python preguntar.py ejemplos\5_correo_soporte.txt  un correo real, con las tres
```

Todo esto está explicado paso a paso en [`MANUAL.md`](MANUAL.md).

## Paso 4 — Tus propias preguntas

No hace falta tocar código. Crea un fichero `.txt` con este formato y pásaselo:

```
input: Buenos días. Llevo desde ayer sin poder entrar a la aplicación: me sale un
error 500 cada vez que intento iniciar sesión.

ask: ¿A qué área hay que enviar este correo?
choice:
  soporte: Fallos y errores del producto
  facturacion: Cobros, facturas y reembolsos
  comercial: Ventas y planes
  otros: Todo lo demás
```

```
python preguntar.py mi_caso.txt
python preguntar.py --texto "input: ... / ask: ... / choice: ..."
python preguntar.py --json mi_caso.txt      las probabilidades completas
```

## Paso 5 — Parar el servidor

Vuelve a la ventana del servidor y pulsa **Ctrl + C**. O desde otra terminal:

```
taskkill /IM llama-server.exe /F
```

## Y ya está

Con eso tienes lo necesario: **el servidor arriba y los modos funcionando**. Escribe tus
propios casos y pásaselos a `preguntar.py`.

Los resultados del estudio —tiempos, acierto, confianza— están en
[`ESTUDIO.md`](ESTUDIO.md), [`METRICAS.md`](METRICAS.md) y [`DETALLE.md`](DETALLE.md).
**Son informativos**: describen lo que dio este montaje en esta máquina, y no hacen
falta para usar el proyecto. Los scripts que los produjeron están en la raíz del
repositorio, por si quieres auditarlos o repetirlos.

> **Si repites los benchmarks:** el terminal de esta máquina lanza cada comando **dos
> veces**, así que dos pueden correr a la vez y contaminarse los tiempos.
> `bench_cascada.py` lo evita con un candado. Si lanzas los otros dos a la vez, los
> números no valen.

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
si quieres **regenerar los gráficos del estudio** — ya están generados en `results/graf/`,
así que puedes ignorarlo por completo.

Si aun así quieres regenerarlos:

```
pip install matplotlib
python rendimiento.py
```
