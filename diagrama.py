"""Diagrama de arquitectura de AIOM.

Los tokens NO son inventados: son los de DESIGN.md, los mismos que usa web/index.html,
para que el repositorio entero hable un solo idioma visual.

El recorrido se lee de izquierda a derecha y esta NUMERADO en las cabeceras de columna,
porque el fallo clasico de un diagrama asi es no saber hacia donde va:

    1 ENTRADAS -> 2 EL CLIENTE -> 3 LA API -> 4 EL MODELO -> 5 LAS DOS VIAS

Lo que el diagrama tiene que dejar claro, porque es donde se lee mal:

  - api.py es la API, NO el cliente. Es un servidor: recibe la peticion del cliente y se
    la pasa a llama-server. Por eso tiene salida, y por eso esta en su propia columna.
  - El documento lo usa el cliente: se sube en la interfaz, api.py lo extrae con
    documento.py y le DEVUELVE el texto, que pasa a ser el `input` de la peticion. Es un
    ida y vuelta, y se dibuja como tal (flecha de vuelta, a trazos).
  - Se puede llamar a la API sin el cliente: con curl o Postman, directo.
  - preguntar.py (la consola) NO pasa por api.py: habla con llama-server el solo.

Entre columna y columna no hay sitio para etiquetas, asi que NO las lleva: lo que dirian
esta escrito en el texto de cada tarjeta, que es donde se lee sin apretar.

Se autocomprueba ANTES de escribir: que ningun texto se salga de su tarjeta ni de la
columna, que ninguna tarjeta se pise, que ninguna flecha cruce una tarjeta que no sea su
origen o su destino, y que las etiquetas no pisen nada.

    python diagrama.py     # escribe docs/arquitectura.svg
"""

import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "docs", "arquitectura.svg")

# --- tokens, copiados de DESIGN.md --------------------------------------------
PANEL = "#E4E5DF"
PAPEL = "#FAFAF7"
TINTA = "#1A1C1B"
TXT2 = "#4A4F49"
TXT3 = "#606560"
HAIRLINE = "#CFD1C9"
HAIRLINE2 = "#B9BDB3"
REGLA = "#1B4D3E"          # verde de escala: la via de decision
CURSOR = "#B4321F"         # rojo de cursor: solo el multiplicador
CHAT = "#606560"           # la via de chat, apagada a proposito

SANS = "Bahnschrift, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
MONO = "Consolas, ui-monospace, SFMono-Regular, Menlo, monospace"

ANCHO, ALTO = 1400, 1050
ZX, ZY, ZW, ZH = 247, 272, 1140, 684      # la frontera de "tu equipo"

# Las cinco columnas y sus anchos. Se declaran UNA vez: las conexiones, las etiquetas y
# las comprobaciones leen de aqui, asi que no pueden desincronizarse.
COL_ENTRADA, W_ENTRADA = 40, 190           # 40 - 230
COL_CLIENTE, W_CLIENTE = 260, 190          # 260 - 450
COL_API, W_API = 485, 185                  # 485 - 670
COL_MODELO, W_MODELO = 705, 185            # 705 - 890
COL_VIA_A, COL_VIA_B, W_VIA = 915, 1155, 228

FILA_1, FILA_2, FILA_3, FILA_4 = 300, 400, 500, 600    # las cuatro filas de arriba
FILA_VIA, FILA_SALIDA = 730, 850           # las vias y sus salidas
H = 76                                     # alto de tarjeta

CX_MODELO = COL_MODELO + W_MODELO / 2
CX_API = COL_API + W_API / 2
CX_CLIENTE = COL_CLIENTE + W_CLIENTE / 2
CX_VIA_A = COL_VIA_A + W_VIA / 2
CX_VIA_B = COL_VIA_B + W_VIA / 2
FORK_X = 907                               # por donde sale la bifurcacion del servidor
Y_FORK = FILA_VIA - 20
# Dos carriles para las dos lineas que van de la fila 4 hacia arriba por la columna del
# cliente: si compartieran x, se pisarian.
CARRIL_SUBIDA, CARRIL_VUELTA = 395, 415
CARRIL_API = 615                           # el bajante de api.py a documento.py


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ancho_texto(t, tam=13, negrita=False):
    """Ancho aproximado, para no dibujar texto que no cabe."""
    return len(t) * tam * (0.58 if negrita else 0.55)


