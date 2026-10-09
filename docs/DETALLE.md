# Las 154 preguntas: opciones, respuesta esperada y tiempos

Cada pregunta con sus opciones, lo que se esperaba y por qué, lo que
contestó cada modo, cómo repartió la probabilidad y cuánto tardó.

Se regenera con `python detalle.py`.

---

## Los tres tipos

- **CHOICE** — Elegir **una** opción de una lista cerrada. Si la probabilidad está repartida entre varias opciones, el modelo no lo tiene claro aunque la ganadora gane. Ahí es donde conviene un umbral.
- **SCORE** — Situarse en una **escala ordenada** de niveles. Una puntuación de 1,4 sobre 2 significa que está entre «bastante» y «mucho», no que sea un 70%. Es una posición ponderada.
- **PROBABILITY** — Una pregunta de **sí o no**, con la probabilidad de que sí. Un 0,52 no es un «sí»: es un empate. A diferencia de CHOICE, aquí no hay una confianza separada que lo delate — hay que mirar el número.

---

## Resumen

Todo junto, para ver la diferencia de un vistazo. El detalle de cada
sección va más abajo.

### Una pregunta por caso (90 casos, 30 de cada tipo)

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **85.6%** (77/90) | 76 ms | 74 ms | 94 ms | 0.82 |
| `natural` | **85.6%** (77/90) | 77 ms | 73 ms | 95 ms | 0.82 |
| `llm` | **86.7%** (78/90) | 111 ms | 113 ms | 174 ms | — |

### Varias preguntas encadenadas (64 preguntas, 14 casos)

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **75.0%** (48/64) | 93 ms | 92 ms | 104 ms | 0.62 |
| `natural` | **75.0%** (48/64) | 95 ms | 95 ms | 106 ms | 0.62 |
| `llm` | **60.9%** (39/64) | 340 ms | 326 ms | 396 ms | — |

### Por tipo de pregunta

| tipo | modo | acierto | p50 | confianza media |
|---|---|---|---|---|
| CHOICE | `tipado` | 83.3% | 77 ms | 0.86 |
| CHOICE | `natural` | 83.3% | 73 ms | 0.86 |
| CHOICE | `llm` | 83.3% | 131 ms | — |
| SCORE | `tipado` | 83.3% | 76 ms | 0.78 |
| SCORE | `natural` | 83.3% | 78 ms | 0.78 |
| SCORE | `llm` | 83.3% | 111 ms | — |
| PROBABILITY | `tipado` | 90.0% | 76 ms | 0.83 |
| PROBABILITY | `natural` | 90.0% | 76 ms | 0.83 |
| PROBABILITY | `llm` | 93.3% | 94 ms | — |
| encadenada CHOICE | `tipado` | 77.8% | 93 ms | 0.84 |
| encadenada CHOICE | `natural` | 77.8% | 95 ms | 0.84 |
| encadenada CHOICE | `llm` | 66.7% | 340 ms | — |
| encadenada SCORE | `tipado` | 64.3% | 94 ms | 0.41 |
| encadenada SCORE | `natural` | 64.3% | 95 ms | 0.41 |
| encadenada SCORE | `llm` | 42.9% | 338 ms | — |
| encadenada sí/no | `tipado` | 78.6% | 94 ms | 0.26 |
| encadenada sí/no | `natural` | 78.6% | 95 ms | 0.26 |
| encadenada sí/no | `llm` | 64.3% | 338 ms | — |


---

## Dos fallos que NO son del modelo

Antes de echarle la culpa al tamaño del modelo conviene comprobar la
pregunta. Estos dos casos se repitieron cambiando **solo la descripción del
campo**, con el mismo modelo y la misma máquina.

### El idioma: acierta si le preguntas solo, falla si le añades las etiquetas

**Qué se ve.** Los tres casos de idioma fallan igual en `tipado` y en `natural` (responden `otro`), mientras el modo `llm` acierta. No es el tamaño del modelo: es cómo se construye la pregunta.

**Medido:**

- Descripción exacta del banco (*«¿En qué idioma está escrito? 'espanol' = Español…»*) → `ingles` **0.33 · 0.33 · 0.33** — empate a tres, no sabe
- Solo la pregunta (*«¿En qué idioma está escrito?»*) → `ingles` **0.69** — correcto
- Con las opciones entre comillas simples eliminadas → `otro` 0.70 — vuelve a fallar

**Causa.** Al añadir `'etiqueta' = descripción` a la pregunta, el texto que lee el modelo se llena de palabras en español («Español», «Inglés», «Cualquier otro idioma»). La pregunta deja de ser «¿en qué idioma está ESTO?» y pasa a ser «aquí hay tres etiquetas, elige una» — y sin referencia al texto de entrada, el modelo se queda sin señal.

**Lección.** Cuando la pregunta es sobre una **propiedad del propio texto** —el idioma, el tono—, las etiquetas no ayudan: estorban. La descripción de cada opción sirve para definir **qué categoría es cuál**, no para preguntar.

### La forma de la fruta: el mismo mecanismo, en el catálogo encadenado

**Qué se ve.** La forma falla 8 de 16 veces y siempre hacia `redonda`, incluso con un plátano. El color, en cambio, solo falla 2 de 16.

**Medido:**

- Descripción exacta del banco (plátano) → `redonda` **0.64** — incorrecto, y con confianza
- Solo la pregunta (*«¿Qué forma tiene?»*) (plátano) → `alargada` **0.67** — correcto
- Con `alargada` listada primero → `redonda` 0.55 — el orden no lo arregla

**Causa.** El mismo efecto: al colgarle la definición de cada opción, la primera etiqueta (`redonda`, la más genérica) absorbe la probabilidad. Reordenar las opciones no lo cambia, así que no es un sesgo de posición sino de dilución de la pregunta.

**Lección.** Si una pregunta falla en el modo decisión pero el mismo modelo la acierta por chat, **el problema es la descripción del campo**, no el modelo. Antes de subir de tamaño o meter RAG, prueba a quitarle las etiquetas.

### Y sobre el RAG

La intuición de que un modelo pequeño se queda corto y hay que suplirlo
con RAG y una base vectorial es buena **en general** — pero ninguno de
estos dos fallos se arregla con eso. En los dos, **el mismo modelo acierta
cuando se le quita la descripción de encima**: no le falta información,
le sobra ruido. Un RAG habría traído más texto al contexto, que es
exactamente lo que aquí empeora el resultado.

El orden correcto es: **primero simplificar la pregunta, después medir, y
solo si el modelo sigue sin poder, darle más contexto.** Meterse en RAG
antes de eso es pagar complejidad por un problema que no existe.

---

## Una pregunta por caso (90)

### CHOICE — 30 preguntas

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **83.3%** (25/30) | 77 ms | 76 ms | 92 ms | 0.86 |
| `natural` | **83.3%** (25/30) | 73 ms | 70 ms | 92 ms | 0.86 |
| `llm` | **83.3%** (25/30) | 131 ms | 133 ms | 174 ms | — |


#### 1. ¿Qué equipo debe atenderlo?

> Me cobraron dos veces la suscripción. ¿Pueden ayudarme?

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `billing`.** Un cobro duplicado es dinero: cargos y reembolsos. No es un fallo de la aplicación ni una consulta general.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 54 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `natural` | **`billing`** | 78 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `llm` | **`billing`** | 105 ms | escribe texto: no da probabilidades |


#### 2. ¿Qué equipo debe atenderlo?

> La app se cierra sola cada vez que abro el informe mensual.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `technical`.** «La app se cierra sola» es un fallo del programa, aunque sea al abrir un informe.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`technical`** | 75 ms | `billing` 0.02 · `technical` 0.98 · `general` 0.00 · conf 0.91 |
| `natural` | **`technical`** | 56 ms | `billing` 0.02 · `technical` 0.98 · `general` 0.00 · conf 0.91 |
| `llm` | **`technical`** | 120 ms | escribe texto: no da probabilidades |


#### 3. ¿Qué equipo debe atenderlo?

> ¿Cuál es vuestro horario de atención telefónica?

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `general`.** Es una consulta informativa sin incidencia: ni dinero ni error técnico.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`general`** | 55 ms | `billing` 0.00 · `technical` 0.01 · `general` 0.99 · conf 0.94 |
| `natural` | **`general`** | 75 ms | `billing` 0.00 · `technical` 0.01 · `general` 0.99 · conf 0.94 |
| `llm` | **`general`** | 99 ms | escribe texto: no da probabilidades |


#### 4. ¿Qué equipo debe atenderlo?

> Llevo tres días esperando el reembolso de un pedido cancelado.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `billing`.** El reembolso es dinero, aunque el origen fuera un pedido cancelado.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 87 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `natural` | **`billing`** | 78 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `llm` | **`billing`** | 107 ms | escribe texto: no da probabilidades |


#### 5. ¿Qué equipo debe atenderlo?

> El botón de exportar no hace nada cuando lo pulso.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `technical`.** Un botón que no responde es una función rota de la aplicación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`technical`** | 81 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 1.00 |
| `natural` | **`technical`** | 76 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 1.00 |
| `llm` | **`technical`** | 130 ms | escribe texto: no da probabilidades |


#### 6. ¿Qué sentimiento tiene el mensaje?

> Me encantó el servicio, muy rápido todo. Gracias!

**choice:**

- `positivo` — Satisfacción o agradecimiento
- `negativo` — Queja, enfado o frustración
- `neutro` — Sin carga emocional clara

**Se esperaba `positivo`.** Agradecimiento explícito y sin queja: positivo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`positivo`** | 87 ms | `positivo` 1.00 · `negativo` 0.00 · `neutro` 0.00 · conf 1.00 |
| `natural` | **`positivo`** | 54 ms | `positivo` 1.00 · `negativo` 0.00 · `neutro` 0.00 · conf 1.00 |
| `llm` | **`positivo`** | 149 ms | escribe texto: no da probabilidades |


#### 7. ¿Qué sentimiento tiene el mensaje?

> Es la tercera vez que escribo y nadie me contesta. Es vergonzoso.

**choice:**

- `positivo` — Satisfacción o agradecimiento
- `negativo` — Queja, enfado o frustración
- `neutro` — Sin carga emocional clara

**Se esperaba `negativo`.** Reproche directo («es vergonzoso») además del problema: negativo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`negativo`** | 76 ms | `positivo` 0.00 · `negativo` 1.00 · `neutro` 0.00 · conf 1.00 |
| `natural` | **`negativo`** | 54 ms | `positivo` 0.00 · `negativo` 1.00 · `neutro` 0.00 · conf 1.00 |
| `llm` | **`negativo`** | 146 ms | escribe texto: no da probabilidades |


#### 8. ¿Qué sentimiento tiene el mensaje?

> Quería consultar si el plan incluye facturación automática.

**choice:**

- `positivo` — Satisfacción o agradecimiento
- `negativo` — Queja, enfado o frustración
- `neutro` — Sin carga emocional clara

**Se esperaba `neutro`.** Pregunta informativa sin carga emocional: neutro.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`neutro`** | 76 ms | `positivo` 0.00 · `negativo` 0.00 · `neutro` 1.00 · conf 1.00 |
| `natural` | **`neutro`** | 69 ms | `positivo` 0.00 · `negativo` 0.00 · `neutro` 1.00 · conf 1.00 |
| `llm` | **`neutro`** | 140 ms | escribe texto: no da probabilidades |


#### 9. ¿Qué sentimiento tiene el mensaje?

> Gracias por arreglarlo tan rápido, sois los mejores.

