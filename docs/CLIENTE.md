# El cliente web

La interfaz de AIOM. Es **un solo fichero**, `web/index.html`: HTML, CSS y JavaScript sin
dependencias, sin CDN, sin fuentes de fuera y **sin paso de compilación**. Eso no es una
limitación, es el requisito: el repositorio es Python puro y se abre con un comando.

## Cómo se despliega

**Lo normal: que la sirva la propia API.**

```bash
python api.py --ui        # y abre http://127.0.0.1:8100/
```

`api.py` atiende la API y sirve `web/index.html` **en el mismo proceso y en el mismo
puerto**, así que no hay un segundo servidor que arrancar ni CORS que configurar. Es la
forma recomendada y la que se usa en todo el proyecto.

**Y si lo quieres en otro sitio:** como es un fichero suelto, también vale servirlo desde
donde quieras (un `python -m http.server`, tu servidor de ficheros, un hosting estático).
La API manda las cabeceras CORS abiertas justo para eso, porque es una herramienta local
que solo escucha en `127.0.0.1`. En ese caso la interfaz tiene que saber dónde está la
API: se cambia la constante **`SERVIDOR`**, al principio del `<script>`, que por defecto
está vacía (el mismo sitio que sirve la página).

> **El fichero se lee del disco en cada petición.** Si lo editas, basta con recargar el
> navegador: no hay que reiniciar `api.py`.

## Qué necesita de la API

Tres endpoints, y ninguno más:

| | para qué |
|---|---|
| `POST /ask` | preguntar. Con `"comparar": true` vuelve además la vía de chat. |
| `POST /documento` | subir un documento y quedarse con el texto extraído. |
| `GET /health` | el punto del armazón: si el modelo está listo. |

Todo el detalle de esos endpoints está en [`API.md`](API.md).

## Los tres modos son el mismo caso

Es la decisión de diseño que sostiene toda la interfaz: **el caso y las preguntas se
escriben una sola vez**, y hay tres formas de hacerlo.

- **Por bloques** — se monta a mano: el caso, y luego cada pregunta con su tipo
  (`choice`, `score` o `noul`), su enunciado y sus opciones, añadiendo y quitando las que
  hagan falta.
- **Lenguaje natural** — el formato de cabeceras: `input:`, `ask:`, `choice:`, `score:`,
  `noul:`.
- **TypeSafe** — el formato de TypeSafe: `state.input` más `questions`.

No son tres sitios donde teclear por separado: **son tres vistas de lo mismo**. Se cambia
de pestaña y lo escrito aparece en la otra forma, en los dos sentidos. Por eso el nombre
de los campos se numera `q1`, `q2`, `q3`: **el nombre del campo también llega al modelo**,
y con los mismos nombres los tres modos dan exactamente el mismo resultado.

Tres detalles que ahorran disgustos:

- **El caso vive fuera de las vistas, y las pestañas debajo de él.** El caso escrito a
  mano es la entrada, la misma en los tres modos, así que no es parte de ninguno: se
  escribe una vez y las pestañas —que sí cambian de modo— van después.
- Un **`noul` es verdadero o falso**: sus dos valores son `false` y `true` y **no se pueden
  añadir más**. Solo se cambia lo que significa cada uno. La interfaz no deja añadir un
  tercero porque no existiría.
- Al cambiar el tipo de una pregunta, las opciones se reajustan: al entrar en un `noul` se
  ponen sus dos valores fijos, y al salir se ponen las del tipo nuevo, en vez de dejar
  dentro dos claves que ya no significan nada.

## El caso puede ser un documento

Se carga un documento (txt, md, csv, json, log, docx, pdf) y **su texto es el caso**: las
preguntas van sobre él. El fichero se sube a la API, que es quien sabe leerlos — así hay
**un solo lector**, el mismo que usa el resto del proyecto, en vez de dos que se comporten
distinto.

Al cargarlo se enseña **la vista previa de lo que se extrajo**: el tipo, los caracteres,
las palabras, las páginas y **el texto entero**, que es exactamente lo que recibe el
modelo. Es la forma de comprobar que la extracción hizo lo que tenía que hacer antes de
preguntar nada.

