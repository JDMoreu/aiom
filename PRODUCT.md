# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Dos públicos, con el mismo peso (confirmado por el autor):

- **Quien lo visita desde el repositorio** — un ingeniero curioso o quien evalúa el
  proyecto. Llega sin contexto, abre la interfaz y tiene que entender qué hace esto y
  por qué importa **sin que nadie se lo explique**. No va a leer el README antes.
- **El autor, José David Moreu**, probando y midiendo en su máquina: preguntas sobre
  documentos reales, comparando la vía de decisión con el chat, mirando tiempos y
  probabilidades. Quiere densidad y datos, no que le expliquen su propio proyecto.

El trabajo de los dos: **hacer preguntas sobre un texto y quedarse con valores** —
qué área, qué urgencia, qué tipo de documento, cuánta experiencia — en vez de leer
prosa y sacar la respuesta a mano.

## Product Purpose

AIOM ("all in one mode") responde preguntas sobre un texto **puntuando las opciones en
vez de escribiendo**. Un solo modelo local, dos vías de salida:

- **Decisión:** una petición, **0 tokens generados**, y devuelve el valor elegido con
  la probabilidad de cada opción y una confianza.
- **Chat:** prosa, un token detrás de otro.

Existe para demostrar que para muchas preguntas concretas **no hace falta generar
texto**, y que además de más rápido eso da algo que la prosa no da: **la probabilidad
de cada opción**, que se puede ordenar, medir y auditar.

El éxito: quien lo abre entiende en segundos la diferencia entre las dos vías y la ve
medida con sus propios ojos, con su propio documento.

## Positioning

El mecanismo que un producto vecino no podría copiar sin cambiar su arquitectura: **el
valor sale de puntuar opciones contra el contexto, no de generar tokens**. Eso trae tres
cosas a la vez, y las tres son propiedades del mecanismo, no promesas:

1. **0 tokens generados** en la vía de decisión.
2. **La distribución completa** de cada pregunta, no solo la respuesta.
3. **N preguntas en una sola petición**, cuando el chat necesita una por pregunta.

No es un chat más rápido: es otra cosa, y por eso la interfaz tiene que enseñar las dos
vías a la vez para que la diferencia se vea, no se lea.

## Operating Context

- Se ejecuta **en local**, contra un `llama-server` en Vulkan. Quien lo visita sin
  servidor ve el mecanismo y el diagrama; la comparación la hace quien lo tiene levantado.
- El caso de entrada casi siempre es **un documento**: un PDF, un DOCX, un correo, un
  CV. Se sube, se extrae su texto en el servidor y **ese texto es el caso**.
- Las preguntas se escriben **a mano** por quien prueba. El autor comprueba a mano, no
  con un script (decisión explícita suya).
- Terminología del producto: **caso** (el texto), **pregunta**, **opción**, **nivel**
  (en las escalas), **valor**, **probabilidad**, **confianza**, **vía** (decisión o
  chat). Los tres tipos de pregunta: **choice** (opciones con nombre), **score**
  (escala ordenada) y **noul** (sí/no). La cabecera que se escribe, el tipo del motor y
  la etiqueta de la API son tres capas del mismo concepto.

## Capabilities and Constraints

Confirmado y en uso:

- **Tres formas de escribir lo mismo**: lenguaje natural con cabeceras
  (`input:` / `ask:` / `choice:` / `score:` / `noul:`), JSON tipado al estilo TypeSafe
  (`state` + `questions`), y **por bloques** (nuevo: la interfaz se construye
  añadiendo caso, preguntas y opciones).
- **Los tres tipos**: `choice`, `score`, `noul`.
- **Comparación** decisión-vs-chat en una sola corrida, con peticiones, tiempo y tokens.
- **Documento como caso**: txt, md, csv, json, log, docx, pdf.
- **Un solo modelo local**, sin servicios externos ni claves.
- API HTTP con `/ask`, `/documento`, `/health`, `/catalog`.

Restricciones que el diseño debe respetar:

- **Un solo fichero HTML/CSS/JS, sin dependencias ni build**, servido por la propia
  API. El repositorio es Python puro: `python api.py --ui` y ya está. Nada de CDN,
  fuentes de fuera, ni segundo servidor.
- **Sin emojis** en documentos ni en nombres de fichero.
- **Nada de credenciales** en ningún artefacto.
- El idioma de la interfaz es **español**.

Lo que se ve al comparar, y que no hay que inventar porque **se mide en vivo**:

- La vía de decisión devuelve un valor y **no escribe**; la de chat escribe prosa que hay
  que interpretar.
- Con varias preguntas encadenadas la diferencia se abre: el motor las puntúa todas en la
  misma pasada, así que añadir una casi no cuesta.
- El chat es **no determinista** en cuánto escribe: la misma pregunta da respuestas de
  largo distinto.
- Agrupar preguntas cambia las de juicio y no las de «¿aparece X?».

## Brand Commitments

- El nombre es **AIOM**, y el autor lo escribe siempre así, en mayúsculas.
- **Sin emojis.** Sin lenguaje de marketing. Sin signos de admiración.
- El autor es exigente con los nombres técnicos correctos y corrige los que no lo son.

## Evidence on Hand

Todo esto es real y está en el repositorio; **nada de esto se puede inventar**:

- La comparación en vivo de las dos vías, que cualquiera puede repetir con sus preguntas.
- Casos de ejemplo reales, en `ejemplos/` (correos de soporte, un CV, un documento).
- El CV del autor (`C:\Users\JDMoreu\CV\`) y un PDF real de 9,3 MB, usados como casos.
- El diagrama de arquitectura (`docs/arquitectura.svg`), dibujado por el propio código.

**Ausencias que no se deben rellenar con invención:** no hay usuarios externos, ni
testimonios, ni clientes, ni precios, ni despliegue en la nube. El proyecto es local y
de una sola persona.

## Product Principles

1. **Enseñar la diferencia, no contarla.** La comparación de las dos vías con sus
   números es la prueba del proyecto, y va en la pantalla principal.
2. **El dato manda.** Tiempos, tokens, probabilidades y confianza son el contenido, no
   decoración: se enseñan con precisión y sin redondear a lo bonito.
3. **Una sola fuente de verdad.** El caso y las preguntas se escriben una vez; bloques,
   lenguaje natural y JSON son tres vistas de lo mismo, no tres sitios donde teclear.
4. **Las dependencias, donde hacen falta.** La consola, el tipado y el motor se abren y
   funcionan sin instalar nada. La API usa FastAPI: es un servidor web, y ahí un
   framework ahorra más de lo que cuesta.
5. **Nada que no esté medido.** Ni cifras, ni capacidades, ni promesas.

## Accessibility & Inclusion

- Contraste de texto ≥ 4.5:1 y foco de teclado visible en todo lo que se puede pulsar.
- Se usa con teclado: escribir las preguntas y lanzarlas sin ratón.
- Sin animaciones que bloqueen la lectura; el contenido se ve por defecto.