**choice:**

- `positivo` — Satisfacción o agradecimiento
- `negativo` — Queja, enfado o frustración
- `neutro` — Sin carga emocional clara

**Se esperaba `positivo`.** Elogio explícito al servicio: positivo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`positivo`** | 87 ms | `positivo` 1.00 · `negativo` 0.00 · `neutro` 0.00 · conf 1.00 |
| `natural` | **`positivo`** | 84 ms | `positivo` 1.00 · `negativo` 0.00 · `neutro` 0.00 · conf 1.00 |
| `llm` | **`positivo`** | 173 ms | escribe texto: no da probabilidades |


#### 10. ¿Qué sentimiento tiene el mensaje?

> Nunca funciona nada, estoy harto de esta aplicación.

**choice:**

- `positivo` — Satisfacción o agradecimiento
- `negativo` — Queja, enfado o frustración
- `neutro` — Sin carga emocional clara

**Se esperaba `negativo`.** «Estoy harto» es frustración declarada: negativo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`negativo`** | 92 ms | `positivo` 0.00 · `negativo` 1.00 · `neutro` 0.00 · conf 1.00 |
| `natural` | **`negativo`** | 79 ms | `positivo` 0.00 · `negativo` 1.00 · `neutro` 0.00 · conf 1.00 |
| `llm` | **`negativo`** | 123 ms | escribe texto: no da probabilidades |


#### 11. ¿Qué quiere el usuario?

> ¿Cómo puedo cambiar la contraseña de mi cuenta?

**choice:**

- `pregunta` — Pide información o instrucciones
- `queja` — Reporta un problema o expresa descontento
- `peticion` — Solicita una acción concreta

**Se esperaba `pregunta`.** Pide información sobre cómo hacer algo; no reporta un fallo ni pide que se actúe.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`peticion`** **← MAL** | 73 ms | `pregunta` 0.10 · `queja` 0.00 · `peticion` 0.90 · conf 0.70 |
| `natural` | **`peticion`** **← MAL** | 90 ms | `pregunta` 0.10 · `queja` 0.00 · `peticion` 0.90 · conf 0.70 |
| `llm` | **`peticion`** **← MAL** | 135 ms | escribe texto: no da probabilidades |


#### 12. ¿Qué quiere el usuario?

> Necesito que me cambien la dirección de envío del pedido 4471.

**choice:**

- `pregunta` — Pide información o instrucciones
- `queja` — Reporta un problema o expresa descontento
- `peticion` — Solicita una acción concreta

**Se esperaba `peticion`.** Pide una acción concreta (cambiar la dirección), no una explicación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`peticion`** | 88 ms | `pregunta` 0.00 · `queja` 0.00 · `peticion` 1.00 · conf 1.00 |
| `natural` | **`peticion`** | 85 ms | `pregunta` 0.00 · `queja` 0.00 · `peticion` 1.00 · conf 1.00 |
| `llm` | **`peticion`** | 174 ms | escribe texto: no da probabilidades |


#### 13. ¿Qué quiere el usuario?

> El producto llegó roto y nadie me ha dado solución.

**choice:**

- `pregunta` — Pide información o instrucciones
- `queja` — Reporta un problema o expresa descontento
- `peticion` — Solicita una acción concreta

**Se esperaba `queja`.** Reporta un problema y la falta de solución: es una queja.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`queja`** | 76 ms | `pregunta` 0.00 · `queja` 1.00 · `peticion` 0.00 · conf 1.00 |
| `natural` | **`queja`** | 71 ms | `pregunta` 0.00 · `queja` 1.00 · `peticion` 0.00 · conf 1.00 |
| `llm` | **`queja`** | 132 ms | escribe texto: no da probabilidades |


#### 14. ¿Qué quiere el usuario?

> ¿Dónde puedo ver el historial de mis pagos?

**choice:**

- `pregunta` — Pide información o instrucciones
- `queja` — Reporta un problema o expresa descontento
- `peticion` — Solicita una acción concreta

**Se esperaba `pregunta`.** Pide saber dónde consultar algo: información.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`pregunta`** | 81 ms | `pregunta` 0.72 · `queja` 0.00 · `peticion` 0.28 · conf 0.45 |
| `natural` | **`pregunta`** | 54 ms | `pregunta` 0.72 · `queja` 0.00 · `peticion` 0.28 · conf 0.45 |
| `llm` | **`peticion`** **← MAL** | 154 ms | escribe texto: no da probabilidades |


#### 15. ¿Qué quiere el usuario?

> Por favor, cancelen mi suscripción a partir del mes que viene.

**choice:**

- `pregunta` — Pide información o instrucciones
- `queja` — Reporta un problema o expresa descontento
- `peticion` — Solicita una acción concreta

**Se esperaba `peticion`.** Solicita una acción concreta (cancelar), no pregunta nada.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`peticion`** | 84 ms | `pregunta` 0.00 · `queja` 0.00 · `peticion` 1.00 · conf 1.00 |
| `natural` | **`peticion`** | 81 ms | `pregunta` 0.00 · `queja` 0.00 · `peticion` 1.00 · conf 1.00 |
| `llm` | **`peticion`** | 165 ms | escribe texto: no da probabilidades |


#### 16. ¿A qué categoría pertenece el producto?

> Zapatillas de trail impermeables con suela de agarre para barro.

**choice:**

- `calzado` — Zapatos, botas o zapatillas
- `ropa` — Prendas de vestir
- `accesorios` — Complementos y equipamiento

**Se esperaba `calzado`.** Zapatillas son calzado, aunque sean de trail.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`calzado`** | 72 ms | `calzado` 1.00 · `ropa` 0.00 · `accesorios` 0.00 · conf 1.00 |
| `natural` | **`calzado`** | 73 ms | `calzado` 1.00 · `ropa` 0.00 · `accesorios` 0.00 · conf 1.00 |
| `llm` | **`calzado`** | 154 ms | escribe texto: no da probabilidades |


#### 17. ¿A qué categoría pertenece el producto?

> Chaqueta impermeable con capucha, talla L, color azul marino.

**choice:**

- `calzado` — Zapatos, botas o zapatillas
- `ropa` — Prendas de vestir
- `accesorios` — Complementos y equipamiento

**Se esperaba `ropa`.** Chaqueta es una prenda de vestir, con talla y color.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`ropa`** | 56 ms | `calzado` 0.00 · `ropa` 0.93 · `accesorios` 0.07 · conf 0.77 |
| `natural` | **`ropa`** | 55 ms | `calzado` 0.00 · `ropa` 0.93 · `accesorios` 0.07 · conf 0.77 |
| `llm` | **`ropa`** | 147 ms | escribe texto: no da probabilidades |


#### 18. ¿A qué categoría pertenece el producto?

> Mochila de 30 litros con funda de lluvia incluida.

**choice:**

- `calzado` — Zapatos, botas o zapatillas
- `ropa` — Prendas de vestir
- `accesorios` — Complementos y equipamiento

**Se esperaba `accesorios`.** Una mochila es equipamiento, no una prenda que se vista.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`accesorios`** | 79 ms | `calzado` 0.00 · `ropa` 0.00 · `accesorios` 1.00 · conf 0.98 |
| `natural` | **`accesorios`** | 72 ms | `calzado` 0.00 · `ropa` 0.00 · `accesorios` 1.00 · conf 0.98 |
| `llm` | **`accesorios`** | 148 ms | escribe texto: no da probabilidades |


#### 19. ¿A qué categoría pertenece el producto?

> Botas de montaña de caña alta para invierno.

**choice:**

- `calzado` — Zapatos, botas o zapatillas
- `ropa` — Prendas de vestir
- `accesorios` — Complementos y equipamiento

**Se esperaba `calzado`.** Botas son calzado, sin importar el uso de montaña.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`calzado`** | 77 ms | `calzado` 1.00 · `ropa` 0.00 · `accesorios` 0.00 · conf 1.00 |
| `natural` | **`calzado`** | 56 ms | `calzado` 1.00 · `ropa` 0.00 · `accesorios` 0.00 · conf 1.00 |
| `llm` | **`calzado`** | 130 ms | escribe texto: no da probabilidades |


#### 20. ¿A qué categoría pertenece el producto?

> Guantes térmicos y gorro de lana para actividades de invierno.

**choice:**

- `calzado` — Zapatos, botas o zapatillas
- `ropa` — Prendas de vestir
- `accesorios` — Complementos y equipamiento

**Se esperaba `accesorios`.** Guantes y gorro son complementos; se llevan encima de la ropa, no son la prenda.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`accesorios`** | 56 ms | `calzado` 0.03 · `ropa` 0.05 · `accesorios` 0.92 · conf 0.70 |
| `natural` | **`accesorios`** | 55 ms | `calzado` 0.03 · `ropa` 0.05 · `accesorios` 0.92 · conf 0.70 |
| `llm` | **`accesorios`** | 160 ms | escribe texto: no da probabilidades |


#### 21. ¿En qué idioma está escrito?

> Hello, I would like to know if you ship to Ireland.

**choice:**

- `espanol` — Español
- `ingles` — Inglés
- `otro` — Cualquier otro idioma

**Se esperaba `ingles`.** El mensaje está en inglés.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`otro`** **← MAL** | 78 ms | `espanol` 0.01 · `ingles` 0.01 · `otro` 0.98 · conf 0.89 |
| `natural` | **`otro`** **← MAL** | 78 ms | `espanol` 0.01 · `ingles` 0.01 · `otro` 0.98 · conf 0.89 |
| `llm` | **`ingles`** | 106 ms | escribe texto: no da probabilidades |


#### 22. ¿En qué idioma está escrito?

> Buenos días, quería consultar el estado de mi pedido.

**choice:**

- `espanol` — Español
- `ingles` — Inglés
- `otro` — Cualquier otro idioma

**Se esperaba `espanol`.** El mensaje está en español.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`otro`** **← MAL** | 76 ms | `espanol` 0.27 · `ingles` 0.02 · `otro` 0.71 · conf 0.39 |
| `natural` | **`otro`** **← MAL** | 79 ms | `espanol` 0.27 · `ingles` 0.02 · `otro` 0.71 · conf 0.39 |
| `llm` | **`espanol`** | 139 ms | escribe texto: no da probabilidades |


#### 23. ¿En qué idioma está escrito?

> Bonjour, je voudrais un remboursement s'il vous plaît.

**choice:**

- `espanol` — Español
- `ingles` — Inglés
- `otro` — Cualquier otro idioma

**Se esperaba `otro`.** Está en francés, que no es ni español ni inglés: la categoría «otro» existe justo para esto.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`otro`** | 76 ms | `espanol` 0.20 · `ingles` 0.35 · `otro` 0.44 · conf 0.04 |
| `natural` | **`otro`** | 79 ms | `espanol` 0.20 · `ingles` 0.35 · `otro` 0.44 · conf 0.04 |
| `llm` | **`espanol`** **← MAL** | 117 ms | escribe texto: no da probabilidades |


#### 24. ¿Qué prioridad tiene el caso?

> La web no carga desde esta mañana en toda la oficina.

**choice:**

- `alta` — Bloquea el trabajo ahora mismo
- `media` — Molesto pero hay forma de seguir
- `baja` — No urge, puede esperar

**Se esperaba `alta`.** La web caída impide trabajar a toda la oficina: bloquea.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`alta`** | 78 ms | `alta` 0.98 · `media` 0.02 · `baja` 0.00 · conf 0.90 |
| `natural` | **`alta`** | 55 ms | `alta` 0.98 · `media` 0.02 · `baja` 0.00 · conf 0.90 |
| `llm` | **`alta`** | 118 ms | escribe texto: no da probabilidades |


