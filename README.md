# AIOM — un modelo, dos formas de preguntar

**La idea, en una frase:** un modelo de decisión como Jev no es un modelo distinto de un
LLM. **Es el mismo.** Lo que cambia es **cómo le haces la pregunta** y **qué le pides de
vuelta**: prosa, o un valor de un conjunto cerrado con sus probabilidades.

Este repositorio demuestra que eso se consigue con **un modelo corriente en tu propio
equipo**, sin entrenar nada y sin cargar un segundo modelo.

Es un proyecto **exploratorio**: la gracia no está en un modelo nuevo, sino en entender
qué hace un LLM por dentro y hasta dónde llega cambiando solo el planteamiento —la
entrada y lo que se espera de la salida—. Nada que ajustar, nada que reentrenar, nada que
descargar de más.

## Cómo funciona

![Arquitectura general: las entradas, el cliente, la API, el modelo y las dos vías](docs/arquitectura.png)

La pieza que lo hace posible no es el modelo: es **el endpoint**. llama.cpp de serie solo
sabe generar texto; el backend
[`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision)
añade uno que **puntúa las opciones en lugar de redactar**. Por eso el modo de decisión
no gasta tokens: no es que escriba poco, es que **no pasa por el bucle de generación**.

**El cliente tiene dos puertas y las dos acaban en el mismo sitio.** La **API**, que habla
con el servidor, y el **cliente web**, que `api.py` sirve en el mismo proceso. Y a la API
también se la puede llamar **sin cliente ninguno**: con `curl` o Postman. El modo —decisión
o chat— no es del sistema: es **una propiedad de la petición**, y por eso se pueden pedir
los dos a la vez y compararlos.

## Empezar

Dos pasos: **levantar el servidor** y **preguntar**. El servidor es un `llama-server` con
el backend de decisión; el resto es este repositorio.

```bash
# 1. el servidor (una terminal aparte; tarda en cargar el modelo)
llama-server -m modelo.gguf -ngl 99 -fa on -c 32768 --decision-seqs 64 --port 8096

# 2. la API y el cliente web (desde la carpeta del repositorio; abre http://127.0.0.1:8100/)
python api.py
```

`--decision-seqs` **no es opcional**: sin él el endpoint de decisión no existe.

**[→ Cómo montarlo todo paso a paso, de cero, y qué hacer si falla](docs/ARRANCAR.md)**

Para preguntar hace falta **FastAPI** (`pip install fastapi "uvicorn[standard]"`), que es
lo que levanta la API y sirve el cliente web. La API trae su propia página de pruebas en
`http://127.0.0.1:8100/docs`. De dónde sale cada pieza está en
[`CREDITOS.md`](docs/CREDITOS.md).

## Las dos formas de preguntar

**Lenguaje natural**, que es la puerta de entrada:

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

La cabecera decide el tipo de pregunta:

| cabecera que escribes | tipo | devuelve |
|---|---|---|
| `choice:` | **choice** | la opción elegida + probabilidad de todas + confianza |
| `score:` | **score** | posición en la escala (puede caer entre dos niveles) |
| `noul:` | **noul** | `true` o `false`, con su probabilidad y su confianza |

**Tipada**, el mismo caso con el esquema explícito —es el formato de TypeSafe, traducido
tal cual—. Las dos dan exactamente lo mismo; el traductor está en `tipado.py`, y su tabla
de equivalencias está en su cabecera.

Los dos formatos son **vías de decisión**: traen su propio esquema y devuelven valores, sin
generar un token. Una pregunta sin tipo (ni `choice:`, ni `score:`, ni `noul:`) se trata
como un verdadero o falso —la vía de decisión necesita un conjunto finito—. Para texto libre
está el formato **`chat`**, que es la otra vía del servidor: una pregunta suelta y el modelo
escribe la respuesta.

Se pega el contenido de cada uno en el cliente web, o se manda a la API en el campo
`entrada`:

```bash
# el contenido del fichero, en el campo "entrada" (con --data-binary, que respeta el UTF-8)
python -c "import json;print(json.dumps({'formato':'natural','entrada':open('ejemplos/5_correo_soporte.txt',encoding='utf-8').read()}))" > p.json
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" --data-binary @p.json
```

Hay un ejemplo por tipo: `1_opciones.txt` (elegir de una lista), `2_niveles.txt` (poner
algo en una escala), `3_booleano.txt` (verdadero o falso), `4_tres_preguntas.txt` (las tres
de golpe) y `5_correo_soporte.txt` (un correo real).

Los cinco están explicados paso a paso, con su salida real, en
[`docs/MANUAL.md`](docs/MANUAL.md).

## La comparación: decisión contra chat

**Esto es lo único que merece la pena medir aquí**, y se mide en vivo, con tus propias
preguntas: qué responde cada vía y cuánto tarda cada una.

```bash
# por la API, con las dos vías en la misma corrida
curl -s http://127.0.0.1:8100/ask -H "Content-Type: application/json" -d '{
  "formato": "natural",
  "entrada": "input: Llevo desde ayer sin poder entrar: me sale un error 500.\n\nask: ¿A qué área hay que enviar este correo?\nchoice:\n  soporte: Fallos y errores del producto\n  facturacion: Cobros, facturas y reembolsos\n  otros: Todo lo demás",
  "comparar": true
}'
```

O en la interfaz web, con «Comparar» activado: pregunta lo mismo por las dos vías y las
pone **lado a lado** — los valores de la decisión uno por pregunta, y la respuesta del
chat entera, porque el chat contesta de una vez.

La diferencia no es de acierto, es de **trabajo**: la vía de decisión **puntúa** las
opciones y devuelve un valor; la de chat **escribe** prosa que hay que interpretar. Con
una pregunta el ahorro es pequeño; con varias encadenadas se abre, porque el motor puntúa
todas **en la misma pasada** y añadir una casi no cuesta. Ese es el hallazgo práctico.

## Dos cosas que conviene saber antes de escribir tus preguntas

**El fallo puede ser de la pregunta, no del modelo.** Si añades `'etiqueta' = descripción`
a cada opción, **diluyes la pregunta**: el modelo reparte su atención entre el enunciado y
las etiquetas. Hay casos que fallan *con* la descripción y acierta *sin* ella. Si un caso
se resiste, prueba a quitarle texto, no a añadírselo.

**Y no le pongas ejemplos.** Suena a que debería ayudar —consultas de ejemplo que le
enseñen el criterio— y está medido que no: con ejemplos largos el resultado **empeora**, y
con ejemplos cortos queda igual que sin ellos. Es lo mismo que arriba: el texto de más
diluye la pregunta.

**Un rango ancho es una trampa.** Un campo numérico con muchos valores posibles obliga al
modelo a puntuar muchos nodos y la probabilidad se reparte: la confianza se cae y el
valor sale mal. Acótalo al rango real.

## Lo que este repositorio NO es

- **No compara con Jev ni con ningún modelo del mercado.** Aquí solo se compara este
  modelo consigo mismo, por las dos vías.
- **No reivindica el motor.** El endpoint es de terceros; lo propio es el cliente, el
  traductor de lenguaje natural, la técnica de los dos modos sobre un solo modelo y la
  comparación en vivo. Está desglosado, con autoría y licencia de cada pieza, en
  [`CREDITOS.md`](docs/CREDITOS.md).
- **No es un modelo entrenado.** No hay ajuste fino en ninguna parte.

## Desde el navegador, y desde un programa

Con el servidor arriba, `api.py` levanta la API y **sirve también la interfaz** — así no
hay un segundo servidor ni un paso de compilación:

```bash
python api.py          # y abre http://127.0.0.1:8100/
```

La interfaz deja escribir el caso y las preguntas **una sola vez**, de tres formas
distintas —**por bloques**, en **lenguaje natural** o en **JSON**— que son tres
vistas de lo mismo: se cambia de pestaña y lo escrito aparece en la otra forma.

**Y el caso no hace falta escribirlo**: se carga un documento (pdf, docx, txt, md, csv) y
las preguntas van sobre él. Un `.docx` se lee sin instalar nada; un `.pdf` pide
`pip install pymupdf`. El cliente web lo sube y enseña el texto extraído; con la API son
**dos llamadas** —`POST /documento` y luego `POST /ask`—, y están completas en
[`docs/EJEMPLOS.md`](docs/EJEMPLOS.md).

`formato` es `natural`, `tipado` o `chat` —se declara, no se adivina—. Los dos primeros son
vías de decisión (valores, 0 tokens); el tercero es prosa. Detalles en
[docs/API.md](docs/API.md).

**Y si lo vas a llamar desde otro programa**, hay un ejemplo completo y ejecutable en
[`ejemplos/integrar.py`](ejemplos/integrar.py): las tres formas de darle el caso, los dos
endpoints, seis preguntas de los tres tipos, y cada campo de la respuesta explicado.

```bash
python ejemplos/integrar.py                # el caso, escrito
python ejemplos/integrar.py carta.pdf      # el caso, sacado de un documento
python ejemplos/integrar.py --tipado       # el mismo caso, en JSON tipado
python ejemplos/integrar.py --comparar     # y además, lo mismo al chat
```

Y **[`docs/EJEMPLOS.md`](docs/EJEMPLOS.md)** tiene todos los ejemplos de consulta, completos
y para copiar y pegar: los tres formatos, los tres tipos de pregunta, con documento, la
comparación y desde el navegador.

## Documentación

| documento | qué hay |
|---|---|
| **[docs/ARRANCAR.md](docs/ARRANCAR.md)** | **la ruta completa, de cero**: el modelo, compilar el servidor, arrancarlo, y las dos puertas para preguntar. Con qué hacer si algo no arranca |
| [docs/MANUAL.md](docs/MANUAL.md) | el manual de uso, con un ejemplo de cada tipo (opciones, niveles, verdadero/falso), cómo se hacen varias preguntas a la vez y cómo se escribe en formato tipado |
| [docs/CLIENTE.md](docs/CLIENTE.md) | la interfaz web: cómo se despliega, los tres modos, el documento como caso, la comparación de las dos vías y cómo se lee una respuesta |
| **[docs/EJEMPLOS.md](docs/EJEMPLOS.md)** | **todos los ejemplos de consulta, completos y para copiar**: los tres formatos, los tres tipos de pregunta, con documento, la comparación y desde el navegador. Sin un solo `...` |
| [docs/API.md](docs/API.md) | la API HTTP: cómo se despliega y cómo se consume, los tres formatos de entrada, el documento como caso, qué devuelve y cómo probarla con `curl` |
| [docs/PRODUCT.md](docs/PRODUCT.md) | la verdad del producto: quién lo usa, qué hace, qué no se puede inventar |
| [docs/DESIGN.md](docs/DESIGN.md) | el sistema visual de la interfaz, con sus tokens, sus reglas y sus prohibiciones. Los nombres de los tokens son los mismos que los de las variables CSS, así que se puede comprobar contra el código |
| [CREDITOS.md](docs/CREDITOS.md) | **de quién es cada pieza**, con commit exacto, licencias y el SHA256 del modelo |

## Estructura

Esto es todo el proyecto. No hay nada más:

```
preguntar.py         el analizador del formato natural: lee las cabeceras (input:, ask:,
                     choice:, score:, noul:) y deduce el tipo de cada pregunta; una o
                     varias en una petición. Lo usa la API, no se ejecuta por consola
aiom.py              el núcleo: hablar con llama-server, el vocabulario del proyecto y la
                     vía de chat. El esquema no vive aquí: lo trae cada petición
tipado.py            el traductor del formato tipado (el de TypeSafe, tal cual)
documento.py         saca el texto de un documento para usarlo como caso
api.py               la API HTTP (FastAPI), que además sirve la interfaz web
web/index.html       la interfaz: un solo fichero, HTML+CSS+JS sin dependencias
ejemplos/            siete casos de ejemplo -cinco sobre correos de soporte, uno por tipo
                     de pregunta y uno con las tres de golpe, y dos con SOLO las
                     preguntas, para usarlos con un documento- y el ejemplo de integracion:
                       integrar.py       como consultar la API desde Python, con el caso
                                         escrito o sacado de un documento
                       demo/             la demo en vivo, con dos casos completos:
                         pqr.pdf         una PQR de dos páginas (y pqr.txt, su texto)
                         servidor.log    un log de errores de un servidor, 336 líneas
                         preguntas_pqr.txt  las 30 preguntas sobre la PQR
                         preguntas_log.txt  las 30 preguntas sobre el log
                         LEEME.md        qué es cada fichero y cómo se usa
                         _gen_pqr.py     los generadores, por si hay que rehacerlos
                         _gen_log.py
docs/                toda la documentación, junta:
                       API.md            la API: los tres formatos, el documento como caso
                       EJEMPLOS.md       todos los ejemplos de consulta, completos y para copiar
                       ARRANCAR.md       la ruta completa desde cero, y qué hacer si falla
                       CLIENTE.md        la interfaz web
                       MANUAL.md         el manual de uso, con un ejemplo de cada tipo
                       PRODUCT.md        la verdad del producto: qué hace y qué no
                       DESIGN.md         el sistema visual de la interfaz
                       CREDITOS.md       de quién es cada pieza, con commit y SHA256
                       arquitectura.svg  el diagrama de arquitectura de arriba
                       arquitectura.png  el mismo, en mapa de bits
requirements.txt     las dependencias, y para qué es cada una
LICENSE              MIT
.gitignore           lo que no se publica: cachés, entornos, estado de herramientas
README.md            este fichero
```

## Requisitos

- Python 3.10+ — el analizador del formato natural, el tipado y el motor **no tienen
  dependencias**: solo la biblioteca estándar. (Los usa la API.)
- Para la **API**: `pip install fastapi "uvicorn[standard]"`.
- Un `llama-server` con el endpoint `/v1/decision`, del backend
  [`parallel-decision`](https://github.com/thecodacus/llama.cpp/tree/parallel-decision).
- Para leer **PDF** como caso, `pip install pymupdf` (un `.docx` o un `.txt` no piden nada).
- Para leer un **PDF escaneado**, `pip install rapidocr-onnxruntime` (~100 MB). Es
  opcional: sin él las páginas escaneadas no se leen y se dice.
- Para **levantar el servidor** hay que compilar el fork de llama.cpp (Vulkan), con las
  instrucciones de [`docs/ARRANCAR.md`](docs/ARRANCAR.md).