def icono(cx, cy, tipo, color):
    """Iconos dibujados a mano: SVG puro, un solo grosor de trazo, sin dependencias."""
    if tipo == "terminal":
        return (f'<rect x="{cx-12}" y="{cy-10}" width="24" height="20" rx="2" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<path d="M {cx-7} {cy-4} l 3.5 4 l -3.5 4" fill="none" '
                f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
                f'<line x1="{cx+1}" y1="{cy+4}" x2="{cx+7}" y2="{cy+4}" '
                f'stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>')
    if tipo == "navegador":
        return (f'<rect x="{cx-12}" y="{cy-10}" width="24" height="20" rx="2" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<line x1="{cx-12}" y1="{cy-4}" x2="{cx+12}" y2="{cy-4}" '
                f'stroke="{color}" stroke-width="1.6"/>'
                f'<circle cx="{cx-8}" cy="{cy-7}" r="1.3" fill="{color}"/>')
    if tipo == "documento":
        return (f'<path d="M {cx-9} {cy-12} h 13 l 6 6 v 18 h -19 z" fill="none" '
                f'stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
                f'<path d="M {cx+4} {cy-12} v 6 h 6" fill="none" stroke="{color}" '
                f'stroke-width="1.6" stroke-linejoin="round"/>'
                f'<line x1="{cx-5}" y1="{cy+2}" x2="{cx+5}" y2="{cy+2}" '
                f'stroke="{color}" stroke-width="1.4"/>')
    if tipo == "texto":                       # el texto ya extraido
        return "".join(
            f'<line x1="{cx-11}" y1="{cy-8+i*6}" x2="{cx+11-i*4}" y2="{cy-8+i*6}" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
            for i in range(4))
    if tipo == "lista":
        return "".join(
            f'<line x1="{cx-10}" y1="{cy-7+i*7}" x2="{cx+10}" y2="{cy-7+i*7}" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<circle cx="{cx-13}" cy="{cy-7+i*7}" r="1.6" fill="{color}"/>'
            for i in range(3))
    if tipo == "chip":
        patas = "".join(
            f'<line x1="{cx-12+i*6}" y1="{cy-13}" x2="{cx-12+i*6}" y2="{cy-8}" '
            f'stroke="{color}" stroke-width="1.5"/>'
            f'<line x1="{cx-12+i*6}" y1="{cy+8}" x2="{cx-12+i*6}" y2="{cy+13}" '
            f'stroke="{color}" stroke-width="1.5"/>' for i in range(5))
        return (patas + f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="2" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<rect x="{cx-4}" y="{cy-3}" width="8" height="6" rx="1" '
                f'fill="{color}" opacity="0.6"/>')
    if tipo == "servidor":
        return (f'<rect x="{cx-13}" y="{cy-12}" width="26" height="10" rx="2" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<rect x="{cx-13}" y="{cy+2}" width="26" height="10" rx="2" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<circle cx="{cx-7}" cy="{cy-7}" r="1.6" fill="{color}"/>'
                f'<circle cx="{cx-7}" cy="{cy+7}" r="1.6" fill="{color}"/>')
    if tipo == "rayo":
        return (f'<path d="M {cx+3} {cy-12} L {cx-7} {cy+1} L {cx-1} {cy+1} '
                f'L {cx-4} {cy+12} L {cx+8} {cy-2} L {cx+1} {cy-2} Z" '
                f'fill="{color}"/>')
    if tipo == "burbuja":
        return (f'<path d="M {cx-12} {cy-9} h 24 a 4 4 0 0 1 4 4 v 9 a 4 4 0 0 1 -4 4 '
                f'h -12 l -6 6 v -6 h -6 a 4 4 0 0 1 -4 -4 v -9 a 4 4 0 0 1 4 -4 z" '
                f'fill="none" stroke="{color}" stroke-width="1.6" '
                f'stroke-linejoin="round"/>')
    if tipo == "escala":
        ticks = "".join(f'<line x1="{cx-14+i*7}" y1="{cy+7}" x2="{cx-14+i*7}" '
                        f'y2="{cy+(1 if i % 2 else 4)}" stroke="{color}" '
                        f'stroke-width="1.4"/>' for i in range(5))
        return (ticks + f'<line x1="{cx-14}" y1="{cy+7}" x2="{cx+14}" y2="{cy+7}" '
                f'stroke="{color}" stroke-width="1.6"/>'
                f'<line x1="{cx-3}" y1="{cy-9}" x2="{cx-3}" y2="{cy+7}" '
                f'stroke="{CURSOR}" stroke-width="2"/>')
    if tipo == "objetivo":
        return (f'<circle cx="{cx}" cy="{cy}" r="11" fill="none" stroke="{color}" '
                f'stroke-width="1.6"/>'
                f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{color}"/>')
    return ""


def tarjeta(x, y, w, h, titulo, lineas, color, tipo=None, mono=None, destacada=False):
    """Tarjeta sobre el panel. La elevacion es tonal y el borde dice lo que importa.

    Sin pildora de etiqueta: la tenia y pisaba el titulo. Lo que decia cabe en las
    lineas, que es donde se lee sin apretar.
    """
    borde = (f'stroke="{color}" stroke-opacity="0.55"' if destacada
             else f'stroke="{HAIRLINE2}"')
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{PAPEL}" '
         f'{borde} stroke-width="{2 if destacada else 1}"/>']

    xi = x + (54 if tipo else 16)
    if tipo:
        p.append(f'<circle cx="{x+27}" cy="{y+h/2}" r="16" '
                 f'fill="{color}" fill-opacity="0.10"/>')
        p.append(icono(x + 27, y + h / 2, tipo, color))

    fam = MONO if mono else SANS
    tam_tit = 13.5 if mono else 14
    alto_txt = 18 + len(lineas) * 15
    y0 = y + (h - alto_txt) / 2 + 13
    p.append(f'<text x="{xi}" y="{y0}" font-family="{fam}" font-size="{tam_tit}" '
             f'font-weight="600" letter-spacing="-0.2" fill="{TINTA}">'
             f'{esc(titulo)}</text>')
    for i, ln in enumerate(lineas):
        p.append(f'<text x="{xi}" y="{y0 + 17 + i*15}" font-family="{SANS}" '
                 f'font-size="11.5" fill="{TXT3}">{esc(ln)}</text>')
    return "\n".join(p)