#### 25. ¿Qué prioridad tiene el caso?

> El color del icono no me gusta demasiado, pero funciona bien.

**choice:**

- `alta` — Bloquea el trabajo ahora mismo
- `media` — Molesto pero hay forma de seguir
- `baja` — No urge, puede esperar

**Se esperaba `baja`.** Un detalle estético con la función intacta: no urge.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`media`** **← MAL** | 55 ms | `alta` 0.00 · `media` 1.00 · `baja` 0.00 · conf 0.98 |
| `natural` | **`media`** **← MAL** | 56 ms | `alta` 0.00 · `media` 1.00 · `baja` 0.00 · conf 0.98 |
| `llm` | **`media`** **← MAL** | 98 ms | escribe texto: no da probabilidades |


#### 26. ¿Qué prioridad tiene el caso?

> Tengo que exportar el informe a mano porque el botón falla, pero puedo seguir.

**choice:**

- `alta` — Bloquea el trabajo ahora mismo
- `media` — Molesto pero hay forma de seguir
- `baja` — No urge, puede esperar

**Se esperaba `media`.** Hay una forma de seguir (exportar a mano), así que molesta pero no bloquea.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`media`** | 76 ms | `alta` 0.00 · `media` 1.00 · `baja` 0.00 · conf 0.98 |
| `natural` | **`media`** | 56 ms | `alta` 0.00 · `media` 1.00 · `baja` 0.00 · conf 0.98 |
| `llm` | **`media`** | 122 ms | escribe texto: no da probabilidades |


#### 27. ¿Qué prioridad tiene el caso?

> No podemos facturar a clientes porque el sistema está caído.

**choice:**

- `alta` — Bloquea el trabajo ahora mismo
- `media` — Molesto pero hay forma de seguir
- `baja` — No urge, puede esperar

**Se esperaba `alta`.** Sin facturar no hay negocio: bloquea.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`alta`** | 77 ms | `alta` 0.97 · `media` 0.01 · `baja` 0.02 · conf 0.85 |
| `natural` | **`alta`** | 78 ms | `alta` 0.97 · `media` 0.01 · `baja` 0.02 · conf 0.85 |
| `llm` | **`alta`** | 116 ms | escribe texto: no da probabilidades |


#### 28. ¿Qué prioridad tiene el caso?

> ¿Podéis añadir un modo oscuro en alguna actualización futura?

**choice:**

- `alta` — Bloquea el trabajo ahora mismo
- `media` — Molesto pero hay forma de seguir
- `baja` — No urge, puede esperar

**Se esperaba `baja`.** Es una sugerencia para el futuro, no un problema actual.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`media`** **← MAL** | 80 ms | `alta` 0.02 · `media` 0.60 · `baja` 0.37 · conf 0.30 |
| `natural` | **`media`** **← MAL** | 55 ms | `alta` 0.02 · `media` 0.60 · `baja` 0.37 · conf 0.30 |
| `llm` | **`media`** **← MAL** | 104 ms | escribe texto: no da probabilidades |


#### 29. ¿Qué equipo debe atenderlo?

> El pago se rechazó tres veces y no sé por qué.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `billing`.** Un pago rechazado es dinero, aunque el usuario no sepa la causa.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 71 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `natural` | **`billing`** | 71 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `llm` | **`billing`** | 126 ms | escribe texto: no da probabilidades |


#### 30. ¿Qué equipo debe atenderlo?

> La integración con nuestra herramienta de nóminas dejó de sincronizar ayer.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación e integraciones
- `general` — Otras consultas

**Se esperaba `technical`.** Una integración que deja de sincronizar es un fallo técnico, no de facturación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`technical`** | 87 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 0.98 |
| `natural` | **`technical`** | 92 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 0.98 |
| `llm` | **`technical`** | 151 ms | escribe texto: no da probabilidades |


### SCORE — 30 preguntas

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **83.3%** (25/30) | 76 ms | 74 ms | 94 ms | 0.78 |
| `natural` | **83.3%** (25/30) | 78 ms | 76 ms | 91 ms | 0.78 |
| `llm` | **83.3%** (25/30) | 111 ms | 110 ms | 134 ms | — |


#### 1. ¿Qué relevancia tiene este elemento para la solicitud?

> Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una ficha de zapatillas de trail impermeables con guía de tallas y reseñas.

**score:**

- `0` — No relevante
- `1` — Algo relevante
- `2` — Muy relevante

**Se esperaba `2`.** Nivel 2: zapatillas impermeables de trail responden exactamente a una búsqueda de calzado de senderismo para lluvia.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 94 ms |  · conf 0.97 |
| `natural` | **`2.0`** | 77 ms |  · conf 0.97 |
| `llm` | **`2.0`** | 119 ms | escribe texto: no da probabilidades |


#### 2. ¿Qué relevancia tiene este elemento para la solicitud?

> Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una ficha de calcetines de algodón para vestir.

**score:**

- `0` — No relevante
- `1` — Algo relevante
- `2` — Muy relevante

**Se esperaba `0`.** Nivel 0: unos calcetines de vestir no tienen que ver con la búsqueda.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 74 ms |  · conf 0.90 |
| `natural` | **`0.0`** | 60 ms |  · conf 0.90 |
| `llm` | **`0.0`** | 130 ms | escribe texto: no da probabilidades |


#### 3. ¿Qué relevancia tiene este elemento para la solicitud?

> Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una ficha de botas de montaña de caña alta para invierno.

**score:**

- `0` — No relevante
- `1` — Algo relevante
- `2` — Muy relevante

**Se esperaba `1`.** Nivel 1: son calzado de montaña, pero de caña alta y para invierno — se acerca sin ser lo pedido.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** **← MAL** | 82 ms |  · conf 0.25 |
| `natural` | **`0.0`** **← MAL** | 82 ms |  · conf 0.25 |
| `llm` | **`1.0`** | 122 ms | escribe texto: no da probabilidades |


#### 4. ¿Qué relevancia tiene este elemento para la solicitud?

> Búsqueda: regalo para un niño de 6 años aficionado a los dinosaurios. Resultado: un set de figuras de dinosaurios de plástico, para mayores de 3 años.

**score:**

- `0` — No relevante
- `1` — Algo relevante
- `2` — Muy relevante

**Se esperaba `2`.** Nivel 2: figuras de dinosaurios para mayores de 3 años encajan con un niño de 6 aficionado.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 82 ms |  · conf 0.87 |
| `natural` | **`2.0`** | 76 ms |  · conf 0.87 |
| `llm` | **`2.0`** | 131 ms | escribe texto: no da probabilidades |


#### 5. ¿Qué relevancia tiene este elemento para la solicitud?

> Búsqueda: regalo para un niño de 6 años aficionado a los dinosaurios. Resultado: una novela histórica para adultos sobre la Segunda Guerra Mundial.

**score:**

- `0` — No relevante
- `1` — Algo relevante
- `2` — Muy relevante

**Se esperaba `0`.** Nivel 0: una novela histórica para adultos no tiene relación con el regalo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 59 ms |  · conf 1.00 |
| `natural` | **`0.0`** | 77 ms |  · conf 1.00 |
| `llm` | **`0.0`** | 131 ms | escribe texto: no da probabilidades |


#### 6. ¿Qué gravedad tiene el problema reportado?

> El botón de exportar se ve un poco desplazado dos píxeles en pantallas pequeñas. La función de exportar funciona correctamente.

**score:**

- `0` — Cosmético, sin impacto en la funcionalidad
- `1` — Función rota pero existe una forma de saltárselo
- `2` — Bloqueante, no hay alternativa

**Se esperaba `0`.** Nivel 0: dos píxeles de desplazamiento no afectan a la funcionalidad.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** **← MAL** | 81 ms |  · conf 0.38 |
| `natural` | **`1.0`** **← MAL** | 76 ms |  · conf 0.38 |
| `llm` | **`0.0`** | 129 ms | escribe texto: no da probabilidades |


#### 7. ¿Qué gravedad tiene el problema reportado?

> El botón de exportar no responde en Safari. En Chrome funciona, y la mayoría de los clientes usan Chrome.

**score:**

- `0` — Cosmético, sin impacto en la funcionalidad
- `1` — Función rota pero existe una forma de saltárselo
- `2` — Bloqueante, no hay alternativa

**Se esperaba `1`.** Nivel 1: la función está rota en Safari, pero Chrome sirve de alternativa para la mayoría.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 70 ms |  · conf 0.73 |
| `natural` | **`1.0`** | 83 ms |  · conf 0.73 |
| `llm` | **`1.0`** | 118 ms | escribe texto: no da probabilidades |


#### 8. ¿Qué gravedad tiene el problema reportado?

> La aplicación no arranca en ningún navegador. Ningún cliente puede entrar desde esta mañana.

**score:**

- `0` — Cosmético, sin impacto en la funcionalidad
- `1` — Función rota pero existe una forma de saltárselo
- `2` — Bloqueante, no hay alternativa

**Se esperaba `2`.** Nivel 2: no arranca para nadie y no hay alternativa posible.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 54 ms |  · conf 0.99 |
| `natural` | **`2.0`** | 79 ms |  · conf 0.99 |
| `llm` | **`2.0`** | 118 ms | escribe texto: no da probabilidades |


#### 9. ¿Qué gravedad tiene el problema reportado?

> El texto del pie de página tiene una errata en una palabra.

**score:**

- `0` — Cosmético, sin impacto en la funcionalidad
- `1` — Función rota pero existe una forma de saltárselo
- `2` — Bloqueante, no hay alternativa

**Se esperaba `0`.** Nivel 0: una errata en el pie es cosmética.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 54 ms |  · conf 0.27 |
| `natural` | **`0.0`** | 82 ms |  · conf 0.27 |
| `llm` | **`0.0`** | 110 ms | escribe texto: no da probabilidades |


#### 10. ¿Qué gravedad tiene el problema reportado?

> La búsqueda devuelve resultados vacíos, pero se puede navegar por categorías.

**score:**

- `0` — Cosmético, sin impacto en la funcionalidad
- `1` — Función rota pero existe una forma de saltárselo
- `2` — Bloqueante, no hay alternativa

**Se esperaba `1`.** Nivel 1: la búsqueda no devuelve nada, pero se puede navegar por categorías.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** **← MAL** | 72 ms |  · conf 0.40 |
| `natural` | **`0.0`** **← MAL** | 70 ms |  · conf 0.40 |
| `llm` | **`1.0`** | 114 ms | escribe texto: no da probabilidades |


#### 11. ¿Qué calidad tiene la experiencia descrita?

> Este producto es exactamente lo que buscaba, llegó antes de lo previsto y en perfecto estado.

**score:**

- `0` — Mala
- `1` — Aceptable
- `2` — Excelente

**Se esperaba `2`.** Nivel 2: llegó antes, en perfecto estado y era lo buscado.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 68 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 68 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 111 ms | escribe texto: no da probabilidades |


#### 12. ¿Qué calidad tiene la experiencia descrita?

> El producto llegó con un golpe visible en la caja y un arañazo en la carcasa.

**score:**

- `0` — Mala
- `1` — Aceptable
- `2` — Excelente

**Se esperaba `0`.** Nivel 0: golpe visible y arañazo en la carcasa.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 74 ms |  · conf 1.00 |
| `natural` | **`0.0`** | 76 ms |  · conf 1.00 |
| `llm` | **`0.0`** | 80 ms | escribe texto: no da probabilidades |


