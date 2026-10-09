"""Escalado en cascada: la misma entrada con 1, 5, 10 y 15 preguntas encadenadas.

La pregunta que responde: **¿cómo crece el coste al añadir preguntas?** En modo
decision el motor puntua todas en la misma pasada, asi que deberia crecer poco; en
modo chat cada respuesta es texto que hay que generar, asi que deberia crecer
linealmente (y a 9,94 ms por token, eso se nota).

En vez de inventar casos distintos por nivel, se define **un fondo de 15 preguntas**
sobre cada entrada y se toman las primeras N. Asi el nivel 15 es literalmente el 5
mas diez, y la comparacion es limpia.

    python bench_cascada.py
"""

# Cada entrada lleva un fondo de 15 preguntas y su verdad de referencia.
# Formato: (id, pregunta, criterios, esperado)
#   dict con {true,false} -> si/no | lista -> score | dict de opciones -> choice

TICKET = "Me cobraron dos veces la suscripción este mes. Escribí el lunes y nadie me "
TICKET += "contestó. Necesito que me devuelvan el dinero antes del viernes."

FONDO_TICKET = [
    ("equipo", "¿Qué equipo debe atenderlo?",
     {"billing": "Pagos, cargos y reembolsos",
      "technical": "Errores de la aplicación",
      "general": "Otras consultas"}, "billing"),
    ("sentimiento", "¿Qué sentimiento tiene el mensaje?",
     {"positivo": "Satisfacción o agradecimiento",
      "neutro": "Sin carga emocional",
      "negativo": "Queja, enfado o frustración"}, "negativo"),
    ("intencion", "¿Qué quiere el cliente?",
     {"pregunta": "Pide información o instrucciones",
      "queja": "Reporta un problema o expresa descontento",
      "peticion": "Solicita una acción concreta"}, "peticion"),
    ("urgencia", "¿Qué urgencia tiene?",
     ["Puede esperar", "Conviene atenderlo hoy", "Necesita acción inmediata"], 2),
    ("escalada", "¿Pide el cliente hablar con una persona?",
     {"true": "Pide explícitamente un agente humano",
      "false": "No lo pide"}, False),
    ("contacto_previo", "¿Menciona un contacto anterior?",
     {"true": "Menciona haber escrito o reclamado antes",
      "false": "No hay señal de contacto anterior"}, True),
    ("datos_personales", "¿Contiene datos personales identificables?",
     {"true": "Nombre, correo, teléfono o documento",
      "false": "No contiene datos personales"}, False),
    ("tono", "¿Qué tono tiene?",
     {"calmado": "Tranquilo y objetivo", "molesto": "Visiblemente enfadado"}, "calmado"),
    ("idioma", "¿En qué idioma está escrito?",
     {"espanol": "Español", "ingles": "Inglés", "otro": "Otro idioma"}, "espanol"),
    ("pide_reembolso", "¿Pide que se le devuelva dinero?",
     {"true": "Sí, pide un reembolso", "false": "No lo pide"}, True),
    ("pide_cancelacion", "¿Pide cancelar el servicio?",
     {"true": "Sí, pide cancelar", "false": "No lo pide"}, False),
    ("menciona_importe", "¿Aparece una cantidad de dinero concreta?",
     {"true": "Aparece una cifra en dinero", "false": "No aparece ninguna cifra"}, False),
    ("gravedad", "¿Qué gravedad tiene el problema?",
     ["Incidencia menor", "Problema real pero acotado", "Problema grave"], 1),
    ("pide_fecha", "¿El cliente impone una fecha límite?",
     {"true": "Menciona un plazo o fecha tope", "false": "No menciona plazo"}, True),
    ("pide_confirmacion", "¿Pide que se le confirme algo?",
     {"true": "Pide que se le confirme o avise", "false": "No pide confirmación"}, False),
]

PRODUCTO = "Zapatillas de trail impermeables, talla 42, color negro, con suela de "
PRODUCTO += "agarre para barro y membrana transpirable. Peso 310 gramos. Precio 89,90 "
PRODUCTO += "euros, con un 15% de descuento hasta el domingo."

FONDO_PRODUCTO = [
    ("categoria", "¿A qué categoría pertenece?",
     {"calzado": "Zapatos, botas o zapatillas",
      "ropa": "Prendas de vestir",
      "accesorios": "Complementos y equipamiento"}, "calzado"),
    ("genero", "¿Para qué público es?",
     {"hombre": "Pensado para hombre", "mujer": "Pensado para mujer",
      "unisex": "Sin género definido"}, "unisex"),
    ("talla", "¿Qué talla se menciona?",
     {"38": "Talla 38", "40": "Talla 40", "42": "Talla 42"}, "42"),
    ("color", "¿De qué color es?",
     {"negro": "Negro", "azul": "Azul", "gris": "Gris"}, "negro"),
    ("precio", "¿Cuál es el precio sin descuento?",
     ["Menos de 50 euros", "Entre 50 y 100 euros", "Más de 100 euros"], 1),
    ("rebajado", "¿Está en oferta?",
     {"true": "Sí, tiene descuento", "false": "No tiene descuento"}, True),
    ("deporte", "¿Para qué deporte es?",
     {"senderismo": "Caminar por el monte",
      "ciudad": "Uso urbano", "gimnasio": "Entrenamiento indoor"}, "senderismo"),
    ("impermeable", "¿Es impermeable?",
     {"true": "Sí, resiste el agua", "false": "No lo es"}, True),
    ("peso", "¿Cuánto pesa?",
     {"ligero": "Menos de 250 gramos", "medio": "Entre 250 y 350 gramos",
      "pesado": "Más de 350 gramos"}, "medio"),
    ("temporada", "¿Para qué temporada?",
     {"verano": "Clima cálido", "invierno": "Clima frío",
      "todo_el_ano": "Cualquier época"}, "todo_el_ano"),
    ("suela", "¿Cómo es la suela?",
     {"lisa": "Sin dibujo", "agarre": "Con dibujo para agarrar",
      "mixta": "Un poco de todo"}, "agarre"),
    ("transpirable", "¿Es transpirable?",
     {"true": "Sí, deja salir el sudor", "false": "No lo es"}, True),
    ("descuento", "¿Cuánto descuento tiene?",
     {"5": "Un 5%", "15": "Un 15%", "30": "Un 30%"}, "15"),
    ("caduca_oferta", "¿La oferta caduca?",
     {"true": "Sí, tiene fecha límite", "false": "No caduca"}, True),
    ("stock", "¿Se indica disponibilidad?",
     {"true": "Se menciona que hay existencias",
      "false": "No se dice nada de disponibilidad"}, False),
]

CASOS = [
    ("ticket", TICKET, FONDO_TICKET),
    ("producto", PRODUCTO, FONDO_PRODUCTO),
]

NIVELES = [1, 5, 10, 15]
