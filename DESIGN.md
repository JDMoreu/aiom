---
name: AIOM
description: Un modelo, dos formas de preguntar — valores o prosa
colors:
  regla: "#1B4D3E"
  regla-claro: "#2A6A55"
  regla-borde: "rgba(0, 0, 0, 0.28)"
  regla-texto: "rgba(255, 255, 255, 0.78)"
  regla-punto: "rgba(255, 255, 255, 0.4)"
  cursor: "#B4321F"
  panel: "#E4E5DF"
  papel: "#FAFAF7"
  papel-hundido: "#F2F3EE"
  tinta: "#1A1C1B"
  apagado: "#4A4F49"
  tenue: "#606560"
  hairline: "#CFD1C9"
  hairline-fuerte: "#B9BDB3"
  estado-ok: "#1B6B4A"
  estado-ok-claro: "#7BE0B0"
  estado-aviso: "#8A6412"
  estado-malo: "#A32B22"
  estado-malo-claro: "#FF9A8F"
  estado-malo-texto: "#7E1F18"
  tipo-choice: "#1B4D3E"
  tipo-score: "#1E3A6E"
  tipo-noul: "#7A3E12"
typography:
  display:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  cifra:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  title:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0.02em"
  ui:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  medida:
    fontFamily: "ui-monospace, SFMono-Regular, 'Cascadia Mono', Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Bahnschrift, 'DIN Alternate', 'Roboto Condensed', 'Arial Narrow', system-ui, sans-serif"
    fontSize: "11.5px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0.14em"
rounded:
  plano: "0"
  filo: "2px"
  placa: "3px"
  circulo: "50%"
  pastilla: "99px"
spacing:
  xs: "8px"
  sm: "14px"
  md: "18px"
  lg: "26px"
  xl: "60px"
components:
  accion-principal:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.regla}"
    rounded: "{rounded.filo}"
    padding: "9px 22px"
    typography: "{typography.label}"
  accion-secundaria:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.filo}"
    padding: "7px 13px"
  accion-en-el-armazon:
    backgroundColor: "{colors.regla}"
    textColor: "{colors.papel}"
    rounded: "{rounded.filo}"
    padding: "7px 13px"
  placa-lectura:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.placa}"
    padding: "14px"
  campo:
    backgroundColor: "{colors.papel-hundido}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.filo}"
    padding: "7px 10px"
  etiqueta-de-tipo:
    backgroundColor: "{colors.tipo-choice}"
    textColor: "{colors.papel}"
    rounded: "{rounded.filo}"
    padding: "2px 7px"
    typography: "{typography.label}"
  pestana-activa:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.filo}"
    padding: "10px 18px"
---

# Design System: AIOM

## Overview

**Creative North Star: "La Regla de Cálculo"**

Esta interfaz no es un panel de control ni una consola: es **un instrumento de
lectura**. La idea que la gobierna es que una respuesta no se «muestra», se **lee** —
como se lee una medida en una regla graduada, con su marca, su escala y el margen de
duda a la vista. De ahí sale todo lo demás: un fondo de panel claro porque los
instrumentos de precisión se leen con luz, una tinta que parece grabada y no impresa
por una pantalla, y una densidad alta, porque un instrumento de medida tiene muchas
graduaciones y ninguna sobra.

El mundo entra por **cuatro cosas y solo cuatro**: el tipo, la paleta, la densidad y
**una** marca. Nunca por la disposición ni por los controles: las pestañas, el
formulario, los botones y los campos son los de siempre en la web, y eso es
deliberado. Un instrumento disfrazado de instrumento sería un disfraz; lo que se
hereda es la manera de leer, no el objeto.

La marca —el movimiento firma— es **la escala graduada con su cursor**: cada respuesta
se dibuja como un trazo por opción cuya altura es su probabilidad, el trazo elegido
entintado en verde, un cursor rojo encima señalando la marca, y una línea base con
graduaciones dibujadas. Es lo único que esta interfaz hace de una forma que no se ve
en otro sitio, y es lo que hace que las probabilidades se entiendan sin leer un número.

**Key Characteristics:**