#### 13. ¿Qué calidad tiene la experiencia descrita?

> El producto funciona bien aunque el embalaje venía algo dañado y tardó un día más de lo previsto.

**score:**

- `0` — Mala
- `1` — Aceptable
- `2` — Excelente

**Se esperaba `1`.** Nivel 1: funciona bien, aunque el embalaje venía dañado y llegó un día tarde.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 58 ms |  · conf 0.79 |
| `natural` | **`1.0`** | 78 ms |  · conf 0.79 |
| `llm` | **`1.0`** | 105 ms | escribe texto: no da probabilidades |


#### 14. ¿Qué calidad tiene la experiencia descrita?

> Impecable: envío rápido, embalaje cuidado y el producto supera lo anunciado.

**score:**

- `0` — Mala
- `1` — Aceptable
- `2` — Excelente

**Se esperaba `2`.** Nivel 2: envío rápido, embalaje cuidado y supera lo anunciado.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 75 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 55 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 111 ms | escribe texto: no da probabilidades |


#### 15. ¿Qué calidad tiene la experiencia descrita?

> Nada más abrir la caja el aparato no encendía y tuve que devolverlo.

**score:**

- `0` — Mala
- `1` — Aceptable
- `2` — Excelente

**Se esperaba `0`.** Nivel 0: no encendía y hubo que devolverlo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 76 ms |  · conf 1.00 |
| `natural` | **`0.0`** | 80 ms |  · conf 1.00 |
| `llm` | **`0.0`** | 87 ms | escribe texto: no da probabilidades |


#### 16. ¿Qué urgencia tiene este caso?

> El sistema lleva caído desde las 8:00 y toda la plantilla está parada sin poder facturar.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `2`.** Nivel 2: el sistema caído con toda la plantilla parada y sin facturar.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 60 ms |  · conf 0.98 |
| `natural` | **`2.0`** | 88 ms |  · conf 0.98 |
| `llm` | **`2.0`** | 134 ms | escribe texto: no da probabilidades |


#### 17. ¿Qué urgencia tiene este caso?

> Quería saber si hay planes de añadir más idiomas en el futuro.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `0`.** Nivel 0: una pregunta sobre planes futuros puede esperar.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 76 ms |  · conf 0.68 |
| `natural` | **`0.0`** | 79 ms |  · conf 0.68 |
| `llm` | **`1.0`** **← MAL** | 111 ms | escribe texto: no da probabilidades |


#### 18. ¿Qué urgencia tiene este caso?

> El informe mensual del cliente sale mañana y el botón de exportar falla.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `1`.** Nivel 1: hay una fecha mañana, así que conviene atenderlo hoy sin ser una caída.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 79 ms |  · conf 0.42 |
| `natural` | **`1.0`** | 63 ms |  · conf 0.42 |
| `llm` | **`2.0`** **← MAL** | 107 ms | escribe texto: no da probabilidades |


#### 19. ¿Qué urgencia tiene este caso?

> Se ha filtrado el acceso a la cuenta de un cliente con datos de pago visibles.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `2`.** Nivel 2: datos de pago de un cliente expuestos exige acción inmediata.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 78 ms |  · conf 0.94 |
| `natural` | **`2.0`** | 79 ms |  · conf 0.94 |
| `llm` | **`2.0`** | 126 ms | escribe texto: no da probabilidades |


#### 20. ¿Qué urgencia tiene este caso?

> Me gustaría saber si el manual está disponible en papel.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `0`.** Nivel 0: saber si el manual está en papel no urge.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 76 ms |  · conf 0.83 |
| `natural` | **`0.0`** | 76 ms |  · conf 0.83 |
| `llm` | **`1.0`** **← MAL** | 96 ms | escribe texto: no da probabilidades |


#### 21. ¿Qué tan útil fue esta respuesta?

> La respuesta explica paso a paso cómo cambiar la contraseña y funcionó a la primera.

**score:**

- `0` — Nada útil
- `1` — Parcialmente útil
- `2` — Muy útil

**Se esperaba `2`.** Nivel 2: paso a paso y funcionó a la primera.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 85 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 91 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 129 ms | escribe texto: no da probabilidades |


#### 22. ¿Qué tan útil fue esta respuesta?

> La respuesta repite lo mismo que ya venía en el manual y no resuelve la duda.

**score:**

- `0` — Nada útil
- `1` — Parcialmente útil
- `2` — Muy útil

**Se esperaba `0`.** Nivel 0: repite el manual y no resuelve la duda.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 84 ms |  · conf 0.73 |
| `natural` | **`0.0`** | 79 ms |  · conf 0.73 |
| `llm` | **`1.0`** **← MAL** | 102 ms | escribe texto: no da probabilidades |


#### 23. ¿Qué tan útil fue esta respuesta?

> La respuesta soluciona el problema pero no explica por qué ocurría.

**score:**

- `0` — Nada útil
- `1` — Parcialmente útil
- `2` — Muy útil

**Se esperaba `1`.** Nivel 1: soluciona el problema pero no explica la causa.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 76 ms |  · conf 0.61 |
| `natural` | **`1.0`** | 54 ms |  · conf 0.61 |
| `llm` | **`1.0`** | 82 ms | escribe texto: no da probabilidades |


#### 24. ¿Qué tan útil fue esta respuesta?

> Instrucciones claras, con capturas y el enlace directo a la pantalla exacta.

**score:**

- `0` — Nada útil
- `1` — Parcialmente útil
- `2` — Muy útil

**Se esperaba `2`.** Nivel 2: instrucciones claras, con capturas y enlace directo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 76 ms |  · conf 0.99 |
| `natural` | **`2.0`** | 85 ms |  · conf 0.99 |
| `llm` | **`2.0`** | 105 ms | escribe texto: no da probabilidades |


#### 25. ¿Qué tan útil fue esta respuesta?

> Me remitieron a otra sección sin decirme dónde encontrarla.

**score:**

- `0` — Nada útil
- `1` — Parcialmente útil
- `2` — Muy útil

**Se esperaba `0`.** Nivel 0: remite a otra sección sin decir dónde.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** **← MAL** | 74 ms |  · conf 0.55 |
| `natural` | **`1.0`** **← MAL** | 70 ms |  · conf 0.55 |
| `llm` | **`0.0`** | 92 ms | escribe texto: no da probabilidades |


#### 26. ¿Cuál es el estado del artículo?

> El producto está en buen estado general, con alguna marca de uso leve en la esquina.

**score:**

- `0` — Deteriorado
- `1` — Con señales de uso
- `2` — Como nuevo

**Se esperaba `1`.** Nivel 1: buen estado general con alguna marca de uso.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 78 ms |  · conf 0.39 |
| `natural` | **`1.0`** | 78 ms |  · conf 0.39 |
| `llm` | **`1.0`** | 128 ms | escribe texto: no da probabilidades |


#### 27. ¿Cuál es el estado del artículo?

> El artículo viene precintado en su caja original, sin abrir.

**score:**

- `0` — Deteriorado
- `1` — Con señales de uso
- `2` — Como nuevo

**Se esperaba `2`.** Nivel 2: precintado en su caja original, sin abrir.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 77 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 78 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 77 ms | escribe texto: no da probabilidades |


#### 28. ¿Cuál es el estado del artículo?

> El artículo tiene la pantalla rota y no enciende.

**score:**

- `0` — Deteriorado
- `1` — Con señales de uso
- `2` — Como nuevo

**Se esperaba `0`.** Nivel 0: pantalla rota y no enciende.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 76 ms |  · conf 0.97 |
| `natural` | **`0.0`** | 78 ms |  · conf 0.97 |
| `llm` | **`0.0`** | 90 ms | escribe texto: no da probabilidades |


#### 29. ¿Cuál es el estado del artículo?

> La carcasa está desgastada en las esquinas y la bisagra suena al cerrar.

**score:**

- `0` — Deteriorado
- `1` — Con señales de uso
- `2` — Como nuevo

**Se esperaba `1`.** Nivel 1: desgaste en las esquinas y la bisagra suena.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 55 ms |  · conf 0.80 |
| `natural` | **`1.0`** | 77 ms |  · conf 0.80 |
| `llm` | **`0.0`** **← MAL** | 107 ms | escribe texto: no da probabilidades |


#### 30. ¿Cuál es el estado del artículo?

> El teclado tiene dos teclas hundidas y la pantalla parpadea al moverla.

**score:**

- `0` — Deteriorado
- `1` — Con señales de uso
- `2` — Como nuevo

**Se esperaba `0`.** Nivel 0: teclas hundidas y pantalla que parpadea.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** **← MAL** | 88 ms |  · conf 0.89 |
| `natural` | **`1.0`** **← MAL** | 79 ms |  · conf 0.89 |
| `llm` | **`0.0`** | 95 ms | escribe texto: no da probabilidades |


### PROBABILITY — 30 preguntas

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **90.0%** (27/30) | 76 ms | 73 ms | 93 ms | 0.83 |
| `natural` | **90.0%** (27/30) | 76 ms | 74 ms | 95 ms | 0.83 |
| `llm` | **93.3%** (28/30) | 94 ms | 96 ms | 129 ms | — |


#### 1. ¿Es spam o intento de estafa?

> ¡GANADOR! Has sido seleccionado para recibir un iPhone gratis. Haz clic aquí para reclamarlo antes de 24 horas.

**noul:**

- `true` — Es spam, fraude o intento de estafa
- `false` — Es un mensaje legítimo

**Se esperaba `True`.** Sí: premio llamativo, urgencia artificial («antes de 24 horas») y un enlace. Es el patrón clásico.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 69 ms | `true` 0.93 · `false` 0.07 · conf 0.65 |
| `natural` | **`True`** | 95 ms | `true` 0.93 · `false` 0.07 · conf 0.65 |
| `llm` | **`True`** | 79 ms | escribe texto: no da probabilidades |


#### 2. ¿Es spam o intento de estafa?

> Tu pedido 4471 ha salido de nuestro almacén y llegará el jueves.

**noul:**

- `true` — Es spam, fraude o intento de estafa
- `false` — Es un mensaje legítimo

**Se esperaba `False`.** No: es el aviso de envío del propio pedido, sin petición de datos ni enlace sospechoso.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 76 ms | `true` 0.00 · `false` 1.00 · conf 0.96 |
| `natural` | **`False`** | 76 ms | `true` 0.00 · `false` 1.00 · conf 0.96 |
| `llm` | **`True`** **← MAL** | 89 ms | escribe texto: no da probabilidades |


#### 3. ¿Es spam o intento de estafa?

> Haga clic en este enlace para verificar su cuenta bancaria o será suspendida.

**noul:**

- `true` — Es spam, fraude o intento de estafa
- `false` — Es un mensaje legítimo

**Se esperaba `True`.** Sí: pide verificar la cuenta bancaria bajo amenaza de suspensión. Ingeniería social.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 54 ms | `true` 0.97 · `false` 0.03 · conf 0.78 |
| `natural` | **`True`** | 77 ms | `true` 0.97 · `false` 0.03 · conf 0.78 |
| `llm` | **`True`** | 91 ms | escribe texto: no da probabilidades |


#### 4. ¿Es spam o intento de estafa?

> Gracias por tu compra. Adjuntamos la factura del pedido 3312.

**noul:**

- `true` — Es spam, fraude o intento de estafa
- `false` — Es un mensaje legítimo