def metrica(x, y, valor, pie, color, tipo):
    """Tarjeta de metrica: el numero grande, en monoespaciada porque es una medida."""
    w, h = 300, 92
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{PAPEL}" '
        f'stroke="{HAIRLINE2}" stroke-width="1"/>',
        icono(x + 34, y + h / 2, tipo, color),
        f'<text x="{x + 62}" y="{y + 44}" font-family="{MONO}" font-size="28" '
        f'font-weight="600" letter-spacing="-1" fill="{color}">{esc(valor)}</text>',
        f'<text x="{x + 62}" y="{y + 66}" font-family="{SANS}" font-size="11.5" '
        f'fill="{TXT3}">{esc(pie)}</text>',
    ])


def rotulo_columna(x, numero, texto):
    """El rotulo de columna: numerado, para que la direccion del flujo sea inequivoca."""
    return "\n".join([
        f'<circle cx="{x+11}" cy="{ZY-26}" r="11" fill="{REGLA}"/>',
        f'<text x="{x+11}" y="{ZY-22}" text-anchor="middle" font-family="{MONO}" '
        f'font-size="12" font-weight="600" fill="{PANEL}">{numero}</text>',
        f'<text x="{x+30}" y="{ZY-21}" font-family="{SANS}" font-size="11.5" '
        f'font-weight="600" letter-spacing="1.6" fill="{TXT3}">{esc(texto)}</text>',
    ])


def pildora(x, y, texto, color):
    """La etiqueta de una flecha: una pastilla sobre el papel, con su texto."""
    an = ancho_texto(texto, 11, True) + 22
    return "\n".join([
        f'<rect x="{x - an/2}" y="{y - 12}" width="{an}" height="24" rx="2" '
        f'fill="{PAPEL}" stroke="{HAIRLINE2}" stroke-width="1"/>',
        f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-family="{SANS}" '
        f'font-size="11" font-weight="600" fill="{color}">{esc(texto)}</text>',
    ])


def flecha(x1, y1, x2, y2, color, opacidad=1.0, ancho=1.8, trazos=False):
    """Una flecha recta. El trazo es mas grueso que un borde: una flecha no es un marco."""
    guion = ' stroke-dasharray="5,4"' if trazos else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-opacity="{opacidad}" stroke-width="{ancho}"{guion} '
            f'stroke-linecap="round" marker-end="url(#punta-{color[1:]})"/>')