Y **mientras hay documento, el campo de escribir el caso a mano se oculta**: el caso es el
documento, así que ese campo no se usa, y tenerlo a la vista invita a escribir en un sitio
que se ignora. Vuelve solo en cuanto se quita el documento.

Un `.docx` se lee sin instalar nada; un `.pdf` pide `pip install pymupdf`. Y si el PDF es
un escaneo, sus páginas las lee el **OCR** (`rapidocr-onnxruntime`, opcional, ~2 s por
página): la vista previa dice cuántas salieron por OCR, porque ese texto puede traer
errores. Las páginas solo se informan en un PDF, que es el único formato donde ese dato es
real: en un `.txt` o un `.docx` no hay páginas hasta que alguien lo maqueta, así que no se
inventa.

## La comparación: la decisión por pregunta, el chat entero

Con «Comparar con el chat» activado, la interfaz pide **las dos vías en la misma
petición**, para que los tiempos sean de la misma corrida. Y cada vía resuelve **una sola
petición**: la decisión devuelve un valor por pregunta, y el chat escribe una respuesta
que las cubre todas.

Por eso el resultado no va emparejado fila a fila: a la izquierda van **los valores de la
decisión, uno por pregunta**, y a la derecha **la respuesta del chat, entera**. Es lo que
hay: el chat no contesta por preguntas sueltas, contesta de una vez.

Al chat **se le pasan las mismas reglas que a la decisión** —el caso, las preguntas, las
opciones y los niveles—, pero **en prosa y sin las cabeceras** `ask:`/`choice:`. Se probó
de las tres maneras y esta es la que funciona: con las cabeceras delante contesta en el
formato de la decisión (medido: un `true` a secas en 2 tokens), y sin las reglas se inventa
los nombres de las opciones. Con ellas, contesta en prosa y usa tus nombres.

Arriba de la lectura, **con ella**, una caja enseña los totales de las dos vías con su
rótulo y el multiplicador. Antes de la primera medición esa caja no existe: la pantalla
vacía solo dice qué hace cada vía y que con «Comparar» las verás lado a lado.

## Cómo se lee una respuesta

La respuesta no se «muestra»: se **lee**, como se lee una medida en un instrumento. Cada
pregunta se dibuja como una **escala graduada**:

- Un **trazo por opción**, cuya altura es su probabilidad relativa al máximo.
- El **trazo elegido**, entintado en verde.
- Un **cursor rojo** encima, señalando la marca.
- Una **línea base con graduaciones dibujadas**, y arriba el valor más alto, para que las
  alturas se lean contra algo.

En un `score` los niveles van **ordenados** (0, 1, 2); en un `choice`, de más probable a
menos. Debajo de cada trazo va su probabilidad y el nombre de la opción.

Dos números que conviene no confundir:

- **`p`** es la **probabilidad de la opción elegida**: lo seguro que está el modelo de esa
  respuesta concreta.
- **`confianza`** no es eso. Es lo **concentrada** que está la distribución: 1 sería un
  reparto sin ninguna duda y 0 un reparto plano entre todas las opciones. Una respuesta
  puede tener `p = 0.65` con confianza baja si las demás opciones se reparten el resto.

## El teclado

- **Ctrl + Enter** lanza la consulta desde cualquier modo.
- Todo lo que se pulsa se alcanza con el tabulador, y el foco se ve siempre.

## El sistema visual

La interfaz sigue un sistema declarado, no improvisado: está en
[`DESIGN.md`](DESIGN.md), con sus tokens, sus reglas y sus prohibiciones. Los
nombres de los tokens son **los mismos** que los de las variables CSS, así que el
documento se puede comprobar contra el código en vez de confiar en que digan lo mismo.

En una frase: panel claro de instrumento, armazón en verde de escala, rojo reservado al
cursor, sin sombras ni degradados, y densidad alta porque es una superficie de medida.