**Se esperaba `False`.** No: factura del pedido con número, sin pedir nada.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 69 ms | `true` 0.05 · `false` 0.95 · conf 0.72 |
| `natural` | **`False`** | 71 ms | `true` 0.05 · `false` 0.95 · conf 0.72 |
| `llm` | **`True`** **← MAL** | 94 ms | escribe texto: no da probabilidades |


#### 5. ¿Es spam o intento de estafa?

> URGENTE: su suscripción caduca hoy, introduzca sus datos de tarjeta para renovarla al instante.

**noul:**

- `true` — Es spam, fraude o intento de estafa
- `false` — Es un mensaje legítimo

**Se esperaba `True`.** Sí: urgencia, caducidad y petición de datos de tarjeta. Los tres a la vez.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 80 ms | `true` 0.93 · `false` 0.07 · conf 0.62 |
| `natural` | **`True`** | 79 ms | `true` 0.93 · `false` 0.07 · conf 0.62 |
| `llm` | **`True`** | 66 ms | escribe texto: no da probabilidades |


#### 6. ¿Está pidiendo el cliente hablar con una persona?

> I have asked three times now. Can I please just talk to a real person?

**noul:**

- `true` — Pide explícitamente un agente humano
- `false` — No lo pide

**Se esperaba `True`.** Sí: «can I please just talk to a real person» lo pide de forma explícita.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 70 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `natural` | **`True`** | 52 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `llm` | **`True`** | 66 ms | escribe texto: no da probabilidades |


#### 7. ¿Está pidiendo el cliente hablar con una persona?

> ¿Podríais indicarme cómo cambiar mi dirección de facturación?

**noul:**

- `true` — Pide explícitamente un agente humano
- `false` — No lo pide

**Se esperaba `False`.** No: pregunta cómo cambiar una dirección, no pide una persona.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 77 ms | `true` 0.01 · `false` 0.99 · conf 0.95 |
| `natural` | **`False`** | 76 ms | `true` 0.01 · `false` 0.99 · conf 0.95 |
| `llm` | **`False`** | 95 ms | escribe texto: no da probabilidades |


#### 8. ¿Está pidiendo el cliente hablar con una persona?

> Quiero hablar con un responsable, esto no lo soluciona un bot.

**noul:**

- `true` — Pide explícitamente un agente humano
- `false` — No lo pide

**Se esperaba `True`.** Sí: «quiero hablar con un responsable» es explícito.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 74 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `natural` | **`True`** | 55 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `llm` | **`True`** | 91 ms | escribe texto: no da probabilidades |


#### 9. ¿Está pidiendo el cliente hablar con una persona?

> ¿Hay alguna forma de descargar la factura en PDF?

**noul:**

- `true` — Pide explícitamente un agente humano
- `false` — No lo pide

**Se esperaba `False`.** No: pregunta si se puede descargar una factura.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 56 ms | `true` 0.00 · `false` 1.00 · conf 0.97 |
| `natural` | **`False`** | 70 ms | `true` 0.00 · `false` 1.00 · conf 0.97 |
| `llm` | **`False`** | 76 ms | escribe texto: no da probabilidades |


#### 10. ¿Está pidiendo el cliente hablar con una persona?

> Pásenme con alguien de verdad, por favor.

**noul:**

- `true` — Pide explícitamente un agente humano
- `false` — No lo pide

**Se esperaba `True`.** Sí: «pásenme con alguien de verdad» es explícito.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 55 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `natural` | **`True`** | 68 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `llm` | **`True`** | 72 ms | escribe texto: no da probabilidades |


#### 11. ¿El cliente menciona un contacto anterior?

> Como ya comenté la semana pasada, el problema sigue exactamente igual.

**noul:**

- `true` — Menciona un intento o ticket previo
- `false` — No hay señal de contacto anterior

**Se esperaba `True`.** Sí: «como ya comenté la semana pasada» remite a un contacto anterior.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 78 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `natural` | **`True`** | 54 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `llm` | **`True`** | 108 ms | escribe texto: no da probabilidades |


#### 12. ¿El cliente menciona un contacto anterior?

> Acabo de registrarme y no encuentro la opción de cambiar el idioma.

**noul:**

- `true` — Menciona un intento o ticket previo
- `false` — No hay señal de contacto anterior

**Se esperaba `False`.** No: acaba de registrarse, es su primer contacto.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 77 ms | `true` 0.00 · `false` 1.00 · conf 0.97 |
| `natural` | **`False`** | 80 ms | `true` 0.00 · `false` 1.00 · conf 0.97 |
| `llm` | **`False`** | 101 ms | escribe texto: no da probabilidades |


#### 13. ¿El cliente menciona un contacto anterior?

> Es la cuarta vez que escribo sobre este mismo asunto.

**noul:**

- `true` — Menciona un intento o ticket previo
- `false` — No hay señal de contacto anterior

**Se esperaba `True`.** Sí: «la cuarta vez que escribo» cuenta los intentos previos.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 79 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `natural` | **`True`** | 53 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `llm` | **`True`** | 84 ms | escribe texto: no da probabilidades |


#### 14. ¿El cliente menciona un contacto anterior?

> Perdón por insistir, ya abrí un ticket el lunes con el número 8823.

**noul:**

- `true` — Menciona un intento o ticket previo
- `false` — No hay señal de contacto anterior

**Se esperaba `True`.** Sí: menciona un ticket previo con su número.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 84 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `natural` | **`True`** | 85 ms | `true` 1.00 · `false` 0.00 · conf 1.00 |
| `llm` | **`True`** | 92 ms | escribe texto: no da probabilidades |


#### 15. ¿El cliente menciona un contacto anterior?

> Necesito ayuda con la configuración inicial del dispositivo.

**noul:**

- `true` — Menciona un intento o ticket previo
- `false` — No hay señal de contacto anterior

**Se esperaba `False`.** No: pide ayuda con la configuración inicial, sin mencionar contactos anteriores.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 54 ms | `true` 0.00 · `false` 1.00 · conf 0.98 |
| `natural` | **`False`** | 67 ms | `true` 0.00 · `false` 1.00 · conf 0.98 |
| `llm` | **`False`** | 75 ms | escribe texto: no da probabilidades |


#### 16. ¿El mensaje contiene datos personales identificables?

> Me llamo Ana García, mi correo es ana.garcia@ejemplo.com y mi teléfono es 612345678.

**noul:**

- `true` — Contiene datos personales como nombre, correo o teléfono
- `false` — No contiene datos personales

**Se esperaba `True`.** Sí: nombre, correo y teléfono, los tres juntos.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 91 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `natural` | **`True`** | 95 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `llm` | **`True`** | 97 ms | escribe texto: no da probabilidades |


#### 17. ¿El mensaje contiene datos personales identificables?

> El pedido número 4471 sigue sin llegar y ya han pasado dos semanas.

**noul:**

- `true` — Contiene datos personales como nombre, correo o teléfono
- `false` — No contiene datos personales

**Se esperaba `False`.** No: un número de pedido no identifica a una persona.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 79 ms | `true` 0.00 · `false` 1.00 · conf 0.99 |
| `natural` | **`False`** | 67 ms | `true` 0.00 · `false` 1.00 · conf 0.99 |
| `llm` | **`False`** | 110 ms | escribe texto: no da probabilidades |


#### 18. ¿El mensaje contiene datos personales identificables?

> Adjunto mi DNI 12345678Z para verificar la titularidad de la cuenta.

**noul:**

- `true` — Contiene datos personales como nombre, correo o teléfono
- `false` — No contiene datos personales

**Se esperaba `True`.** Sí: un DNI es un dato identificativo directo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 69 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `natural` | **`True`** | 80 ms | `true` 1.00 · `false` 0.00 · conf 0.98 |
| `llm` | **`True`** | 105 ms | escribe texto: no da probabilidades |


#### 19. ¿El mensaje contiene datos personales identificables?

> La aplicación va lenta desde la última actualización.

**noul:**

- `true` — Contiene datos personales como nombre, correo o teléfono
- `false` — No contiene datos personales

**Se esperaba `False`.** No: describe un problema de rendimiento sin datos personales.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 78 ms | `true` 0.00 · `false` 1.00 · conf 0.98 |
| `natural` | **`False`** | 81 ms | `true` 0.00 · `false` 1.00 · conf 0.98 |
| `llm` | **`False`** | 90 ms | escribe texto: no da probabilidades |


#### 20. ¿El mensaje contiene datos personales identificables?

> Soy Juan Pérez y quiero cancelar mi suscripción.

**noul:**

- `true` — Contiene datos personales como nombre, correo o teléfono
- `false` — No contiene datos personales

**Se esperaba `True`.** Sí: nombre y apellidos («Soy Juan Pérez»).

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 75 ms | `true` 0.93 · `false` 0.07 · conf 0.63 |
| `natural` | **`True`** | 90 ms | `true` 0.93 · `false` 0.07 · conf 0.63 |
| `llm` | **`True`** | 88 ms | escribe texto: no da probabilidades |


#### 21. ¿El caso necesita acción humana inmediata?

> Se ha caído la base de datos de producción y ningún cliente puede acceder.

**noul:**

- `true` — Requiere que una persona actúe ya
- `false` — Puede gestionarse sin intervención humana

**Se esperaba `True`.** Sí: base de datos caída que afecta a todos los clientes.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 77 ms | `true` 0.99 · `false` 0.01 · conf 0.94 |
| `natural` | **`True`** | 78 ms | `true` 0.99 · `false` 0.01 · conf 0.94 |
| `llm` | **`True`** | 129 ms | escribe texto: no da probabilidades |


#### 22. ¿El caso necesita acción humana inmediata?

> ¿Podéis confirmarme si el envío incluye seguimiento?

**noul:**

- `true` — Requiere que una persona actúe ya
- `false` — Puede gestionarse sin intervención humana

**Se esperaba `False`.** No: es una consulta sobre seguimiento de envío.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 53 ms | `true` 0.02 · `false` 0.98 · conf 0.84 |
| `natural` | **`False`** | 65 ms | `true` 0.02 · `false` 0.98 · conf 0.84 |
| `llm` | **`False`** | 94 ms | escribe texto: no da probabilidades |


#### 23. ¿El caso necesita acción humana inmediata?

> Hay un cargo de 4.500 euros que no reconozco en mi tarjeta corporativa.

**noul:**

- `true` — Requiere que una persona actúe ya
- `false` — Puede gestionarse sin intervención humana

**Se esperaba `True`.** Sí: un cargo de 4.500 euros no reconocido hay que mirarlo ya.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 93 ms | `true` 0.91 · `false` 0.09 · conf 0.56 |
| `natural` | **`True`** | 83 ms | `true` 0.91 · `false` 0.09 · conf 0.56 |
| `llm` | **`True`** | 124 ms | escribe texto: no da probabilidades |


#### 24. ¿El caso necesita acción humana inmediata?

> Quería saber cuál es la política de devoluciones para productos abiertos.

**noul:**

- `true` — Requiere que una persona actúe ya
- `false` — Puede gestionarse sin intervención humana

**Se esperaba `False`.** No: pregunta por la política de devoluciones, sin caso abierto.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 75 ms | `true` 0.05 · `false` 0.95 · conf 0.72 |
| `natural` | **`False`** | 54 ms | `true` 0.05 · `false` 0.95 · conf 0.72 |
| `llm` | **`False`** | 129 ms | escribe texto: no da probabilidades |


#### 25. ¿El caso necesita acción humana inmediata?