def codo(x1, y1, x2, y2, color, radio=10, opacidad=1.0, ancho=1.8, trazos=False):
    """Un codo recto con la esquina redondeada: mas legible que una curva S cuando el
    recorrido no es de arriba abajo."""
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    guion = ' stroke-dasharray="5,4"' if trazos else ""
    return (f'<path d="M {x1} {y1} L {x2 - sx*radio} {y1} '
            f'Q {x2} {y1} {x2} {y1 + sy*radio} L {x2} {y2}" fill="none" '
            f'stroke="{color}" stroke-opacity="{opacidad}" stroke-width="{ancho}"'
            f'{guion} stroke-linecap="round" marker-end="url(#punta-{color[1:]})"/>')


# (titulo, x, y, w, h, lineas, color, icono, mono, destacada, dentro)
CAJAS = [
    # --- 1. las entradas. De donde viene lo que se pregunta. Fuera de la maquina. ---
    ("Tú escribes", COL_ENTRADA, FILA_1, W_ENTRADA, H, ["el caso, a mano"],
     TXT3, "terminal", False, False, False),
    ("Navegador", COL_ENTRADA, FILA_2, W_ENTRADA, H, ["la interfaz web"],
     TXT3, "navegador", False, False, False),
    ("curl / Postman", COL_ENTRADA, FILA_3, W_ENTRADA, H, ["sin el cliente"],
     TXT3, "terminal", False, False, False),
    ("Un documento", COL_ENTRADA, FILA_4, W_ENTRADA, H, ["pdf · docx · txt"],
     TXT3, "documento", False, False, False),

    # --- 2. el cliente: lo que usas. La consola, y la interfaz en el navegador. ---
    ("preguntar.py", COL_CLIENTE, FILA_1, W_CLIENTE, H, ["la consola",
                                                        "lee la cabecera"],
     REGLA, "lista", True, True, True),
    ("web/index.html", COL_CLIENTE, FILA_2, W_CLIENTE, H, ["la interfaz",
                                                           "aquí preguntas"],
     REGLA, "navegador", True, True, True),

    # --- 3. la API: un servidor, no el cliente. Recibe y pasa al modelo. ---
    ("api.py", COL_API, FILA_2, W_API, H, ["recibe el input",
                                           "y las preguntas"],
     REGLA, "servidor", True, True, True),
    ("documento.py", COL_API, FILA_4, W_API, H, ["saca el texto",
                                                 "del documento"],
     REGLA, "texto", True, True, True),

    # --- 4. el modelo y lo que necesita para funcionar. ---
    ("llama-server", COL_MODELO, FILA_2, W_MODELO, H, ["un solo proceso",
                                                       "Vulkan · RX 9070"],
     REGLA, "servidor", True, True, True),
    ("Spark-X2.5-4B", COL_MODELO, FILA_3, W_MODELO, H, ["Q8_0",
                                                        "9 GB en VRAM"],
     TXT3, "chip", False, False, True),

    # --- 5. las dos vias: no son del sistema, son de la peticion. ---
    ("/v1/decision", COL_VIA_A, FILA_VIA, W_VIA, H, ["PUNTÚA las opciones",
                                                     "no genera ni un token"],
     REGLA, "rayo", True, True, True),
    ("/v1/chat/completions", COL_VIA_B, FILA_VIA, W_VIA, H, ["GENERA texto",
                                                             "token a token"],
     CHAT, "burbuja", True, False, True),

    # --- y sus salidas. ---
    ("Valor listo", COL_VIA_A, FILA_SALIDA, W_VIA, H, ["+ prob. + confianza"],
     REGLA, "escala", False, True, True),
    ("Prosa", COL_VIA_B, FILA_SALIDA, W_VIA, H, ["hay que interpretarla"],
     CHAT, "burbuja", False, False, True),
]

# Las etiquetas de las flechas, declaradas APARTE de las flechas: asi se puede comprobar
# que ninguna pildora pisa una tarjeta ni a otra pildora.
# (texto, x del centro, y del centro, color)
ETIQUETAS = [
    ("la petición elige la vía", 1091, Y_FORK - 32, REGLA),
]