- Panel claro de instrumento con el armazón en verde de escala profundo.
- Tinta grabada, cifras tabulares, etiquetas en versalitas muy espaciadas.
- Densidad alta y deliberada: es una superficie de medida, no una landing.
- Un solo movimiento firma: la marca sobre la escala graduada.
- Bordes de filo (2px), sin sombras difusas, sin brillos, sin desenfoques.

## Colors

La paleta es de instrumento: un verde profundo que compromete el armazón, un rojo de
señal reservado para una sola cosa, y una escala de grises verdosos que se leen como
un panel pintado. Ninguno de los tres colores de estado compite con ellos, porque
aparecen poco.

### Primary

- **Verde de Escala** (#1B4D3E): el color comprometido. Ocupa el armazón superior a
  todo el ancho, y es también el color de la acción principal y del trazo elegido en
  cada escala. Es lo que hace que la pantalla tenga dueño.
- **Verde de Escala Claro** (#2A6A55): solo para el estado *hover* de lo que ya es
  verde. No aparece nunca como color propio.

### Secondary

- **Rojo de Cursor** (#B4321F): **la marca**. Es el cursor de la escala graduada, el
  foco del teclado y el borde del multiplicador de la medida. Nada más
  lo usa: su rareza es lo que lo hace leer como una aguja y no como un adorno.

### Tertiary

- **Azul de Escala** (#1E3A6E) para las preguntas de tipo `score`.
- **Ocre de Escala** (#7A3E12) para las de tipo `noul`.
- **Verde de Escala** para las de tipo `choice`.
  Los tres códigos vienen de la regla de cálculo, que marca sus escalas con bandas de
  color para que se encuentren de un vistazo. Aquí el color **informa**: dice de qué
  tipo es cada pregunta, en la etiqueta de la placa y en el selector de su bloque.

### Neutral

- **Tinta Grabada** (#1A1C1B): todo el texto principal. Nunca negro puro.
- **Secundario** (#4A4F49): texto de apoyo, valores de probabilidad, cifras menores.
- **Terciario** (#606560): etiquetas y rótulos. Es el gris más claro que **aún pasa
  4.5:1 sobre el panel** (#E4E5DF, 4.70:1); más claro incumple y no se usa.
- **Panel de Instrumento** (#E4E5DF): el fondo de la página.
- **Cara de Regla** (#FAFAF7): las placas donde se lee, y el texto sobre el verde. Es
  el blanco del instrumento; el blanco puro (#FFF) **no se usa en ningún sitio**.
- **Cara de Regla Hundida** (#F2F3EE): los campos de escritura y las cabeceras de placa.
- **Hairline** (#CFD1C9) y **Hairline Fuerte** (#B9BDB3): las líneas de 1px y las
  graduaciones dibujadas.
- **Sobre el armazón:** el filo oscuro (#regla-borde), el texto de apoyo
  (#regla-texto, blanco al 78%) y el punto de estado en reposo (#regla-punto, al 40%)
  viven solo encima del verde, y por eso son tokens propios: no se usan sobre el panel.

### Named Rules

**La Regla del Cursor.** El rojo (#B4321F) aparece **una sola vez por pregunta**: en su
cursor. Si hay dos rojos compitiendo en la misma placa, uno sobra.

**La Regla del Gris que Pasa.** Ningún gris por debajo de #606560 sobre el panel. Un
gris más claro se lee bonito en la captura y no se lee en la pantalla.

## Typography

**Display Font:** Bahnschrift (con "DIN Alternate", "Roboto Condensed", "Arial Narrow"
y la pila del sistema como respaldo)
**Body Font:** la misma
**Label/Mono Font:** la pila monoespaciada del sistema, **solo** para código y medidas

**Character:** una grotesca condensada de linaje DIN —la letra de los estándares de
ingeniería alemanes— para todo lo que se lee, y monoespaciada solo donde hay código o
una cifra que se compara en columna. No es una pareja de fuentes: es una fuente con un
registro técnico al lado. Se eligió Bahnschrift porque el proyecto **prohíbe las
dependencias externas** (un fichero, sin build, sin CDN), y entre las que ya están en
la máquina es la que tiene el carácter del mundo. Si no está, la pila cae en la fuente
del sistema y **el carácter se sostiene igual**, porque viene del tratamiento —cifras
tabulares, versalitas espaciadas, contraste de peso— y no del dibujo de la letra.

### Hierarchy

Ocho pasos, y ninguno es decorativo: cada uno tiene un trabajo y un sitio.

- **Display** (600, 30px, 1.0, -0.03em): el multiplicador de la medida.
  Es la cifra que prueba el proyecto y es lo más grande de la pantalla.
- **Headline** (600, 21px, 1.15, -0.015em): el valor elegido de cada respuesta.
- **Cifra** (600, 19px, 1.15): los números de la medida y la palabra AIOM
  del armazón. Van en cifras tabulares, porque se leen en columna.
- **Body** (400, 15px, 1.5): el texto corrido, la prosa del chat y los enunciados
  largos. Medida máxima de 75ch.
- **Title** (400, 13.5px, 1.5, +0.02em): enunciados de pregunta, pestañas, títulos de
  placa, nombre del documento.
- **UI** (400, 12.5px, 1.4): etiquetas de botón, claves de opción, texto de ayuda.
- **Medida** (400, 12px, monoespaciada): probabilidades, tiempos, tokens y el texto
  extraído de un documento. Todo lo que es una medida va aquí.
- **Label** (400, 11.5px, 0.14em, versalitas): rótulos de sección, etiquetas de tipo,
  encabezados de columna. **Es el suelo del sistema**: nada por debajo.

### Named Rules

**La Regla del Número Tabular.** Toda cifra que se compare en columna —tiempos,
tokens, probabilidades, peticiones— va con cifras tabulares. Si dos números no se
alinean verticalmente, el instrumento está mal montado.

**La Regla del Mono con Permiso.** La monoespaciada solo se usa para código y para
medidas. Un rótulo en mono para que parezca técnico es un disfraz.

## Layout

Una sola columna, y el orden lo manda el trabajo: el armazón, las pestañas de los tres
modos, el caso (con su documento y su vista previa), las preguntas, **la acción de
preguntar debajo de ellas** —es lo último que haces— y al final la lectura, con su
medida encima.

- **Ancho de contenido:** 1180px, centrado, con relleno lateral fluido
  (`clamp(14px, 3vw, 26px)`).
- **Ritmo vertical:** `clamp(16px, 2.5vw, 24px)` entre bloques. Más aire por encima de
  un rótulo que por debajo de él.
- **Densidad:** alta a propósito. Los márgenes internos de una placa son de 14-18px, no
  de 40px. Es una superficie de lectura, no una página de presentación.
- **Responsive:** por debajo de 940px las dos placas de lectura se apilan; por debajo
  de 640px el armazón deja de ser pegajoso, el multiplicador baja a su propia línea y los campos de clave se ensanchan. Sin desbordes horizontales a 390px.

## Elevation & Depth

**No hay sombras.** Cero. La profundidad se dice con **capas tonales y líneas de 1px**:
el panel (#E4E5DF) es el fondo, la cara de la regla (#FAFAF7) es lo que está encima, y
la cara hundida (#F2F3EE) es lo que está debajo del dedo. Un borde de 1px separa una
capa de otra; un borde de 2px marca lo activo (la pestaña elegida, el armazón).

Esto no es una limitación: es la decisión. Un instrumento de precisión no flota. Una
sombra difusa sobre este panel diría «tarjeta de aplicación web» y rompería el mundo
entero.

### Named Rules

**La Regla del Plano.** Si algo necesita una sombra para entenderse, lo que falla es la
jerarquía, no la sombra. Se arregla con una línea, un peso o un color, nunca con un
desenfoque.

## Shapes

Forma de filo: los radios son **2px** (botones, campos, pestañas) y **3px** (placas y
bloques). Nada redondeado, nada biselado. Las líneas son de 1px salvo la de 2px que
marca el armazón y la pestaña activa.

La única forma circular es el punto de estado (7px) y la única pastilla completa
(99px) es el interruptor de comparar, porque es un control que el usuario ya conoce
con esa forma y cambiarla sería disfrazarlo.

**La geometría que sí importa es la escala.** Su línea base lleva graduaciones
dibujadas —un SVG de verdad, con cada quinta más larga, como en una regla— y sobre
ella se levantan los trazos de las opciones. Es la única forma «de adorno» que hay en
el sistema, y no es adorno: es la retícula de medida a la vista.

## Components

### Buttons

- **Shape:** filo, 2px de radio.
- **Principal (en el armazón):** fondo blanco sobre el verde, texto verde en
  versalitas espaciadas (9px 22px). Es la acción de la pantalla y vive en el armazón.
- **Secundario:** fondo de cara de regla, borde de 1px hairline fuerte, texto de tinta
  (7px 13px). Al pasar por encima, el borde y el texto se vuelven verdes.
- **En el armazón:** verde sobre verde claro al pasar por encima.
- **Fuerte:** verde lleno con texto blanco, para la acción local (cargar documento).
- **Hover / Focus:** el borde cambia de color en 0.12s. El foco de teclado es un
  contorno de 2px en rojo de cursor, con 2px de separación. Nunca se quita el foco.

### Chips

- **Style:** etiquetas de tipo (choice / score / noul) y la cinta «una sola petición»:
  fondo del color de su tipo (o borde de 1px si es neutra), texto en versalitas.
- **State:** el tipo se elige en el bloque y la etiqueta cambia de color con él.

### Cards / Containers

- **Corner Style:** 3px.
- **Background:** cara de regla sobre el panel.
- **Shadow Strategy:** ninguna. Ver Elevation & Depth.
- **Border:** 1px hairline fuerte; 2px solo en lo activo.
- **Internal Padding:** 14-18px.

### Inputs / Fields

- **Style:** fondo hundido (#F2F3EE), borde de 1px hairline, radio 2px, 7px 10px.
- **Focus:** el fondo pasa a la cara de regla y el borde a verde de escala. Sin brillo.
- **Error / Disabled:** el error es una caja de tinta roja sobre fondo rojizo muy
  tenue, en monoespaciada, con el mensaje **completo** de la API; nunca «algo falló».

### Navigation

- **Style:** pestañas de texto con subrayado de 2px en verde para la activa. El estado
  se marca con `aria-selected`, no con una clase.
- **Mobile:** el armazón deja de ser pegajoso y la cinta lateral se oculta.

### La Escala Graduada (componente firma)

Es lo que define esta interfaz. Por cada respuesta:

- Una **línea base** de 1px con graduaciones dibujadas (SVG en línea, tic cada 9px,
  cada quinto más largo).
- Un **trazo por opción**, ancho repartido a partes iguales, cuya altura es su
  probabilidad relativa al máximo. Mínimo 2px, para que una probabilidad de 0.000 se
  vea como una marca y no desaparezca.
- El **trazo elegido**, entintado en verde de escala. Los demás, en hairline fuerte.
- El **cursor**: una aguja roja de 2px a altura completa, con una punta triangular
  arriba, centrada en la opción elegida.
- **Etiquetas** debajo, una por trazo, con su probabilidad en cifras tabulares. En un
  `score` van ordenadas por nivel (0, 1, 2); en un `choice`, de más probable a menos.

## Do's and Don'ts

### Do:

- **Do** usar el rojo de cursor (#B4321F) **una sola vez por pregunta**: en su cursor.
- **Do** poner cifras tabulares en todo lo que se compare en columna.
- **Do** decir la verdad en los números: la lectura vacía enseña la medición publicada
  del repositorio **dicha como lo que es**, y la sustituye por la tuya en cuanto mides.
- **Do** mantener el gris más claro en #606560 o más oscuro sobre el panel.
- **Do** construir con controles web de siempre: pestañas, campos, botones, interruptor.
- **Do** mantener el orden de lectura del trabajo: caso → preguntas → resultado.

### Don't:

- **Don't** usar sombras, desenfoques, `backdrop-filter` ni degradados. La profundidad
  son capas tonales y líneas de 1px.
- **Don't** redondear por encima de 3px, salvo el interruptor (99px), que es un control
  que el usuario ya conoce así.
- **Don't** usar la monoespaciada como disfraz de «técnico»: solo código y medidas.
- **Don't** bajar ningún texto de 11.5px.
- **Don't** usar glifos de texto ni emoji como iconos: los iconos se dibujan (SVG en
  línea, un solo grosor de trazo).
- **Don't** inventar cifras. Todo número de esta interfaz sale de una medición real; si
  no hay medición, no hay número.
- **Don't** vestir el instrumento: nada de biseles, tornillos, agujas decorativas ni
  texturas de madera. El mundo entra por el tipo, el color, la densidad y la marca.