> Un cliente ha denunciado una brecha de datos y hay que avisar a protección de datos hoy mismo.

**noul:**

- `true` — Requiere que una persona actúe ya
- `false` — Puede gestionarse sin intervención humana

**Se esperaba `True`.** Sí: brecha de datos con obligación de avisar a protección de datos.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 75 ms | `true` 1.00 · `false` 0.00 · conf 0.99 |
| `natural` | **`True`** | 80 ms | `true` 1.00 · `false` 0.00 · conf 0.99 |
| `llm` | **`True`** | 107 ms | escribe texto: no da probabilidades |


#### 26. ¿El caso es una consulta informativa sin acción pendiente?

> El usuario pregunta si el plan anual se puede pagar en dos plazos.

**noul:**

- `true` — Es solo una pregunta informativa
- `false` — Requiere una acción, no solo información

**Se esperaba `True`.** Sí: solo pregunta si se puede pagar en dos plazos; no pide que se haga nada.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** **← MAL** | 66 ms | `true` 0.40 · `false` 0.60 · conf 0.03 |
| `natural` | **`False`** **← MAL** | 72 ms | `true` 0.40 · `false` 0.60 · conf 0.03 |
| `llm` | **`True`** | 111 ms | escribe texto: no da probabilidades |


#### 27. ¿El caso es una consulta informativa sin acción pendiente?

> El usuario pide que le devolvamos el importe del pedido 3312.

**noul:**

- `true` — Es solo una pregunta informativa
- `false` — Requiere una acción, no solo información

**Se esperaba `False`.** No: pide expresamente que se devuelva el importe — hay una acción pendiente.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 74 ms | `true` 0.02 · `false` 0.98 · conf 0.88 |
| `natural` | **`False`** | 86 ms | `true` 0.02 · `false` 0.98 · conf 0.88 |
| `llm` | **`False`** | 127 ms | escribe texto: no da probabilidades |


#### 28. ¿El caso es una consulta informativa sin acción pendiente?

> ¿Cada cuánto se renueva automáticamente la suscripción?

**noul:**

- `true` — Es solo una pregunta informativa
- `false` — Requiere una acción, no solo información

**Se esperaba `True`.** Sí: pregunta la periodicidad de renovación, es información pura.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** **← MAL** | 83 ms | `true` 0.02 · `false` 0.98 · conf 0.88 |
| `natural` | **`False`** **← MAL** | 78 ms | `true` 0.02 · `false` 0.98 · conf 0.88 |
| `llm` | **`True`** | 105 ms | escribe texto: no da probabilidades |


#### 29. ¿El caso es una consulta informativa sin acción pendiente?

> Necesito que me emitan una factura rectificativa del mes pasado.

**noul:**

- `true` — Es solo una pregunta informativa
- `false` — Requiere una acción, no solo información

**Se esperaba `False`.** No: pide que se emita una factura rectificativa, es una acción.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 76 ms | `true` 0.04 · `false` 0.96 · conf 0.77 |
| `natural` | **`False`** | 62 ms | `true` 0.04 · `false` 0.96 · conf 0.77 |
| `llm` | **`False`** | 107 ms | escribe texto: no da probabilidades |


#### 30. ¿El caso es una consulta informativa sin acción pendiente?

> ¿Tenéis tienda física en Bogotá?

**noul:**

- `true` — Es solo una pregunta informativa
- `false` — Requiere una acción, no solo información

**Se esperaba `True`.** Sí: pregunta si hay tienda física, sin pedir ninguna acción.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** **← MAL** | 77 ms | `true` 0.44 · `false` 0.56 · conf 0.01 |
| `natural` | **`False`** **← MAL** | 90 ms | `true` 0.44 · `false` 0.56 · conf 0.01 |
| `llm` | **`True`** | 73 ms | escribe texto: no da probabilidades |


---

## Varias preguntas encadenadas (64)
Cada entrada lleva varias preguntas **en una sola petición**. El
tiempo es el de la petición completa: responde a todas de golpe.


### Frutas

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **72.5%** (29/40) | 91 ms | 91 ms | 104 ms | 0.58 |
| `natural` | **72.5%** (29/40) | 97 ms | 96 ms | 106 ms | 0.58 |
| `llm` | **75.0%** (30/40) | 346 ms | 352 ms | 396 ms | — |


### una manzana roja

Una manzana es **dulce** (no cítrica), de forma **redonda**, y al decir «roja» el color ya viene dado. Su piel es de **un solo tono**, sin manchas. Respecto al tamaño, una manzana entra en la categoría **mediana**.


#### ¿Qué sabor tiene?

> una manzana roja

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 71 ms | `citrico` 0.00 · `dulce` 1.00 · `insipido` 0.00 · conf 1.00 |
| `natural` | **`dulce`** | 106 ms | `citrico` 0.00 · `dulce` 1.00 · `insipido` 0.00 · conf 1.00 |
| `llm` | **`dulce`** | 341 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> una manzana roja

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `redonda`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`redonda`** | 71 ms | `redonda` 0.99 · `alargada` 0.00 · `irregular` 0.00 · conf 0.97 |
| `natural` | **`redonda`** | 106 ms | `redonda` 0.99 · `alargada` 0.00 · `irregular` 0.00 · conf 0.97 |
| `llm` | **`redonda`** | 341 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> una manzana roja

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `rojo`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`rojo`** | 71 ms | `rojo` 1.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 0.00 · conf 1.00 |
| `natural` | **`rojo`** | 106 ms | `rojo` 1.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 0.00 · conf 1.00 |
| `llm` | **`rojo`** | 341 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> una manzana roja

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 71 ms | `true` 0.95 · `false` 0.05 · conf 0.71 |
| `natural` | **`True`** | 106 ms | `true` 0.95 · `false` 0.05 · conf 0.71 |
| `llm` | **`True`** | 341 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> una manzana roja

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `1`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 71 ms |  · conf 0.30 |
| `natural` | **`1.0`** | 106 ms |  · conf 0.30 |
| `llm` | **`1.0`** | 341 ms | escribe texto: no da probabilidades |

*La petición completa tarda 71 ms.*


### un plátano amarillo maduro

Un plátano maduro es **dulce**; su forma es **alargada**, no esférica. El amarillo lo da el enunciado, y la piel de un plátano maduro es de **tono uniforme** (las manchas aparecen al pasarse). **Tamaño mediano**.


#### ¿Qué sabor tiene?

> un plátano amarillo maduro

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 91 ms | `citrico` 0.00 · `dulce` 1.00 · `insipido` 0.00 · conf 1.00 |
| `natural` | **`dulce`** | 105 ms | `citrico` 0.00 · `dulce` 1.00 · `insipido` 0.00 · conf 1.00 |
| `llm` | **`dulce`** | 359 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> un plátano amarillo maduro

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `alargada`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`redonda`** **← MAL** | 91 ms | `redonda` 0.90 · `alargada` 0.09 · `irregular` 0.00 · conf 0.69 |
| `natural` | **`redonda`** **← MAL** | 105 ms | `redonda` 0.90 · `alargada` 0.09 · `irregular` 0.00 · conf 0.69 |
| `llm` | **`redonda`** **← MAL** | 359 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> un plátano amarillo maduro

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `amarillo`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`amarillo`** | 91 ms | `rojo` 0.00 · `amarillo` 1.00 · `verde` 0.00 · `naranja` 0.00 · conf 1.00 |
| `natural` | **`amarillo`** | 105 ms | `rojo` 0.00 · `amarillo` 1.00 · `verde` 0.00 · `naranja` 0.00 · conf 1.00 |
| `llm` | **`amarillo`** | 359 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> un plátano amarillo maduro

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 91 ms | `true` 0.79 · `false` 0.21 · conf 0.27 |
| `natural` | **`True`** | 105 ms | `true` 0.79 · `false` 0.21 · conf 0.27 |
| `llm` | **`True`** | 359 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> un plátano amarillo maduro

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `1`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** **← MAL** | 91 ms |  · conf 0.47 |
| `natural` | **`2.0`** **← MAL** | 105 ms |  · conf 0.47 |
| `llm` | **`2.0`** **← MAL** | 359 ms | escribe texto: no da probabilidades |

*La petición completa tarda 91 ms.*


### un limón verde

El limón es el caso **cítrico** por antonomasia. Su forma es **redonda** u ovalada, el verde viene dado, la piel es **uniforme**, y es **pequeño**.


#### ¿Qué sabor tiene?

> un limón verde

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `citrico`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`citrico`** | 96 ms | `citrico` 1.00 · `dulce` 0.00 · `insipido` 0.00 · conf 1.00 |
| `natural` | **`citrico`** | 71 ms | `citrico` 1.00 · `dulce` 0.00 · `insipido` 0.00 · conf 1.00 |
| `llm` | **`citrico`** | 340 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> un limón verde

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `redonda`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`redonda`** | 96 ms | `redonda` 0.98 · `alargada` 0.01 · `irregular` 0.01 · conf 0.91 |
| `natural` | **`redonda`** | 71 ms | `redonda` 0.98 · `alargada` 0.01 · `irregular` 0.01 · conf 0.91 |
| `llm` | **`redonda`** | 340 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> un limón verde

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `verde`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`verde`** | 96 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 1.00 · `naranja` 0.00 · conf 1.00 |
| `natural` | **`verde`** | 71 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 1.00 · `naranja` 0.00 · conf 1.00 |
| `llm` | **`verde`** | 340 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> un limón verde

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 96 ms | `true` 0.66 · `false` 0.34 · conf 0.07 |
| `natural` | **`True`** | 71 ms | `true` 0.66 · `false` 0.34 · conf 0.07 |
| `llm` | **`True`** | 340 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> un limón verde

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `0`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 96 ms |  · conf 0.08 |
| `natural` | **`0.0`** | 71 ms |  · conf 0.08 |
| `llm` | **`1.0`** **← MAL** | 340 ms | escribe texto: no da probabilidades |

*La petición completa tarda 96 ms.*


### una naranja

La naranja es **cítrica** aunque sea dulce al paladar: la pregunta es por el sabor ácido característico. Es **redonda**, **naranja** por definición, de piel **uniforme** y **mediana**.


#### ¿Qué sabor tiene?

> una naranja

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `citrico`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** **← MAL** | 90 ms | `citrico` 0.05 · `dulce` 0.95 · `insipido` 0.00 · conf 0.83 |
| `natural` | **`dulce`** **← MAL** | 94 ms | `citrico` 0.05 · `dulce` 0.95 · `insipido` 0.00 · conf 0.83 |
| `llm` | **`citrico`** | 344 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> una naranja

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `redonda`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`redonda`** | 90 ms | `redonda` 0.97 · `alargada` 0.03 · `irregular` 0.00 · conf 0.85 |
| `natural` | **`redonda`** | 94 ms | `redonda` 0.97 · `alargada` 0.03 · `irregular` 0.00 · conf 0.85 |
| `llm` | **`redonda`** | 344 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> una naranja

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `naranja`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`naranja`** | 90 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 1.00 · conf 0.99 |
| `natural` | **`naranja`** | 94 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 1.00 · conf 0.99 |
| `llm` | **`naranja`** | 344 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> una naranja

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 90 ms | `true` 0.84 · `false` 0.16 · conf 0.37 |
| `natural` | **`True`** | 94 ms | `true` 0.84 · `false` 0.16 · conf 0.37 |
| `llm` | **`True`** | 344 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> una naranja

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `1`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** **← MAL** | 90 ms |  · conf 0.62 |
| `natural` | **`2.0`** **← MAL** | 94 ms |  · conf 0.62 |
| `llm` | **`1.0`** | 344 ms | escribe texto: no da probabilidades |