# Los tramos de flecha, para comprobar que ninguno pasa por encima de una tarjeta.
# (x1, y1, x2, y2)
SEGMENTOS = [
    # 1 -> 2: las entradas, a lo que las usa
    (COL_ENTRADA + W_ENTRADA, FILA_1 + H/2, COL_CLIENTE, FILA_1 + H/2),
    (COL_ENTRADA + W_ENTRADA, FILA_2 + H/2, COL_CLIENTE, FILA_2 + H/2),
    (COL_ENTRADA + W_ENTRADA, FILA_3 + H/2, CARRIL_API - 55, FILA_3 + H/2),
    (CARRIL_API - 55, FILA_3 + H/2, CARRIL_API - 55, FILA_2 + H),
    (COL_ENTRADA + W_ENTRADA, FILA_4 + H/2, CARRIL_SUBIDA, FILA_4 + H/2),
    (CARRIL_SUBIDA, FILA_4 + H/2, CARRIL_SUBIDA, FILA_2 + H),
    # 2: el cliente, a la API (y la consola, directa al modelo)
    (COL_CLIENTE + W_CLIENTE, FILA_2 + H/2, COL_API, FILA_2 + H/2),
    (COL_CLIENTE + W_CLIENTE, FILA_1 + H/2, CX_MODELO, FILA_1 + H/2),
    (CX_MODELO, FILA_1 + H/2, CX_MODELO, FILA_2),
    # 3: la API, al modelo
    (COL_API + W_API, FILA_2 + H/2, COL_MODELO, FILA_2 + H/2),
    # y la vuelta: documento.py devuelve el texto al cliente, que lo manda como `input`
    (COL_API, FILA_4 + H/2, CARRIL_VUELTA, FILA_4 + H/2),
    (CARRIL_VUELTA, FILA_4 + H/2, CARRIL_VUELTA, FILA_2 + H),
    (CARRIL_API, FILA_2 + H, CARRIL_API, FILA_4),
    # 4: el modelo carga el peso, y de el salen las dos vias
    (CX_MODELO, FILA_3, CX_MODELO, FILA_2 + H),
    (COL_MODELO + W_MODELO, FILA_2 + H/2, FORK_X, FILA_2 + H/2),
    (FORK_X, FILA_2 + H/2, FORK_X, Y_FORK),
    (FORK_X, Y_FORK, CX_VIA_A, Y_FORK),
    (FORK_X, Y_FORK, CX_VIA_B, Y_FORK),
    (CX_VIA_A, Y_FORK, CX_VIA_A, FILA_VIA),
    (CX_VIA_B, Y_FORK, CX_VIA_B, FILA_VIA),
    # 5: y cada via, a su salida
    (CX_VIA_A, FILA_VIA + H, CX_VIA_A, FILA_SALIDA),
    (CX_VIA_B, FILA_VIA + H, CX_VIA_B, FILA_SALIDA),
]


def caja_de_etiqueta(texto, x, y):
    """El rectangulo que ocupa una pildora, para poder comprobarla."""
    an = ancho_texto(texto, 11, True) + 22
    return (x - an/2, y - 12, an, 24)


def choca(a, b, margen=0):
    """Si dos rectangulos (x, y, w, h) se solapan."""
    return (a[0] < b[0] + b[2] + margen and b[0] < a[0] + a[2] + margen
            and a[1] < b[1] + b[3] + margen and b[1] < a[1] + a[3] + margen)


