"""90 casos con verdad de referencia: 30 de cada tipo de pregunta.

Los tres modos que se comparan responden EXACTAMENTE a estos mismos casos:

  tipado      el formato de TypeSafe, JSON con state.input + questions.decision
  natural     el mismo caso escrito con cabeceras (choice: / score: / boolean:)
  llm         la pregunta a pelo por /v1/chat/completions, sin esquema

`esperado` es la respuesta correcta. En SCORE es el nivel (0, 1 o 2).
"""

CHOICE = [
    # (estado, pregunta, {clave: descripcion}, esperado)
    ("Me cobraron dos veces la suscripción. ¿Pueden ayudarme?",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "billing"),

    ("La app se cierra sola cada vez que abro el informe mensual.",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "technical"),

    ("¿Cuál es vuestro horario de atención telefónica?",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "general"),

    ("Llevo tres días esperando el reembolso de un pedido cancelado.",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "billing"),

    ("El botón de exportar no hace nada cuando lo pulso.",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "technical"),

    ("Me encantó el servicio, muy rápido todo. Gracias!",
     "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "negativo": "Queja, enfado o frustración",
      "neutro": "Sin carga emocional clara"}, "positivo"),

    ("Es la tercera vez que escribo y nadie me contesta. Es vergonzoso.",
     "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "negativo": "Queja, enfado o frustración",
      "neutro": "Sin carga emocional clara"}, "negativo"),

    ("Quería consultar si el plan incluye facturación automática.",
     "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "negativo": "Queja, enfado o frustración",
      "neutro": "Sin carga emocional clara"}, "neutro"),

    ("Gracias por arreglarlo tan rápido, sois los mejores.",
     "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "negativo": "Queja, enfado o frustración",
      "neutro": "Sin carga emocional clara"}, "positivo"),

    ("Nunca funciona nada, estoy harto de esta aplicación.",
     "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "negativo": "Queja, enfado o frustración",
      "neutro": "Sin carga emocional clara"}, "negativo"),

    ("¿Cómo puedo cambiar la contraseña de mi cuenta?",
     "¿Qué quiere el usuario?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "pregunta"),

    ("Necesito que me cambien la dirección de envío del pedido 4471.",
     "¿Qué quiere el usuario?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "peticion"),

    ("El producto llegó roto y nadie me ha dado solución.",
     "¿Qué quiere el usuario?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "queja"),

    ("¿Dónde puedo ver el historial de mis pagos?",
     "¿Qué quiere el usuario?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "pregunta"),

    ("Por favor, cancelen mi suscripción a partir del mes que viene.",
     "¿Qué quiere el usuario?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "peticion"),

    ("Zapatillas de trail impermeables con suela de agarre para barro.",
     "¿A qué categoría pertenece el producto?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "calzado"),

    ("Chaqueta impermeable con capucha, talla L, color azul marino.",
     "¿A qué categoría pertenece el producto?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "ropa"),

    ("Mochila de 30 litros con funda de lluvia incluida.",
     "¿A qué categoría pertenece el producto?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "accesorios"),

    ("Botas de montaña de caña alta para invierno.",
     "¿A qué categoría pertenece el producto?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "calzado"),

    ("Guantes térmicos y gorro de lana para actividades de invierno.",
     "¿A qué categoría pertenece el producto?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "accesorios"),

    ("Hello, I would like to know if you ship to Ireland.",
     "¿En qué idioma está escrito?",
     {"espanol": "Español",
      "ingles": "Inglés",
      "otro": "Cualquier otro idioma"}, "ingles"),

    ("Buenos días, quería consultar el estado de mi pedido.",
     "¿En qué idioma está escrito?",
     {"espanol": "Español",
      "ingles": "Inglés",
      "otro": "Cualquier otro idioma"}, "espanol"),

    ("Bonjour, je voudrais un remboursement s'il vous plaît.",
     "¿En qué idioma está escrito?",
     {"espanol": "Español",
      "ingles": "Inglés",
      "otro": "Cualquier otro idioma"}, "otro"),

    ("La web no carga desde esta mañana en toda la oficina.",
     "¿Qué prioridad tiene el caso?",
     {"alta": "Bloquea el trabajo ahora mismo",
      "media": "Molesto pero hay forma de seguir",
      "baja": "No urge, puede esperar"}, "alta"),

    ("El color del icono no me gusta demasiado, pero funciona bien.",
     "¿Qué prioridad tiene el caso?",
     {"alta": "Bloquea el trabajo ahora mismo",
      "media": "Molesto pero hay forma de seguir",
      "baja": "No urge, puede esperar"}, "baja"),

    ("Tengo que exportar el informe a mano porque el botón falla, pero puedo seguir.",
     "¿Qué prioridad tiene el caso?",
     {"alta": "Bloquea el trabajo ahora mismo",
      "media": "Molesto pero hay forma de seguir",
      "baja": "No urge, puede esperar"}, "media"),

    ("No podemos facturar a clientes porque el sistema está caído.",
     "¿Qué prioridad tiene el caso?",
     {"alta": "Bloquea el trabajo ahora mismo",
      "media": "Molesto pero hay forma de seguir",
      "baja": "No urge, puede esperar"}, "alta"),

    ("¿Podéis añadir un modo oscuro en alguna actualización futura?",
     "¿Qué prioridad tiene el caso?",
     {"alta": "Bloquea el trabajo ahora mismo",
      "media": "Molesto pero hay forma de seguir",
      "baja": "No urge, puede esperar"}, "baja"),

    ("El pago se rechazó tres veces y no sé por qué.",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "billing"),

    ("La integración con nuestra herramienta de nóminas dejó de sincronizar ayer.",
     "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación e integraciones",
      "general": "Otras consultas"}, "technical"),
]

SCORE = [
    # (estado, pregunta, [niveles de menor a mayor], esperado)
    ("Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una "
     "ficha de zapatillas de trail impermeables con guía de tallas y reseñas.",
     "¿Qué relevancia tiene este elemento para la solicitud?",
     ["No relevante", "Algo relevante", "Muy relevante"], 2),

    ("Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una "
     "ficha de calcetines de algodón para vestir.",
     "¿Qué relevancia tiene este elemento para la solicitud?",
     ["No relevante", "Algo relevante", "Muy relevante"], 0),

    ("Búsqueda: zapatillas de senderismo ligeras para días de lluvia. Resultado: una "
     "ficha de botas de montaña de caña alta para invierno.",
     "¿Qué relevancia tiene este elemento para la solicitud?",
     ["No relevante", "Algo relevante", "Muy relevante"], 1),

    ("Búsqueda: regalo para un niño de 6 años aficionado a los dinosaurios. Resultado: "
     "un set de figuras de dinosaurios de plástico, para mayores de 3 años.",
     "¿Qué relevancia tiene este elemento para la solicitud?",
     ["No relevante", "Algo relevante", "Muy relevante"], 2),

    ("Búsqueda: regalo para un niño de 6 años aficionado a los dinosaurios. Resultado: "
     "una novela histórica para adultos sobre la Segunda Guerra Mundial.",
     "¿Qué relevancia tiene este elemento para la solicitud?",
     ["No relevante", "Algo relevante", "Muy relevante"], 0),

    ("El botón de exportar se ve un poco desplazado dos píxeles en pantallas pequeñas. "
     "La función de exportar funciona correctamente.",
     "¿Qué gravedad tiene el problema reportado?",
     ["Cosmético, sin impacto en la funcionalidad",
      "Función rota pero existe una forma de saltárselo",
      "Bloqueante, no hay alternativa"], 0),

    ("El botón de exportar no responde en Safari. En Chrome funciona, y la mayoría de "
     "los clientes usan Chrome.",
     "¿Qué gravedad tiene el problema reportado?",
     ["Cosmético, sin impacto en la funcionalidad",
      "Función rota pero existe una forma de saltárselo",
      "Bloqueante, no hay alternativa"], 1),

    ("La aplicación no arranca en ningún navegador. Ningún cliente puede entrar desde "
     "esta mañana.",
     "¿Qué gravedad tiene el problema reportado?",
     ["Cosmético, sin impacto en la funcionalidad",
      "Función rota pero existe una forma de saltárselo",
      "Bloqueante, no hay alternativa"], 2),

    ("El texto del pie de página tiene una errata en una palabra.",
     "¿Qué gravedad tiene el problema reportado?",
     ["Cosmético, sin impacto en la funcionalidad",
      "Función rota pero existe una forma de saltárselo",
      "Bloqueante, no hay alternativa"], 0),

    ("La búsqueda devuelve resultados vacíos, pero se puede navegar por categorías.",
     "¿Qué gravedad tiene el problema reportado?",
     ["Cosmético, sin impacto en la funcionalidad",
      "Función rota pero existe una forma de saltárselo",
      "Bloqueante, no hay alternativa"], 1),

    ("Este producto es exactamente lo que buscaba, llegó antes de lo previsto y en "
     "perfecto estado.",
     "¿Qué calidad tiene la experiencia descrita?",
     ["Mala", "Aceptable", "Excelente"], 2),

    ("El producto llegó con un golpe visible en la caja y un arañazo en la carcasa.",
     "¿Qué calidad tiene la experiencia descrita?",
     ["Mala", "Aceptable", "Excelente"], 0),

    ("El producto funciona bien aunque el embalaje venía algo dañado y tardó un día "
     "más de lo previsto.",
     "¿Qué calidad tiene la experiencia descrita?",
     ["Mala", "Aceptable", "Excelente"], 1),

    ("Impecable: envío rápido, embalaje cuidado y el producto supera lo anunciado.",
     "¿Qué calidad tiene la experiencia descrita?",
     ["Mala", "Aceptable", "Excelente"], 2),

    ("Nada más abrir la caja el aparato no encendía y tuve que devolverlo.",
     "¿Qué calidad tiene la experiencia descrita?",
     ["Mala", "Aceptable", "Excelente"], 0),

    ("El sistema lleva caído desde las 8:00 y toda la plantilla está parada sin poder "
     "facturar.",
     "¿Qué urgencia tiene este caso?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 2),

    ("Quería saber si hay planes de añadir más idiomas en el futuro.",
     "¿Qué urgencia tiene este caso?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 0),

    ("El informe mensual del cliente sale mañana y el botón de exportar falla.",
     "¿Qué urgencia tiene este caso?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 1),

    ("Se ha filtrado el acceso a la cuenta de un cliente con datos de pago visibles.",
     "¿Qué urgencia tiene este caso?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 2),

    ("Me gustaría saber si el manual está disponible en papel.",
     "¿Qué urgencia tiene este caso?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 0),

    ("La respuesta explica paso a paso cómo cambiar la contraseña y funcionó a la "
     "primera.",
     "¿Qué tan útil fue esta respuesta?",
     ["Nada útil", "Parcialmente útil", "Muy útil"], 2),

    ("La respuesta repite lo mismo que ya venía en el manual y no resuelve la duda.",
     "¿Qué tan útil fue esta respuesta?",
     ["Nada útil", "Parcialmente útil", "Muy útil"], 0),

    ("La respuesta soluciona el problema pero no explica por qué ocurría.",
     "¿Qué tan útil fue esta respuesta?",
     ["Nada útil", "Parcialmente útil", "Muy útil"], 1),

    ("Instrucciones claras, con capturas y el enlace directo a la pantalla exacta.",
     "¿Qué tan útil fue esta respuesta?",
     ["Nada útil", "Parcialmente útil", "Muy útil"], 2),

    ("Me remitieron a otra sección sin decirme dónde encontrarla.",
     "¿Qué tan útil fue esta respuesta?",
     ["Nada útil", "Parcialmente útil", "Muy útil"], 0),

    ("El producto está en buen estado general, con alguna marca de uso leve en la "
     "esquina.",
     "¿Cuál es el estado del artículo?",
     ["Deteriorado", "Con señales de uso", "Como nuevo"], 1),

    ("El artículo viene precintado en su caja original, sin abrir.",
     "¿Cuál es el estado del artículo?",
     ["Deteriorado", "Con señales de uso", "Como nuevo"], 2),

    ("El artículo tiene la pantalla rota y no enciende.",
     "¿Cuál es el estado del artículo?",
     ["Deteriorado", "Con señales de uso", "Como nuevo"], 0),

    ("La carcasa está desgastada en las esquinas y la bisagra suena al cerrar.",
     "¿Cuál es el estado del artículo?",
     ["Deteriorado", "Con señales de uso", "Como nuevo"], 1),

    ("El teclado tiene dos teclas hundidas y la pantalla parpadea al moverla.",
     "¿Cuál es el estado del artículo?",
     ["Deteriorado", "Con señales de uso", "Como nuevo"], 0),
]

PROBABILITY = [
    # (estado, pregunta, {true: ..., false: ...}, esperado)
    ("¡GANADOR! Has sido seleccionado para recibir un iPhone gratis. Haz clic aquí "
     "para reclamarlo antes de 24 horas.",
     "¿Es spam o intento de estafa?",
     {"true": "Es spam, fraude o intento de estafa",
      "false": "Es un mensaje legítimo"}, True),

    ("Tu pedido 4471 ha salido de nuestro almacén y llegará el jueves.",
     "¿Es spam o intento de estafa?",
     {"true": "Es spam, fraude o intento de estafa",
      "false": "Es un mensaje legítimo"}, False),

    ("Haga clic en este enlace para verificar su cuenta bancaria o será suspendida.",
     "¿Es spam o intento de estafa?",
     {"true": "Es spam, fraude o intento de estafa",
      "false": "Es un mensaje legítimo"}, True),

    ("Gracias por tu compra. Adjuntamos la factura del pedido 3312.",
     "¿Es spam o intento de estafa?",
     {"true": "Es spam, fraude o intento de estafa",
      "false": "Es un mensaje legítimo"}, False),

    ("URGENTE: su suscripción caduca hoy, introduzca sus datos de tarjeta para "
     "renovarla al instante.",
     "¿Es spam o intento de estafa?",
     {"true": "Es spam, fraude o intento de estafa",
      "false": "Es un mensaje legítimo"}, True),

    ("I have asked three times now. Can I please just talk to a real person?",
     "¿Está pidiendo el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, True),

    ("¿Podríais indicarme cómo cambiar mi dirección de facturación?",
     "¿Está pidiendo el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, False),

    ("Quiero hablar con un responsable, esto no lo soluciona un bot.",
     "¿Está pidiendo el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, True),

    ("¿Hay alguna forma de descargar la factura en PDF?",
     "¿Está pidiendo el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, False),

    ("Pásenme con alguien de verdad, por favor.",
     "¿Está pidiendo el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, True),

    ("Como ya comenté la semana pasada, el problema sigue exactamente igual.",
     "¿El cliente menciona un contacto anterior?",
     {"true": "Menciona un intento o ticket previo",
      "false": "No hay señal de contacto anterior"}, True),

    ("Acabo de registrarme y no encuentro la opción de cambiar el idioma.",
     "¿El cliente menciona un contacto anterior?",
     {"true": "Menciona un intento o ticket previo",
      "false": "No hay señal de contacto anterior"}, False),

    ("Es la cuarta vez que escribo sobre este mismo asunto.",
     "¿El cliente menciona un contacto anterior?",
     {"true": "Menciona un intento o ticket previo",
      "false": "No hay señal de contacto anterior"}, True),

    ("Perdón por insistir, ya abrí un ticket el lunes con el número 8823.",
     "¿El cliente menciona un contacto anterior?",
     {"true": "Menciona un intento o ticket previo",
      "false": "No hay señal de contacto anterior"}, True),

    ("Necesito ayuda con la configuración inicial del dispositivo.",
     "¿El cliente menciona un contacto anterior?",
     {"true": "Menciona un intento o ticket previo",
      "false": "No hay señal de contacto anterior"}, False),

    ("Me llamo Ana García, mi correo es ana.garcia@ejemplo.com y mi teléfono es "
     "612345678.",
     "¿El mensaje contiene datos personales identificables?",
     {"true": "Contiene datos personales como nombre, correo o teléfono",
      "false": "No contiene datos personales"}, True),

    ("El pedido número 4471 sigue sin llegar y ya han pasado dos semanas.",
     "¿El mensaje contiene datos personales identificables?",
     {"true": "Contiene datos personales como nombre, correo o teléfono",
      "false": "No contiene datos personales"}, False),

    ("Adjunto mi DNI 12345678Z para verificar la titularidad de la cuenta.",
     "¿El mensaje contiene datos personales identificables?",
     {"true": "Contiene datos personales como nombre, correo o teléfono",
      "false": "No contiene datos personales"}, True),

    ("La aplicación va lenta desde la última actualización.",
     "¿El mensaje contiene datos personales identificables?",
     {"true": "Contiene datos personales como nombre, correo o teléfono",
      "false": "No contiene datos personales"}, False),

    ("Soy Juan Pérez y quiero cancelar mi suscripción.",
     "¿El mensaje contiene datos personales identificables?",
     {"true": "Contiene datos personales como nombre, correo o teléfono",
      "false": "No contiene datos personales"}, True),

    ("Se ha caído la base de datos de producción y ningún cliente puede acceder.",
     "¿El caso necesita acción humana inmediata?",
     {"true": "Requiere que una persona actúe ya",
      "false": "Puede gestionarse sin intervención humana"}, True),

    ("¿Podéis confirmarme si el envío incluye seguimiento?",
     "¿El caso necesita acción humana inmediata?",
     {"true": "Requiere que una persona actúe ya",
      "false": "Puede gestionarse sin intervención humana"}, False),

    ("Hay un cargo de 4.500 euros que no reconozco en mi tarjeta corporativa.",
     "¿El caso necesita acción humana inmediata?",
     {"true": "Requiere que una persona actúe ya",
      "false": "Puede gestionarse sin intervención humana"}, True),

    ("Quería saber cuál es la política de devoluciones para productos abiertos.",
     "¿El caso necesita acción humana inmediata?",
     {"true": "Requiere que una persona actúe ya",
      "false": "Puede gestionarse sin intervención humana"}, False),

    ("Un cliente ha denunciado una brecha de datos y hay que avisar a protección "
     "de datos hoy mismo.",
     "¿El caso necesita acción humana inmediata?",
     {"true": "Requiere que una persona actúe ya",
      "false": "Puede gestionarse sin intervención humana"}, True),

    ("El usuario pregunta si el plan anual se puede pagar en dos plazos.",
     "¿El caso es una consulta informativa sin acción pendiente?",
     {"true": "Es solo una pregunta informativa",
      "false": "Requiere una acción, no solo información"}, True),

    ("El usuario pide que le devolvamos el importe del pedido 3312.",
     "¿El caso es una consulta informativa sin acción pendiente?",
     {"true": "Es solo una pregunta informativa",
      "false": "Requiere una acción, no solo información"}, False),

    ("¿Cada cuánto se renueva automáticamente la suscripción?",
     "¿El caso es una consulta informativa sin acción pendiente?",
     {"true": "Es solo una pregunta informativa",
      "false": "Requiere una acción, no solo información"}, True),

    ("Necesito que me emitan una factura rectificativa del mes pasado.",
     "¿El caso es una consulta informativa sin acción pendiente?",
     {"true": "Es solo una pregunta informativa",
      "false": "Requiere una acción, no solo información"}, False),

    ("¿Tenéis tienda física en Bogotá?",
     "¿El caso es una consulta informativa sin acción pendiente?",
     {"true": "Es solo una pregunta informativa",
      "false": "Requiere una acción, no solo información"}, True),
]

TODOS = {
    "choice": CHOICE,
    "score": SCORE,
    "probability": PROBABILITY,
}
