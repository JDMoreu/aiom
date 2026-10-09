"""Por qué se espera cada respuesta, y cómo funciona cada tipo de pregunta.

Esto es lo que hace que el detalle se pueda leer sin adivinar: cada caso lleva su
razonamiento, y cada bloque lleva la explicación de sus opciones.

No lo usa ningún script para medir; solo lo consume `detalle.py` para redactar
docs/DETALLE.md. Va aquí y no en los casos para no mezclar datos y prosa.
"""

# --------------------------------------------------------------------------- #
# Cómo funciona cada tipo
# --------------------------------------------------------------------------- #
TIPOS = {
    "choice": {
        "nombre": "CHOICE",
        "que_es": "Elegir **una** opción de una lista cerrada.",
        "como_funciona": (
            "El servidor construye un árbol de decisión con las opciones y lee los "
            "logits en el nodo correspondiente. Devuelve la de más probabilidad, la "
            "probabilidad de **cada** opción (suman 1) y una confianza derivada de lo "
            "repartida que esté."),
        "que_mirar": (
            "Si la probabilidad está repartida entre varias opciones, el modelo no lo "
            "tiene claro aunque la ganadora gane. Ahí es donde conviene un umbral."),
    },
    "score": {
        "nombre": "SCORE",
        "que_es": "Situarse en una **escala ordenada** de niveles.",
        "como_funciona": (
            "Los niveles van de menor a mayor y se numeran desde 0. El servidor "
            "devuelve la probabilidad de cada nivel, y la puntuación se calcula "
            "multiplicando cada nivel por su probabilidad y sumando — puede caer "
            "**entre** dos niveles, que es justo lo informativo."),
        "que_mirar": (
            "Una puntuación de 1,4 sobre 2 significa que está entre «bastante» y "
            "«mucho», no que sea un 70%. Es una posición ponderada."),
    },
    "probability": {
        "nombre": "PROBABILITY",
        "que_es": "Una pregunta de **sí o no**, con la probabilidad de que sí.",
        "como_funciona": (
            "Solo hay dos resultados posibles, así que un único número describe la "
            "respuesta entera. El servidor devuelve la probabilidad de `true` y de "
            "`false` (suman 1)."),
        "que_mirar": (
            "Un 0,52 no es un «sí»: es un empate. A diferencia de CHOICE, aquí no hay "
            "una confianza separada que lo delate — hay que mirar el número."),
    },
}

# --------------------------------------------------------------------------- #
# CHOICE — por qué esa opción
# --------------------------------------------------------------------------- #
CHOICE = {
    1: "Un cobro duplicado es dinero: cargos y reembolsos. No es un fallo de la aplicación ni una consulta general.",
    2: "«La app se cierra sola» es un fallo del programa, aunque sea al abrir un informe.",
    3: "Es una consulta informativa sin incidencia: ni dinero ni error técnico.",
    4: "El reembolso es dinero, aunque el origen fuera un pedido cancelado.",
    5: "Un botón que no responde es una función rota de la aplicación.",
    6: "Agradecimiento explícito y sin queja: positivo.",
    7: "Reproche directo («es vergonzoso») además del problema: negativo.",
    8: "Pregunta informativa sin carga emocional: neutro.",
    9: "Elogio explícito al servicio: positivo.",
    10: "«Estoy harto» es frustración declarada: negativo.",
    11: "Pide información sobre cómo hacer algo; no reporta un fallo ni pide que se actúe.",
    12: "Pide una acción concreta (cambiar la dirección), no una explicación.",
    13: "Reporta un problema y la falta de solución: es una queja.",
    14: "Pide saber dónde consultar algo: información.",
    15: "Solicita una acción concreta (cancelar), no pregunta nada.",
    16: "Zapatillas son calzado, aunque sean de trail.",
    17: "Chaqueta es una prenda de vestir, con talla y color.",
    18: "Una mochila es equipamiento, no una prenda que se vista.",
    19: "Botas son calzado, sin importar el uso de montaña.",
    20: "Guantes y gorro son complementos; se llevan encima de la ropa, no son la prenda.",
    21: "El mensaje está en inglés.",
    22: "El mensaje está en español.",
    23: "Está en francés, que no es ni español ni inglés: la categoría «otro» existe justo para esto.",
    24: "La web caída impide trabajar a toda la oficina: bloquea.",
    25: "Un detalle estético con la función intacta: no urge.",
    26: "Hay una forma de seguir (exportar a mano), así que molesta pero no bloquea.",
    27: "Sin facturar no hay negocio: bloquea.",
    28: "Es una sugerencia para el futuro, no un problema actual.",
    29: "Un pago rechazado es dinero, aunque el usuario no sepa la causa.",
    30: "Una integración que deja de sincronizar es un fallo técnico, no de facturación.",
}