def comprobar():
    """Todo lo que puede salir mal en un diagrama dibujado a mano, comprobado."""
    fallos = []
    for tit, x, y, w, h, lns, _c, ic, mono, _d, dentro in CAJAS:
        necesita = (54 if ic else 16) + max(
            [ancho_texto(tit, 13.5 if mono else 14, True)]
            + [ancho_texto(l, 11.5) for l in lns])
        if necesita > w - 12:
            fallos.append(f"«{tit}»: el texto pide {necesita:.0f}px, la caja tiene {w}")
        # El texto tiene que caber DENTRO de su tarjeta, con aire arriba y abajo. Es lo
        # que garantiza que un titulo largo no se salga ni pise a la linea de al lado.
        alto_txt = 18 + len(lns) * 15
        y0 = y + (h - alto_txt) / 2 + 13
        if y0 - 11 < y + 4 or y0 + 17 + (len(lns) - 1) * 15 + 4 > y + h - 4:
            fallos.append(f"«{tit}»: el texto no cabe en su tarjeta")
        if x < 10 or x + w > ANCHO - 10 or y < 0 or y + h > ALTO:
            fallos.append(f"«{tit}» se sale del lienzo")
        if dentro and (x < ZX or x + w > ZX + ZW or y < ZY or y + h > ZY + ZH):
            fallos.append(f"«{tit}» cruza la frontera de TU EQUIPO")
        if not dentro and x + w > ZX:
            fallos.append(f"«{tit}» debería quedar fuera de la frontera")

    rect_cajas = [(c[1], c[2], c[3], c[4]) for c in CAJAS]
    titulos = [c[0] for c in CAJAS]
    for i, a in enumerate(rect_cajas):
        for j in range(i + 1, len(rect_cajas)):
            if choca(a, rect_cajas[j]):
                fallos.append(f"«{titulos[i]}» y «{titulos[j]}» se pisan")

    # LAS ETIQUETAS: que ninguna pise una tarjeta, ni a otra etiqueta, ni se salga.
    rect_etq = [(t, caja_de_etiqueta(t, x, y)) for t, x, y, _c in ETIQUETAS]
    for texto, (ex, ey, ew, eh) in rect_etq:
        if ex < 10 or ex + ew > ANCHO - 10 or ey < 0 or ey + eh > ALTO:
            fallos.append(f"la etiqueta «{texto}» se sale del lienzo")
        for k, c in enumerate(rect_cajas):
            if choca((ex, ey, ew, eh), c, margen=6):
                fallos.append(f"la etiqueta «{texto}» pisa la tarjeta «{titulos[k]}»")
    for i, (ta, ra) in enumerate(rect_etq):
        for tb, rb in rect_etq[i+1:]:
            if choca(ra, rb, margen=6):
                fallos.append(f"las etiquetas «{ta}» y «{tb}» se pisan")

    # Ninguna flecha puede cruzar por encima de una tarjeta que no sea su origen o su
    # destino: es el fallo que hace ilegible un diagrama de flujo.
    def dentro_de(px, py, caja):
        return (caja[1] < px < caja[1] + caja[3]
                and caja[2] < py < caja[2] + caja[4])

    def toca_extremo(x1, y1, x2, y2, caja):
        for px, py in ((x1, y1), (x2, y2)):
            # Un extremo DENTRO de la caja no exime: es justo lo que hay que cazar.
            if dentro_de(px, py, caja):
                continue
            if (caja[1] - 3 <= px <= caja[1] + caja[3] + 3
                    and caja[2] - 3 <= py <= caja[2] + caja[4] + 3):
                return True
        return False

    for (x1, y1, x2, y2) in SEGMENTOS:
        for caja in CAJAS:
            if toca_extremo(x1, y1, x2, y2, caja):
                continue
            for k in range(1, 12):
                px = x1 + (x2 - x1) * k / 12
                py = y1 + (y2 - y1) * k / 12
                if dentro_de(px, py, caja):
                    fallos.append(f"una flecha pasa por encima de «{caja[0]}»")
                    break

    if ZY + ZH > ALTO - 90:
        fallos.append("la frontera no deja sitio para la leyenda")
    if ZY - 40 < 226:
        fallos.append("los rotulos de columna pisan las metricas")
    return fallos