*La petición completa tarda 90 ms.*


### una sandía partida por la mitad

La sandía es **dulce** (de ahí que se coma como postre) y **redonda**, pero al decir que está partida vemos el exterior verde y el interior rojo: su color **no es de un solo tono**. Es **grande**.


#### ¿Qué sabor tiene?

> una sandía partida por la mitad

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 92 ms | `citrico` 0.31 · `dulce` 0.69 · `insipido` 0.00 · conf 0.44 |
| `natural` | **`dulce`** | 105 ms | `citrico` 0.31 · `dulce` 0.69 · `insipido` 0.00 · conf 0.44 |
| `llm` | **`dulce`** | 347 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> una sandía partida por la mitad

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `redonda`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`alargada`** **← MAL** | 92 ms | `redonda` 0.24 · `alargada` 0.68 · `irregular` 0.08 · conf 0.27 |
| `natural` | **`alargada`** **← MAL** | 105 ms | `redonda` 0.24 · `alargada` 0.68 · `irregular` 0.08 · conf 0.27 |
| `llm` | **`redonda`** | 347 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> una sandía partida por la mitad

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `verde`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`amarillo`** **← MAL** | 92 ms | `rojo` 0.00 · `amarillo` 0.84 · `verde` 0.07 · `naranja` 0.08 · conf 0.60 |
| `natural` | **`amarillo`** **← MAL** | 105 ms | `rojo` 0.00 · `amarillo` 0.84 · `verde` 0.07 · `naranja` 0.08 · conf 0.60 |
| `llm` | **`rojo`** **← MAL** | 347 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> una sandía partida por la mitad

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `False`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 92 ms | `true` 0.24 · `false` 0.76 · conf 0.20 |
| `natural` | **`False`** | 105 ms | `true` 0.24 · `false` 0.76 · conf 0.20 |
| `llm` | **`True`** **← MAL** | 347 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> una sandía partida por la mitad

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `2`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 92 ms |  · conf 0.12 |
| `natural` | **`2.0`** | 105 ms |  · conf 0.12 |
| `llm` | **`1.0`** **← MAL** | 347 ms | escribe texto: no da probabilidades |

*La petición completa tarda 92 ms.*


### un racimo de uvas moradas

Las uvas son **dulces**; cada uva es **redonda** aunque el racimo no lo sea, y el enunciado fija el **morado**. El color es **uniforme** y cada uva es **pequeña**.


#### ¿Qué sabor tiene?

> un racimo de uvas moradas

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 99 ms | `citrico` 0.03 · `dulce` 0.77 · `insipido` 0.20 · conf 0.44 |
| `natural` | **`dulce`** | 100 ms | `citrico` 0.03 · `dulce` 0.77 · `insipido` 0.20 · conf 0.44 |
| `llm` | **`dulce`** | 348 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> un racimo de uvas moradas

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `redonda`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`irregular`** **← MAL** | 99 ms | `redonda` 0.43 · `alargada` 0.13 · `irregular` 0.44 · conf 0.10 |
| `natural` | **`irregular`** **← MAL** | 100 ms | `redonda` 0.43 · `alargada` 0.13 · `irregular` 0.44 · conf 0.10 |
| `llm` | **`redonda`** | 348 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> un racimo de uvas moradas

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `morado` — Morado o violeta

**Se esperaba `morado`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`morado`** | 99 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 0.00 · `morado` 1.00 · conf 1.00 |
| `natural` | **`morado`** | 100 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 0.00 · `morado` 1.00 · conf 1.00 |
| `llm` | **`morado`** | 348 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> un racimo de uvas moradas

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** **← MAL** | 99 ms | `true` 0.44 · `false` 0.56 · conf 0.01 |
| `natural` | **`False`** **← MAL** | 100 ms | `true` 0.44 · `false` 0.56 · conf 0.01 |
| `llm` | **`True`** | 348 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> un racimo de uvas moradas

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `0`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** **← MAL** | 99 ms |  · conf 0.01 |
| `natural` | **`1.0`** **← MAL** | 100 ms |  · conf 0.01 |
| `llm` | **`1.0`** **← MAL** | 348 ms | escribe texto: no da probabilidades |

*La petición completa tarda 99 ms.*


### una fresa roja con las hojas verdes

La fresa es **dulce**; su forma es **irregular** (no es una esfera ni un alargado limpio, tiene el cuello ancho). El rojo viene dado, pero las hojas verdes hacen que el conjunto **no sea de un solo tono**. Es **pequeña**.


#### ¿Qué sabor tiene?

> una fresa roja con las hojas verdes

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 104 ms | `citrico` 0.01 · `dulce` 0.98 · `insipido` 0.00 · conf 0.91 |
| `natural` | **`dulce`** | 93 ms | `citrico` 0.01 · `dulce` 0.98 · `insipido` 0.00 · conf 0.91 |
| `llm` | **`dulce`** | 337 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> una fresa roja con las hojas verdes

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `irregular`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`redonda`** **← MAL** | 104 ms | `redonda` 0.87 · `alargada` 0.02 · `irregular` 0.11 · conf 0.59 |
| `natural` | **`redonda`** **← MAL** | 93 ms | `redonda` 0.87 · `alargada` 0.02 · `irregular` 0.11 · conf 0.59 |
| `llm` | **`redonda`** **← MAL** | 337 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> una fresa roja con las hojas verdes

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `rojo`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`rojo`** | 104 ms | `rojo` 1.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 0.00 · conf 0.98 |
| `natural` | **`rojo`** | 93 ms | `rojo` 1.00 · `amarillo` 0.00 · `verde` 0.00 · `naranja` 0.00 · conf 0.98 |
| `llm` | **`rojo`** | 337 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> una fresa roja con las hojas verdes

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `False`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** **← MAL** | 104 ms | `true` 0.89 · `false` 0.11 · conf 0.51 |
| `natural` | **`True`** **← MAL** | 93 ms | `true` 0.89 · `false` 0.11 · conf 0.51 |
| `llm` | **`True`** **← MAL** | 337 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> una fresa roja con las hojas verdes

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `0`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 104 ms |  · conf 0.11 |
| `natural` | **`0.0`** | 93 ms |  · conf 0.11 |
| `llm` | **`1.0`** **← MAL** | 337 ms | escribe texto: no da probabilidades |

*La petición completa tarda 104 ms.*


### una pera verde alargada

Una pera es **dulce**, de forma **alargada**, y el enunciado fija el **verde**. Su piel es **uniforme** y su tamaño es **mediano**.


#### ¿Qué sabor tiene?

> una pera verde alargada

**choice:**

- `citrico` — Ácido, como el limón
- `dulce` — Dulce, como el azúcar
- `insipido` — Sin sabor apreciable

**Se esperaba `dulce`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`dulce`** | 84 ms | `citrico` 0.03 · `dulce` 0.96 · `insipido` 0.01 · conf 0.82 |
| `natural` | **`dulce`** | 93 ms | `citrico` 0.03 · `dulce` 0.96 · `insipido` 0.01 · conf 0.82 |
| `llm` | **`dulce`** | 396 ms | escribe texto: no da probabilidades |


#### ¿Qué forma tiene?

> una pera verde alargada

**choice:**

- `redonda` — Esférica o casi esférica
- `alargada` — Más larga que ancha
- `irregular` — Sin forma definida

**Se esperaba `alargada`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`alargada`** | 84 ms | `redonda` 0.00 · `alargada` 1.00 · `irregular` 0.00 · conf 1.00 |
| `natural` | **`alargada`** | 93 ms | `redonda` 0.00 · `alargada` 1.00 · `irregular` 0.00 · conf 1.00 |
| `llm` | **`alargada`** | 396 ms | escribe texto: no da probabilidades |


#### ¿De qué color es?

> una pera verde alargada

**choice:**

- `rojo` — Rojo
- `amarillo` — Amarillo
- `verde` — Verde
- `naranja` — Naranja

**Se esperaba `verde`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`verde`** | 84 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 1.00 · `naranja` 0.00 · conf 1.00 |
| `natural` | **`verde`** | 93 ms | `rojo` 0.00 · `amarillo` 0.00 · `verde` 1.00 · `naranja` 0.00 · conf 1.00 |
| `llm` | **`verde`** | 396 ms | escribe texto: no da probabilidades |


#### ¿Su color es uniforme, de un solo tono?

> una pera verde alargada

**noul:**

- `true` — Un solo tono en toda la superficie
- `false` — Varios tonos o manchas

**Se esperaba `True`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 84 ms | `true` 0.57 · `false` 0.43 · conf 0.02 |
| `natural` | **`True`** | 93 ms | `true` 0.57 · `false` 0.43 · conf 0.02 |
| `llm` | **`True`** | 396 ms | escribe texto: no da probabilidades |


#### ¿Qué tamaño tiene?

> una pera verde alargada

**score:**

- `0` — Pequeño
- `1` — Mediano
- `2` — Grande

**Se esperaba `1`.** 

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 84 ms |  · conf 0.10 |
| `natural` | **`1.0`** | 93 ms |  · conf 0.10 |
| `llm` | **`1.0`** | 396 ms | escribe texto: no da probabilidades |

*La petición completa tarda 84 ms.*


### Tickets

| modo | acierto | p50 | media | máx | confianza media |
|---|---|---|---|---|---|
| `tipado` | **79.2%** (19/24) | 96 ms | 95 ms | 102 ms | 0.68 |
| `natural` | **79.2%** (19/24) | 95 ms | 94 ms | 101 ms | 0.68 |
| `llm` | **37.5%** (9/24) | 290 ms | 283 ms | 311 ms | — |


### Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el dinero antes del viernes.


#### ¿Qué equipo debe atenderlo?

> Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el dinero antes del viernes.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `billing`.** Un cobro duplicado con petición de devolución es facturación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 96 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `natural` | **`billing`** | 101 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 1.00 |
| `llm` | **`general`** **← MAL** | 291 ms | escribe texto: no da probabilidades |


#### ¿Qué urgencia tiene?

> Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el dinero antes del viernes.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `1`.** **Aquí el modelo y yo discrepamos.** Yo esperaba nivel 1 («conviene atenderlo hoy»): es dinero, pero un cobro duplicado no tumba el negocio. El modelo responde 2 porque lee «antes del viernes» como presión. Es discutible, y por eso está marcado como fallo en vez de esconderse.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** **← MAL** | 96 ms |  · conf 0.49 |
| `natural` | **`2.0`** **← MAL** | 101 ms |  · conf 0.49 |
| `llm` | **`2.0`** **← MAL** | 291 ms | escribe texto: no da probabilidades |


#### ¿Conviene que lo revise una persona antes de actuar?

> Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el dinero antes del viernes.

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `True`.** Yo esperaba que sí, por ser dinero y con fecha límite. El modelo dice que no **con confianza 0,024** — un empate técnico: no sabe. Es la clase de caso donde el umbral de confianza debería mandar a revisión humana.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** **← MAL** | 96 ms | `true` 0.38 · `false` 0.62 · conf 0.04 |
| `natural` | **`False`** **← MAL** | 101 ms | `true` 0.38 · `false` 0.62 · conf 0.04 |
| `llm` | **`False`** **← MAL** | 291 ms | escribe texto: no da probabilidades |


#### ¿Qué tono tiene el cliente?

> Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el dinero antes del viernes.

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `calmado`.** El texto no insulta ni usa mayúsculas ni reprocha: es una petición firme pero **tranquila**. El modelo lee «necesito… antes del viernes» como enfado. Segunda discrepancia del mismo caso.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`molesto`** **← MAL** | 96 ms | `calmado` 0.11 · `molesto` 0.89 · conf 0.49 |
| `natural` | **`molesto`** **← MAL** | 101 ms | `calmado` 0.11 · `molesto` 0.89 · conf 0.49 |
| `llm` | **`molesto`** **← MAL** | 291 ms | escribe texto: no da probabilidades |

*La petición completa tarda 96 ms.*


### La aplicación no arranca desde esta mañana y toda la plantilla está parada sin poder facturar. Esto es inaceptable.


#### ¿Qué equipo debe atenderlo?

> La aplicación no arranca desde esta mañana y toda la plantilla está parada sin poder facturar. Esto es inaceptable.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `technical`.** «No arranca» es un fallo de la aplicación: técnico.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`technical`** | 96 ms | `billing` 0.02 · `technical` 0.98 · `general` 0.00 · conf 0.91 |
| `natural` | **`technical`** | 82 ms | `billing` 0.02 · `technical` 0.98 · `general` 0.00 · conf 0.91 |
| `llm` | **`technical`** | 311 ms | escribe texto: no da probabilidades |


#### ¿Qué urgencia tiene?

> La aplicación no arranca desde esta mañana y toda la plantilla está parada sin poder facturar. Esto es inaceptable.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `2`.** Nivel 2 claro: nadie puede trabajar.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 96 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 82 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 311 ms | escribe texto: no da probabilidades |


#### ¿Conviene que lo revise una persona antes de actuar?

> La aplicación no arranca desde esta mañana y toda la plantilla está parada sin poder facturar. Esto es inaceptable.

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `True`.** Sí: una caída total con impacto económico no se resuelve automáticamente.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 96 ms | `true` 0.62 · `false` 0.38 · conf 0.04 |
| `natural` | **`True`** | 82 ms | `true` 0.62 · `false` 0.38 · conf 0.04 |
| `llm` | **`True`** | 311 ms | escribe texto: no da probabilidades |


#### ¿Qué tono tiene el cliente?

> La aplicación no arranca desde esta mañana y toda la plantilla está parada sin poder facturar. Esto es inaceptable.

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `molesto`.** «Esto es inaceptable» es un reproche explícito: molesto.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`molesto`** | 96 ms | `calmado` 0.00 · `molesto` 1.00 · conf 1.00 |
| `natural` | **`molesto`** | 82 ms | `calmado` 0.00 · `molesto` 1.00 · conf 1.00 |
| `llm` | **`molesto`** | 311 ms | escribe texto: no da probabilidades |

*La petición completa tarda 96 ms.*


### ¿Cuál es vuestro horario de atención telefónica los sábados?


#### ¿Qué equipo debe atenderlo?

> ¿Cuál es vuestro horario de atención telefónica los sábados?

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `general`.** Consulta informativa sin incidencia: general.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`general`** | 93 ms | `billing` 0.01 · `technical` 0.01 · `general` 0.98 · conf 0.92 |
| `natural` | **`general`** | 94 ms | `billing` 0.01 · `technical` 0.01 · `general` 0.98 · conf 0.92 |
| `llm` | **no se pudo leer** | 248 ms | — |


#### ¿Qué urgencia tiene?

> ¿Cuál es vuestro horario de atención telefónica los sábados?

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `0`.** Nivel 0: saber un horario puede esperar.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`0.0`** | 93 ms |  · conf 0.60 |
| `natural` | **`0.0`** | 94 ms |  · conf 0.60 |
| `llm` | **no se pudo leer** | 248 ms | — |


#### ¿Conviene que lo revise una persona antes de actuar?

> ¿Cuál es vuestro horario de atención telefónica los sábados?

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `False`.** No: es información que se puede dar sin intervención humana.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 93 ms | `true` 0.06 · `false` 0.94 · conf 0.67 |
| `natural` | **`False`** | 94 ms | `true` 0.06 · `false` 0.94 · conf 0.67 |
| `llm` | **no se pudo leer** | 248 ms | — |


#### ¿Qué tono tiene el cliente?

> ¿Cuál es vuestro horario de atención telefónica los sábados?

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `calmado`.** Pregunta neutra y educada: tranquilo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`calmado`** | 93 ms | `calmado` 0.99 · `molesto` 0.01 · conf 0.94 |
| `natural` | **`calmado`** | 94 ms | `calmado` 0.99 · `molesto` 0.01 · conf 0.94 |
| `llm` | **no se pudo leer** | 248 ms | — |

*La petición completa tarda 93 ms.*


### El botón de exportar no hace nada en Safari. En Chrome sí funciona.


#### ¿Qué equipo debe atenderlo?

> El botón de exportar no hace nada en Safari. En Chrome sí funciona.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `technical`.** Un botón que no responde: técnico.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`technical`** | 87 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 0.98 |
| `natural` | **`technical`** | 93 ms | `billing` 0.00 · `technical` 1.00 · `general` 0.00 · conf 0.98 |
| `llm` | **`general`** **← MAL** | 306 ms | escribe texto: no da probabilidades |


#### ¿Qué urgencia tiene?

> El botón de exportar no hace nada en Safari. En Chrome sí funciona.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `1`.** Nivel 1: hay alternativa (Chrome), así que no es bloqueante.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** | 87 ms |  · conf 0.37 |
| `natural` | **`1.0`** | 93 ms |  · conf 0.37 |
| `llm` | **`1.0`** | 306 ms | escribe texto: no da probabilidades |


#### ¿Conviene que lo revise una persona antes de actuar?

> El botón de exportar no hace nada en Safari. En Chrome sí funciona.

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `False`.** No: el propio texto indica que hay forma de seguir.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 87 ms | `true` 0.29 · `false` 0.71 · conf 0.13 |
| `natural` | **`False`** | 93 ms | `true` 0.29 · `false` 0.71 · conf 0.13 |
| `llm` | **`False`** | 306 ms | escribe texto: no da probabilidades |


#### ¿Qué tono tiene el cliente?

> El botón de exportar no hace nada en Safari. En Chrome sí funciona.

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `calmado`.** Describe el fallo sin carga emocional: tranquilo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`molesto`** **← MAL** | 87 ms | `calmado` 0.07 · `molesto` 0.93 · conf 0.65 |
| `natural` | **`molesto`** **← MAL** | 93 ms | `calmado` 0.07 · `molesto` 0.93 · conf 0.65 |
| `llm` | **`molesto`** **← MAL** | 306 ms | escribe texto: no da probabilidades |

*La petición completa tarda 87 ms.*


### Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con un responsable.


#### ¿Qué equipo debe atenderlo?

> Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con un responsable.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `billing`.** Un reembolso es facturación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 96 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 0.98 |
| `natural` | **`billing`** | 97 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 0.98 |
| `llm` | **`general`** **← MAL** | 290 ms | escribe texto: no da probabilidades |


#### ¿Qué urgencia tiene?

> Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con un responsable.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `2`.** Nivel 2: tres semanas sin respuesta y una petición explícita de escalada.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`2.0`** | 96 ms |  · conf 1.00 |
| `natural` | **`2.0`** | 97 ms |  · conf 1.00 |
| `llm` | **`2.0`** | 290 ms | escribe texto: no da probabilidades |


#### ¿Conviene que lo revise una persona antes de actuar?

> Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con un responsable.

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `True`.** Sí, y además lo pide el propio cliente.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`True`** | 96 ms | `true` 0.72 · `false` 0.28 · conf 0.15 |
| `natural` | **`True`** | 97 ms | `true` 0.72 · `false` 0.28 · conf 0.15 |
| `llm` | **`True`** | 290 ms | escribe texto: no da probabilidades |


#### ¿Qué tono tiene el cliente?

> Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con un responsable.

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `molesto`.** Tres semanas de silencio y una exigencia: molesto.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`molesto`** | 96 ms | `calmado` 0.00 · `molesto` 1.00 · conf 1.00 |
| `natural` | **`molesto`** | 97 ms | `calmado` 0.00 · `molesto` 1.00 · conf 1.00 |
| `llm` | **`molesto`** | 290 ms | escribe texto: no da probabilidades |

*La petición completa tarda 96 ms.*


### Quería saber si el plan anual se puede pagar en dos plazos.


#### ¿Qué equipo debe atenderlo?

> Quería saber si el plan anual se puede pagar en dos plazos.

**choice:**

- `billing` — Pagos, cargos y reembolsos
- `technical` — Errores de la aplicación
- `general` — Otras consultas

**Se esperaba `billing`.** Condiciones de pago: facturación.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`billing`** | 102 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 0.99 |
| `natural` | **`billing`** | 98 ms | `billing` 1.00 · `technical` 0.00 · `general` 0.00 · conf 0.99 |
| `llm` | **no se pudo leer** | 255 ms | — |


#### ¿Qué urgencia tiene?

> Quería saber si el plan anual se puede pagar en dos plazos.

**score:**

- `0` — Puede esperar
- `1` — Conviene atenderlo hoy
- `2` — Necesita acción inmediata

**Se esperaba `0`.** Nivel 0: es una consulta previa, no hay nada en marcha.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`1.0`** **← MAL** | 102 ms |  · conf 0.47 |
| `natural` | **`1.0`** **← MAL** | 98 ms |  · conf 0.47 |
| `llm` | **no se pudo leer** | 255 ms | — |


#### ¿Conviene que lo revise una persona antes de actuar?

> Quería saber si el plan anual se puede pagar en dos plazos.

**noul:**

- `true` — Sí, conviene revisión humana
- `false` — No hace falta, puede automatizarse

**Se esperaba `False`.** No: es información que el sistema puede dar solo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`False`** | 102 ms | `true` 0.14 · `false` 0.86 · conf 0.43 |
| `natural` | **`False`** | 98 ms | `true` 0.14 · `false` 0.86 · conf 0.43 |
| `llm` | **no se pudo leer** | 255 ms | — |


#### ¿Qué tono tiene el cliente?

> Quería saber si el plan anual se puede pagar en dos plazos.

**choice:**

- `calmado` — Tranquilo y objetivo
- `molesto` — Visiblemente enfadado

**Se esperaba `calmado`.** Pregunta cortés: tranquilo.

| modelo | eligió | tiempo | probabilidad de cada opción |
|---|---|---|---|
| `tipado` | **`calmado`** | 102 ms | `calmado` 1.00 · `molesto` 0.00 · conf 1.00 |
| `natural` | **`calmado`** | 98 ms | `calmado` 1.00 · `molesto` 0.00 · conf 1.00 |
| `llm` | **no se pudo leer** | 255 ms | — |

*La petición completa tarda 102 ms.*


---

## Cómo leerlo

- **`← MAL`** — no coincide con lo que se esperaba. Si no aparece, acertó.
- **`conf`** — lo repartida que está la probabilidad: 1,00 es un solo pico,
  cerca de 0 es un empate. En PROBABILITY no hace falta, el número ya lo dice.
- **`escribe texto`** — el modo `llm` no da probabilidades: redacta, y de ahí
  se lee una sola respuesta. **`no se pudo leer`** es que ni eso.
- El tiempo es el de la petición HTTP, con la caché ya caliente.

---

*Documento generado por `detalle.py` a partir de `results/modos.json` y
`results/multi.json`. Para comprobar que las cifras siguen cuadrando con los
datos: `python verificar.py`.*