# --------------------------------------------------------------------------- #
# SCORE — por qué ese nivel
# --------------------------------------------------------------------------- #
SCORE = {
    1: "Nivel 2: zapatillas impermeables de trail responden exactamente a una búsqueda de calzado de senderismo para lluvia.",
    2: "Nivel 0: unos calcetines de vestir no tienen que ver con la búsqueda.",
    3: "Nivel 1: son calzado de montaña, pero de caña alta y para invierno — se acerca sin ser lo pedido.",
    4: "Nivel 2: figuras de dinosaurios para mayores de 3 años encajan con un niño de 6 aficionado.",
    5: "Nivel 0: una novela histórica para adultos no tiene relación con el regalo.",
    6: "Nivel 0: dos píxeles de desplazamiento no afectan a la funcionalidad.",
    7: "Nivel 1: la función está rota en Safari, pero Chrome sirve de alternativa para la mayoría.",
    8: "Nivel 2: no arranca para nadie y no hay alternativa posible.",
    9: "Nivel 0: una errata en el pie es cosmética.",
    10: "Nivel 1: la búsqueda no devuelve nada, pero se puede navegar por categorías.",
    11: "Nivel 2: llegó antes, en perfecto estado y era lo buscado.",
    12: "Nivel 0: golpe visible y arañazo en la carcasa.",
    13: "Nivel 1: funciona bien, aunque el embalaje venía dañado y llegó un día tarde.",
    14: "Nivel 2: envío rápido, embalaje cuidado y supera lo anunciado.",
    15: "Nivel 0: no encendía y hubo que devolverlo.",
    16: "Nivel 2: el sistema caído con toda la plantilla parada y sin facturar.",
    17: "Nivel 0: una pregunta sobre planes futuros puede esperar.",
    18: "Nivel 1: hay una fecha mañana, así que conviene atenderlo hoy sin ser una caída.",
    19: "Nivel 2: datos de pago de un cliente expuestos exige acción inmediata.",
    20: "Nivel 0: saber si el manual está en papel no urge.",
    21: "Nivel 2: paso a paso y funcionó a la primera.",
    22: "Nivel 0: repite el manual y no resuelve la duda.",
    23: "Nivel 1: soluciona el problema pero no explica la causa.",
    24: "Nivel 2: instrucciones claras, con capturas y enlace directo.",
    25: "Nivel 0: remite a otra sección sin decir dónde.",
    26: "Nivel 1: buen estado general con alguna marca de uso.",
    27: "Nivel 2: precintado en su caja original, sin abrir.",
    28: "Nivel 0: pantalla rota y no enciende.",
    29: "Nivel 1: desgaste en las esquinas y la bisagra suena.",
    30: "Nivel 0: teclas hundidas y pantalla que parpadea.",
}