def main():
    fallos = comprobar()
    if fallos:
        print("  FALLOS:")
        for f_ in fallos:
            print("   -", f_)
        raise SystemExit(1)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" '
         f'width="{ANCHO}" height="{ALTO}">', "<defs>",
         # La reticula de medida: las graduaciones de la regla, a escala de pagina.
         f'<pattern id="reticula" width="36" height="36" patternUnits="userSpaceOnUse">'
         f'<path d="M0 0v36M0 0h36" stroke="{HAIRLINE}" stroke-opacity="0.42" '
         f'stroke-width="1"/></pattern>']
    for c in (REGLA, CHAT, TXT3, CURSOR):
        s.append(f'<marker id="punta-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
    s.append("</defs>")

    # ---------------------------------------------------------- fondo
    s.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="{PANEL}"/>')
    s.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="url(#reticula)"/>')

    # ---------------------------------------------------------- cabecera
    s.append(f'<rect x="48" y="40" width="42" height="42" rx="3" fill="{REGLA}"/>')
    s.append(f'<path d="M 62 54 h 14 M 62 62 h 14 M 62 70 h 8" stroke="{PAPEL}" '
             f'stroke-width="2.2" stroke-linecap="round"/>')
    s.append(f'<text x="108" y="62" font-family="{SANS}" font-size="25" '
             f'font-weight="600" letter-spacing="-0.9" fill="{TINTA}">'
             f'AIOM: un cliente, una API, un modelo, dos formas de preguntar</text>')
    s.append(f'<text x="108" y="84" font-family="{SANS}" font-size="13" '
             f'letter-spacing="-0.1" fill="{TXT3}">El cliente manda UNA petición con el '
             f'input —el texto del documento, si lo hay— y las preguntas; la API se la '
             f'pasa a llama-server, que la atiende por una de sus dos vías.</text>')
    s.append(f'<rect x="{ANCHO-232}" y="48" width="184" height="26" rx="2" '
             f'fill="{PAPEL}" stroke="{HAIRLINE2}" stroke-width="1"/>')
    s.append(f'<circle cx="{ANCHO-212}" cy="61" r="3.5" fill="{REGLA}"/>')
    s.append(f'<text x="{ANCHO-200}" y="65" font-family="{MONO}" font-size="11" '
             f'fill="{TXT2}">local · sin red · sin nube</text>')

    # ---------------------------------------------------------- metricas
    for k, (val, pie, col, ic) in enumerate((
            ("0 tokens", "por respuesta de decisión", REGLA, "rayo"),
            ("2,7×", "más rápido que el chat, 1 pregunta", CURSOR, "objetivo"),
            ("9,8×", "más rápido con 15 encadenadas", CURSOR, "objetivo"),
            ("85,6%", "de acierto con una pregunta", TXT2, "escala"))):
        s.append(metrica(48 + k * 326, 130, val, pie, col, ic))

    # ---------------------------------------------------------- frontera
    s.append(f'<rect x="{ZX}" y="{ZY}" width="{ZW}" height="{ZH}" rx="4" '
             f'fill="{PAPEL}" fill-opacity="0.45" stroke="{HAIRLINE2}" '
             f'stroke-width="1" stroke-dasharray="7,6"/>')
    s.append(f'<text x="{ZX+18}" y="{ZY+24}" font-family="{SANS}" font-size="11.5" '
             f'font-weight="600" letter-spacing="1.6" fill="{TXT3}">TU EQUIPO</text>')

    # ---------------------------------------------------------- rotulos de columna
    for x, num, txt in ((COL_ENTRADA, "1", "ENTRADAS"),
                        (COL_CLIENTE, "2", "EL CLIENTE"),
                        (COL_API, "3", "LA API"),
                        (COL_MODELO, "4", "EL MODELO"),
                        (COL_VIA_A, "5", "LAS DOS VÍAS")):
        s.append(rotulo_columna(x, num, txt))

    # ---------------------------------------------------------- flechas
    # 1 -> 2: las entradas, a lo que las usa.
    s.append(flecha(COL_ENTRADA + W_ENTRADA, FILA_1 + H/2, COL_CLIENTE, FILA_1 + H/2,
                    TXT3, ancho=1.5))
    s.append(flecha(COL_ENTRADA + W_ENTRADA, FILA_2 + H/2, COL_CLIENTE, FILA_2 + H/2,
                    TXT3, ancho=1.5))
    # curl y Postman entran directos a la API, sin pasar por el cliente.
    s.append(codo(COL_ENTRADA + W_ENTRADA, FILA_3 + H/2, CARRIL_API - 55,
                  FILA_2 + H, TXT3, ancho=1.5))
    # y el documento: se sube desde el cliente, por eso la linea sube por su columna.
    s.append(codo(COL_ENTRADA + W_ENTRADA, FILA_4 + H/2, CARRIL_SUBIDA, FILA_2 + H,
                  TXT3, ancho=1.5))
    # 2: el cliente, a la API. Y la consola, directa al modelo: no pasa por la API.
    s.append(flecha(COL_CLIENTE + W_CLIENTE, FILA_2 + H/2, COL_API, FILA_2 + H/2, REGLA))
    s.append(codo(COL_CLIENTE + W_CLIENTE, FILA_1 + H/2, CX_MODELO, FILA_2, REGLA))
    # 3: la API, al modelo.
    s.append(flecha(COL_API + W_API, FILA_2 + H/2, COL_MODELO, FILA_2 + H/2, REGLA,
                    ancho=2.2))
    # y la vuelta del documento: api.py lo extrae y le devuelve el texto al cliente.
    s.append(codo(CX_API, FILA_2 + H, CARRIL_API, FILA_4, REGLA, opacidad=0.85,
                  ancho=1.5))
    s.append(codo(COL_API, FILA_4 + H/2, CARRIL_VUELTA, FILA_2 + H, TXT3, ancho=1.5,
                  trazos=True))
    # 4: el modelo, cargado, y de el salen las dos vias.
    s.append(flecha(CX_MODELO, FILA_3, CX_MODELO, FILA_2 + H, TXT3, opacidad=0.8,
                    ancho=1.5))
    s.append(codo(COL_MODELO + W_MODELO, FILA_2 + H/2, FORK_X, Y_FORK, REGLA))
    s.append(f'<line x1="{FORK_X}" y1="{Y_FORK}" x2="{CX_VIA_B}" y2="{Y_FORK}" '
             f'stroke="{REGLA}" stroke-width="1.8" stroke-linecap="round"/>')
    s.append(flecha(CX_VIA_A, Y_FORK, CX_VIA_A, FILA_VIA, REGLA))
    s.append(flecha(CX_VIA_B, Y_FORK, CX_VIA_B, FILA_VIA, CHAT, opacidad=0.85))
    # 5: cada via, a su salida.
    s.append(flecha(CX_VIA_A, FILA_VIA + H, CX_VIA_A, FILA_SALIDA, REGLA))
    s.append(flecha(CX_VIA_B, FILA_VIA + H, CX_VIA_B, FILA_SALIDA, CHAT, opacidad=0.85))

    # ---------------------------------------------------------- tarjetas y etiquetas
    for (tit, x, y, w, h, lns, col, ic, mono, dest, _d) in CAJAS:
        s.append(tarjeta(x, y, w, h, tit, lns, col, ic, mono, dest))
    # Las etiquetas van DESPUES de las tarjetas: si alguna se acercara, el papel de la
    # pildora tapa el borde en vez de que el borde corte el texto.
    for texto, x, y, color in ETIQUETAS:
        s.append(pildora(x, y, texto, color))

    # ---------------------------------------------------------- leyenda
    ly = ALTO - 46
    s.append(f'<line x1="48" y1="{ly-30}" x2="{ANCHO-48}" y2="{ly-30}" '
             f'stroke="{HAIRLINE}" stroke-width="1"/>')
    s.append(f'<text x="48" y="{ly}" font-family="{SANS}" font-size="11.5" '
             f'font-weight="600" letter-spacing="1.6" fill="{TXT3}">LEYENDA</text>')
    x = 168
    for nombre, col, dest, trazos in (
            ("Entrada del usuario", TXT3, False, False),
            ("Vía de decisión · 0 tokens", REGLA, True, False),
            ("Vía de chat · respaldo", CHAT, False, False),
            ("El texto del documento vuelve al cliente", TXT3, False, True)):
        s.append(f'<rect x="{x}" y="{ly-13}" width="20" height="17" rx="2" '
                 f'fill="{PAPEL}" stroke="{col}" '
                 f'stroke-opacity="{0.55 if dest else 0.3}" '
                 f'stroke-width="{2 if dest else 1}"/>')
        if trazos:
            s.append(f'<line x1="{x+3}" y1="{ly-4}" x2="{x+17}" y2="{ly-4}" '
                     f'stroke="{col}" stroke-width="1.5" stroke-dasharray="4,3"/>')
        else:
            s.append(f'<rect x="{x+4}" y="{ly-9}" width="12" height="9" rx="1" '
                     f'fill="{col}" fill-opacity="{0.25 if dest else 0.12}"/>')
        s.append(f'<text x="{x+29}" y="{ly}" font-family="{SANS}" font-size="12" '
                 f'fill="{TXT2}">{esc(nombre)}</text>')
        x += 29 + ancho_texto(nombre, 12) + 34
    s.append(f'<text x="{ANCHO-48}" y="{ly}" text-anchor="end" font-family="{MONO}" '
             f'font-size="11" fill="{TXT3}">cifras medidas aquí · results/</text>')

    s.append("</svg>")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(s))
    print(f"  escrito {SALIDA}  ({ANCHO}x{ALTO})")
    print(f"  {len(CAJAS)} tarjetas, {len(SEGMENTOS)} tramos de flecha y "
          f"{len(ETIQUETAS)} etiquetas: nada se sale, nada se pisa, ninguna flecha "
          f"cruza una tarjeta, la frontera las contiene")


if __name__ == "__main__":
    main()