# --------------------------------------------------------------------------- #
# PROBABILITY — por qué sí o no
# --------------------------------------------------------------------------- #
PROBABILITY = {
    1: "Sí: premio llamativo, urgencia artificial («antes de 24 horas») y un enlace. Es el patrón clásico.",
    2: "No: es el aviso de envío del propio pedido, sin petición de datos ni enlace sospechoso.",
    3: "Sí: pide verificar la cuenta bancaria bajo amenaza de suspensión. Ingeniería social.",
    4: "No: factura del pedido con número, sin pedir nada.",
    5: "Sí: urgencia, caducidad y petición de datos de tarjeta. Los tres a la vez.",
    6: "Sí: «can I please just talk to a real person» lo pide de forma explícita.",
    7: "No: pregunta cómo cambiar una dirección, no pide una persona.",
    8: "Sí: «quiero hablar con un responsable» es explícito.",
    9: "No: pregunta si se puede descargar una factura.",
    10: "Sí: «pásenme con alguien de verdad» es explícito.",
    11: "Sí: «como ya comenté la semana pasada» remite a un contacto anterior.",
    12: "No: acaba de registrarse, es su primer contacto.",
    13: "Sí: «la cuarta vez que escribo» cuenta los intentos previos.",
    14: "Sí: menciona un ticket previo con su número.",
    15: "No: pide ayuda con la configuración inicial, sin mencionar contactos anteriores.",
    16: "Sí: nombre, correo y teléfono, los tres juntos.",
    17: "No: un número de pedido no identifica a una persona.",
    18: "Sí: un DNI es un dato identificativo directo.",
    19: "No: describe un problema de rendimiento sin datos personales.",
    20: "Sí: nombre y apellidos («Soy Juan Pérez»).",
    21: "Sí: base de datos caída que afecta a todos los clientes.",
    22: "No: es una consulta sobre seguimiento de envío.",
    23: "Sí: un cargo de 4.500 euros no reconocido hay que mirarlo ya.",
    24: "No: pregunta por la política de devoluciones, sin caso abierto.",
    25: "Sí: brecha de datos con obligación de avisar a protección de datos.",
    26: "Sí: solo pregunta si se puede pagar en dos plazos; no pide que se haga nada.",
    27: "No: pide expresamente que se devuelva el importe — hay una acción pendiente.",
    28: "Sí: pregunta la periodicidad de renovación, es información pura.",
    29: "No: pide que se emita una factura rectificativa, es una acción.",
    30: "Sí: pregunta si hay tienda física, sin pedir ninguna acción.",
}

# --------------------------------------------------------------------------- #
# Hallazgos: casos donde el fallo NO es del modelo
# --------------------------------------------------------------------------- #
# Diagnostico medido, no una hipotesis. Los numeros salen de repetir el mismo caso
# cambiando solo la descripcion del campo.
DIAGNOSTICO = [
    {
        "titulo": "El idioma: acierta si le preguntas solo, falla si le añades las etiquetas",
        "sintoma": (
            "Los tres casos de idioma fallan igual en `tipado` y en `natural` "
            "(responden `otro`), mientras el modo `llm` acierta. No es el tamaño del "
            "modelo: es cómo se construye la pregunta."),
        "medido": [
            ("Descripción exacta del banco "
             "(*«¿En qué idioma está escrito? 'espanol' = Español…»*)",
             "`ingles` **0.33 · 0.33 · 0.33** — empate a tres, no sabe"),
            ("Solo la pregunta (*«¿En qué idioma está escrito?»*)",
             "`ingles` **0.69** — correcto"),
            ("Con las opciones entre comillas simples eliminadas",
             "`otro` 0.70 — vuelve a fallar"),
        ],
        "causa": (
            "Al añadir `'etiqueta' = descripción` a la pregunta, el texto que lee el "
            "modelo se llena de palabras en español («Español», «Inglés», «Cualquier "
            "otro idioma»). La pregunta deja de ser «¿en qué idioma está ESTO?» y pasa "
            "a ser «aquí hay tres etiquetas, elige una» — y sin referencia al texto de "
            "entrada, el modelo se queda sin señal."),
        "leccion": (
            "Cuando la pregunta es sobre una **propiedad del propio texto** —el idioma, "
            "el tono—, las etiquetas no ayudan: estorban. La descripción de cada "
            "opción sirve para definir **qué categoría es cuál**, no para preguntar."),
    },
    {
        "titulo": "La forma de la fruta: el mismo mecanismo, en el catálogo encadenado",
        "sintoma": (
            "La forma falla 8 de 16 veces y siempre hacia `redonda`, incluso con un "
            "plátano. El color, en cambio, solo falla 2 de 16."),
        "medido": [
            ("Descripción exacta del banco (plátano)",
             "`redonda` **0.64** — incorrecto, y con confianza"),
            ("Solo la pregunta (*«¿Qué forma tiene?»*) (plátano)",
             "`alargada` **0.67** — correcto"),
            ("Con `alargada` listada primero",
             "`redonda` 0.55 — el orden no lo arregla"),
        ],
        "causa": (
            "El mismo efecto: al colgarle la definición de cada opción, la primera "
            "etiqueta (`redonda`, la más genérica) absorbe la probabilidad. Reordenar "
            "las opciones no lo cambia, así que no es un sesgo de posición sino de "
            "dilución de la pregunta."),
        "leccion": (
            "Si una pregunta falla en el modo decisión pero el mismo modelo la acierta "
            "por chat, **el problema es la descripción del campo**, no el modelo. "
            "Antes de subir de tamaño o meter RAG, prueba a quitarle las etiquetas."),
    },
]

# Para las frutas se explica el objeto entero de una vez: los cinco atributos salen
# del mismo razonamiento, no de cinco decisiones independientes.
FRUTAS = {
    "una manzana roja":
        "Una manzana es **dulce** (no cítrica), de forma **redonda**, y al decir «roja» "
        "el color ya viene dado. Su piel es de **un solo tono**, sin manchas. Respecto "
        "al tamaño, una manzana entra en la categoría **mediana**.",
    "un plátano amarillo maduro":
        "Un plátano maduro es **dulce**; su forma es **alargada**, no esférica. El "
        "amarillo lo da el enunciado, y la piel de un plátano maduro es de **tono "
        "uniforme** (las manchas aparecen al pasarse). **Tamaño mediano**.",
    "un limón verde":
        "El limón es el caso **cítrico** por antonomasia. Su forma es **redonda** u "
        "ovalada, el verde viene dado, la piel es **uniforme**, y es **pequeño**.",
    "una naranja":
        "La naranja es **cítrica** aunque sea dulce al paladar: la pregunta es por el "
        "sabor ácido característico. Es **redonda**, **naranja** por definición, de "
        "piel **uniforme** y **mediana**.",
    "una sandía partida por la mitad":
        "La sandía es **dulce** (de ahí que se coma como postre) y **redonda**, pero al "
        "decir que está partida vemos el exterior verde y el interior rojo: su color "
        "**no es de un solo tono**. Es **grande**.",
    "un racimo de uvas moradas":
        "Las uvas son **dulces**; cada uva es **redonda** aunque el racimo no lo sea, y "
        "el enunciado fija el **morado**. El color es **uniforme** y cada uva es "
        "**pequeña**.",
    "una fresa roja con las hojas verdes":
        "La fresa es **dulce**; su forma es **irregular** (no es una esfera ni un "
        "alargado limpio, tiene el cuello ancho). El rojo viene dado, pero las hojas "
        "verdes hacen que el conjunto **no sea de un solo tono**. Es **pequeña**.",
    "una pera verde alargada":
        "Una pera es **dulce**, de forma **alargada**, y el enunciado fija el "
        "**verde**. Su piel es **uniforme** y su tamaño es **mediano**.",
}

# --------------------------------------------------------------------------- #
# TICKETS — por qué cada campo
# --------------------------------------------------------------------------- #
TICKETS = {
    ("Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el "
     "dinero antes del viernes.", "equipo"):
        "Un cobro duplicado con petición de devolución es facturación.",
    ("Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el "
     "dinero antes del viernes.", "urgencia"):
        "**Aquí el modelo y yo discrepamos.** Yo esperaba nivel 1 («conviene "
        "atenderlo hoy»): es dinero, pero un cobro duplicado no tumba el negocio. El "
        "modelo responde 2 porque lee «antes del viernes» como presión. Es discutible, "
        "y por eso está marcado como fallo en vez de esconderse.",
    ("Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el "
     "dinero antes del viernes.", "persona"):
        "Yo esperaba que sí, por ser dinero y con fecha límite. El modelo dice que no "
        "**con confianza 0,024** — un empate técnico: no sabe. Es la clase de caso "
        "donde el umbral de confianza debería mandar a revisión humana.",
    ("Me cobraron dos veces la suscripción este mes y necesito que me devuelvan el "
     "dinero antes del viernes.", "tono"):
        "El texto no insulta ni usa mayúsculas ni reprocha: es una petición firme pero "
        "**tranquila**. El modelo lee «necesito… antes del viernes» como enfado. Segunda "
        "discrepancia del mismo caso.",

    ("La aplicación no arranca desde esta mañana y toda la plantilla está parada sin "
     "poder facturar. Esto es inaceptable.", "equipo"):
        "«No arranca» es un fallo de la aplicación: técnico.",
    ("La aplicación no arranca desde esta mañana y toda la plantilla está parada sin "
     "poder facturar. Esto es inaceptable.", "urgencia"):
        "Nivel 2 claro: nadie puede trabajar.",
    ("La aplicación no arranca desde esta mañana y toda la plantilla está parada sin "
     "poder facturar. Esto es inaceptable.", "persona"):
        "Sí: una caída total con impacto económico no se resuelve automáticamente.",
    ("La aplicación no arranca desde esta mañana y toda la plantilla está parada sin "
     "poder facturar. Esto es inaceptable.", "tono"):
        "«Esto es inaceptable» es un reproche explícito: molesto.",

    ("¿Cuál es vuestro horario de atención telefónica los sábados?", "equipo"):
        "Consulta informativa sin incidencia: general.",
    ("¿Cuál es vuestro horario de atención telefónica los sábados?", "urgencia"):
        "Nivel 0: saber un horario puede esperar.",
    ("¿Cuál es vuestro horario de atención telefónica los sábados?", "persona"):
        "No: es información que se puede dar sin intervención humana.",
    ("¿Cuál es vuestro horario de atención telefónica los sábados?", "tono"):
        "Pregunta neutra y educada: tranquilo.",

    ("El botón de exportar no hace nada en Safari. En Chrome sí funciona.", "equipo"):
        "Un botón que no responde: técnico.",
    ("El botón de exportar no hace nada en Safari. En Chrome sí funciona.", "urgencia"):
        "Nivel 1: hay alternativa (Chrome), así que no es bloqueante.",
    ("El botón de exportar no hace nada en Safari. En Chrome sí funciona.", "persona"):
        "No: el propio texto indica que hay forma de seguir.",
    ("El botón de exportar no hace nada en Safari. En Chrome sí funciona.", "tono"):
        "Describe el fallo sin carga emocional: tranquilo.",

    ("Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con "
     "un responsable.", "equipo"):
        "Un reembolso es facturación.",
    ("Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con "
     "un responsable.", "urgencia"):
        "Nivel 2: tres semanas sin respuesta y una petición explícita de escalada.",
    ("Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con "
     "un responsable.", "persona"):
        "Sí, y además lo pide el propio cliente.",
    ("Llevo tres semanas esperando el reembolso y nadie me contesta. Quiero hablar con "
     "un responsable.", "tono"):
        "Tres semanas de silencio y una exigencia: molesto.",

    ("Quería saber si el plan anual se puede pagar en dos plazos.", "equipo"):
        "Condiciones de pago: facturación.",
    ("Quería saber si el plan anual se puede pagar en dos plazos.", "urgencia"):
        "Nivel 0: es una consulta previa, no hay nada en marcha.",
    ("Quería saber si el plan anual se puede pagar en dos plazos.", "persona"):
        "No: es información que el sistema puede dar solo.",
    ("Quería saber si el plan anual se puede pagar en dos plazos.", "tono"):
        "Pregunta cortés: tranquilo.",
}
