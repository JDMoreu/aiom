"""Diagrama de arquitectura de AIOM, en el mismo sistema visual que la interfaz.

Los tokens NO son inventados: son los de DESIGN.md, los mismos que usa web/index.html.
Asi el repositorio entero habla un solo idioma visual.

  - Fondo de panel (#E4E5DF) y ELEVACION POR CAPAS TONALES, no por sombras: la cara de
    la regla (#FAFAF7) esta encima del panel. Un instrumento de precision no flota.
  - Bordes de 1px en hairline (#CFD1C9 / #B9BDB3); 2px solo en lo que esta destacado.
  - Tracking negativo en los tamanos grandes y pesos 400/600 (nunca 700).
  - Monoespaciada para los identificadores tecnicos (llama-server, /v1/decision).
  - DOS acentos con trabajo: el verde de escala (#1B4D3E) para la via de decision y el
    rojo de cursor (#B4321F) reservado al multiplicador. El chat va en gris apagado
    porque ES el respaldo: de-enfatizarlo es lo honesto.

El recorrido que dibuja, de izquierda a derecha:

    las entradas  ->  el cliente  ->  el modelo  ->  las dos vias  ->  las salidas

Se autocomprueba ANTES de escribir: si una etiqueta no cabe en su tarjeta, si dos
tarjetas se pisan o si algo cruza la frontera, falla en vez de dejar un SVG roto.

    python diagrama.py     # escribe docs/arquitectura.svg
"""

import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "docs", "arquitectura.svg")

# --- tokens, copiados de DESIGN.md --------------------------------------------
PANEL = "#E4E5DF"          # el fondo
PAPEL = "#FAFAF7"          # la cara de la regla: las tarjetas
TINTA = "#1A1C1B"          # texto principal
TXT2 = "#4A4F49"           # secundario
TXT3 = "#606560"           # terciario
HAIRLINE = "#CFD1C9"
HAIRLINE2 = "#B9BDB3"
REGLA = "#1B4D3E"          # verde de escala: la via de decision
CURSOR = "#B4321F"         # rojo de cursor: solo el multiplicador
CHAT = "#606560"           # la via de chat, apagada a proposito

SANS = "Bahnschrift, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
MONO = "Consolas, ui-monospace, SFMono-Regular, Menlo, monospace"

ANCHO, ALTO = 1400, 1040
# La frontera de "tu equipo". Dentro corre todo; fuera queda por donde entra el usuario.
ZX, ZY, ZW, ZH = 300, 288, 1000, 648

# Las columnas del recorrido. Se declaran aqui para que las conexiones y las
# comprobaciones usen los mismos numeros y no puedan desincronizarse.
COL_ENTRADA, COL_CLIENTE, COL_SERVIDOR, COL_VIA = 48, 330, 650, 970
W_COL = 240
CENTRO = COL_VIA + 125


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ancho_texto(t, tam=13, negrita=False):
    """Ancho aproximado, para no dibujar etiquetas que no caben."""
    return len(t) * tam * (0.58 if negrita else 0.55)


def icono(cx, cy, tipo, color):
    """Iconos dibujados a mano: SVG puro, sin dependencias ni fuentes de iconos."""
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
        # La marca del sistema: la escala graduada con su cursor.
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


def tarjeta(x, y, w, h, titulo, lineas, color, tipo=None, etiqueta=None,
            mono=None, destacada=False):
    """Tarjeta sobre el panel. La elevacion es tonal y el borde dice lo que importa."""
    borde = (f'stroke="{color}" stroke-opacity="0.55"' if destacada
             else f'stroke="{HAIRLINE2}"')
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{PAPEL}" '
         f'{borde} stroke-width="{2 if destacada else 1}"/>']

    xi = x + (56 if tipo else 16)
    if tipo:
        p.append(f'<circle cx="{x+28}" cy="{y+h/2}" r="16" '
                 f'fill="{color}" fill-opacity="0.10"/>')
        p.append(icono(x + 28, y + h / 2, tipo, color))

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

    if etiqueta:
        tw = ancho_texto(etiqueta, 9.5, True) + 18
        p.append(f'<rect x="{x + w - tw - 10}" y="{y + 9}" width="{tw}" height="18" '
                 f'rx="2" fill="{color}" fill-opacity="0.12"/>')
        p.append(f'<text x="{x + w - tw/2 - 10}" y="{y + 21.5}" text-anchor="middle" '
                 f'font-family="{MONO}" font-size="9.5" fill="{color}">'
                 f'{esc(etiqueta)}</text>')
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


def rotulo(x, y, texto):
    """El rotulo de columna: en versalitas espaciadas, como en la interfaz."""
    return (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="11.5" '
            f'font-weight="600" letter-spacing="1.6" fill="{TXT3}">{esc(texto)}</text>')


def pildora(x, y, texto, color):
    """La etiqueta de una flecha, en una pastilla sobre el papel."""
    an = ancho_texto(texto, 11, True) + 22
    return "\n".join([
        f'<rect x="{x - an/2}" y="{y - 12}" width="{an}" height="24" rx="2" '
        f'fill="{PAPEL}" stroke="{HAIRLINE}" stroke-width="1"/>',
        f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-family="{SANS}" '
        f'font-size="11" font-weight="600" fill="{color}">{esc(texto)}</text>',
    ])


def bezier(x1, y1, x2, y2, color, etiqueta=None, opacidad=1.0):
    """Curva S: mas elegante que un codo y deja claro de donde sale cada rama."""
    dy = (y2 - y1) * 0.5
    p = [f'<path d="M {x1} {y1} C {x1} {y1+dy} {x2} {y2-dy} {x2} {y2}" fill="none" '
         f'stroke="{color}" stroke-opacity="{opacidad}" stroke-width="1.6" '
         f'marker-end="url(#punta-{color[1:]})"/>']
    if etiqueta:
        p.append(pildora((x1 + x2) / 2, (y1 + y2) / 2, etiqueta, color))
    return "\n".join(p)


def recto(x1, y1, x2, y2, color, etiqueta=None, opacidad=1.0, dx=0):
    p = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
         f'stroke-opacity="{opacidad}" stroke-width="1.6" '
         f'marker-end="url(#punta-{color[1:]})"/>']
    if etiqueta:
        p.append(pildora((x1 + x2) / 2 + dx, (y1 + y2) / 2, etiqueta, color))
    return "\n".join(p)


# (titulo, x, y, w, h, lineas, color, icono, etiqueta, mono, destacada, dentro)
CAJAS = [
    # --- las entradas: por donde entra el usuario. Fuera de la maquina. ---
    ("Tú escribes", COL_ENTRADA, 340, 190, 84, ["el caso, a mano"],
     TXT3, "terminal", None, False, False, False),
    ("El navegador", COL_ENTRADA, 444, 190, 84, ["la interfaz web"],
     TXT3, "navegador", None, False, False, False),
    ("Un documento", COL_ENTRADA, 548, 190, 84, ["pdf · docx · txt"],
     TXT3, "documento", None, False, False, False),

    # --- el cliente: lo que lee lo que escribes y arma la peticion. ---
    ("preguntar.py", COL_CLIENTE, 340, W_COL, 84, ["lee la cabecera", "y deduce el tipo"],
     REGLA, "lista", "por consola", True, True, True),
    ("api.py", COL_CLIENTE, 444, W_COL, 84, ["HTTP en el 8100", "sirve la interfaz"],
     REGLA, "servidor", "la puerta", True, True, True),
    ("documento.py", COL_CLIENTE, 548, W_COL, 84, ["saca el texto", "del documento"],
     REGLA, "documento", None, True, False, True),

    # --- el modelo y lo que necesita para funcionar. ---
    ("llama-server", COL_SERVIDOR, 444, W_COL, 96, ["un solo proceso", "Vulkan · local"],
     REGLA, "servidor", "RX 9070", True, True, True),
    ("Spark-X2.5-4B", COL_SERVIDOR, 320, W_COL, 78, ["Q8_0 · ~9 GB en VRAM"],
     TXT3, "chip", None, False, False, True),
    ("Catálogo de campos", COL_SERVIDOR, 580, W_COL, 78, ["qué se puede preguntar"],
     TXT3, "lista", "catalogs/*.json", False, False, True),

    # --- las dos vias: no son del sistema, son de la peticion. ---
    ("/v1/decision", COL_VIA, 340, 250, 92, ["PUNTÚA las opciones", "no genera ni un token"],
     REGLA, "rayo", "0 tokens", True, True, True),
    ("/v1/chat/completions", COL_VIA, 452, 250, 92, ["GENERA texto", "token a token"],
     CHAT, "burbuja", "respaldo", True, False, True),

    # --- las salidas. ---
    ("Valor listo para usar", COL_VIA, 590, 250, 78, ["+ probabilidad + confianza"],
     REGLA, "escala", None, False, True, True),
    ("Prosa", COL_VIA, 700, 250, 78, ["hay que interpretarla"],
     CHAT, "burbuja", None, False, False, True),
]


def comprobar():
    """Todo lo que puede salir mal en un diagrama dibujado a mano, comprobado."""
    fallos = []
    for tit, x, y, w, h, lns, _c, ic, etq, mono, _d, dentro in CAJAS:
        necesita = (56 if ic else 16) + max(
            [ancho_texto(tit, 13.5 if mono else 14, True)]
            + [ancho_texto(l, 11.5) for l in lns])
        if necesita > w - 12:
            fallos.append(f"«{tit}»: el texto pide {necesita:.0f}px, la caja tiene {w}")
        if x < 10 or x + w > ANCHO - 10 or y < 0 or y + h > ALTO:
            fallos.append(f"«{tit}» se sale del lienzo")
        if dentro and (x < ZX or x + w > ZX + ZW or y < ZY or y + h > ZY + ZH):
            fallos.append(f"«{tit}» cruza la frontera de TU EQUIPO")
        if not dentro and x + w > ZX:
            fallos.append(f"«{tit}» debería quedar fuera de la frontera")
        if etq and ancho_texto(etq, 9.5, True) + 18 + 10 > w:
            fallos.append(f"«{tit}»: la etiqueta «{etq}» no cabe en la tarjeta")
    # Ninguna tarjeta puede pisar a otra.
    for i, a in enumerate(CAJAS):
        for b in CAJAS[i+1:]:
            if (a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
                    and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]):
                fallos.append(f"«{a[0]}» y «{b[0]}» se pisan")
    # El lienzo tiene que dar cabida a la frontera y a la leyenda.
    if ZY + ZH > ALTO - 90:
        fallos.append("la frontera no deja sitio para la leyenda")
    # Los rotulos de columna no se pueden solapar entre si.
    xs = [COL_ENTRADA, COL_CLIENTE, COL_SERVIDOR, COL_VIA]
    nombres = ["ENTRADAS", "EL CLIENTE", "EL MODELO", "LAS DOS VÍAS"]
    for i in range(len(xs) - 1):
        if xs[i] + ancho_texto(nombres[i], 11.5, True) + 12 > xs[i+1]:
            fallos.append(f"los rotulos «{nombres[i]}» y «{nombres[i+1]}» se solapan")
    # El rotulo de la bifurcacion no puede salirse por la izquierda.
    l1 = (COL_VIA - 30 + CENTRO) / 2
    if l1 - (ancho_texto("sí · puntúa las opciones", 11, True) + 22) / 2 < COL_SERVIDOR + W_COL:
        fallos.append("el rotulo «sí · puntúa las opciones» se sale por la izquierda")
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
             f'AIOM: un cliente, un servidor, dos formas de preguntar</text>')
    s.append(f'<text x="108" y="84" font-family="{SANS}" font-size="13" '
             f'letter-spacing="-0.1" fill="{TXT3}">El mismo servidor atiende las dos. '
             f'El modo no es del sistema: es una propiedad de la petición.</text>')
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
    for x, nombre in ((COL_ENTRADA, "ENTRADAS"), (COL_CLIENTE, "EL CLIENTE"),
                      (COL_SERVIDOR, "EL MODELO"), (COL_VIA, "LAS DOS VÍAS")):
        s.append(rotulo(x, ZY - 12, nombre))

    # ---------------------------------------------------------- tarjetas
    for (tit, x, y, w, h, lns, col, ic, etq, mono, dest, _d) in CAJAS:
        s.append(tarjeta(x, y, w, h, tit, lns, col, ic, etq, mono, dest))

    # ---------------------------------------------------------- conexiones
    # Las tres entradas entran a su pieza del cliente.
    s.append(recto(238, 382, COL_CLIENTE, 382, TXT3))
    s.append(recto(238, 486, COL_CLIENTE, 486, TXT3))
    s.append(recto(238, 590, COL_CLIENTE, 590, TXT3))
    # El documento alimenta tanto a la API como a la consola.
    s.append(f'<line x1="570" y1="590" x2="640" y2="590" stroke="{TXT3}" '
             f'stroke-width="1.4"/>')
    s.append(f'<line x1="640" y1="590" x2="640" y2="492" stroke="{TXT3}" '
             f'stroke-width="1.4"/>')
    s.append(f'<line x1="640" y1="492" x2="{COL_SERVIDOR}" y2="492" stroke="{TXT3}" '
             f'stroke-width="1.4" marker-end="url(#punta-{TXT3[1:]})"/>')
    # El cliente le pasa el esquema y el texto al servidor.
    s.append(recto(570, 382, COL_SERVIDOR, 442, REGLA, "esquema + texto", dx=-6))
    s.append(recto(570, 486, COL_SERVIDOR, 486, REGLA))
    # El modelo y el catalogo, cargados una vez.
    s.append(recto(COL_SERVIDOR + 120, 398, COL_SERVIDOR + 120, 444, TXT3, None, 0.8))
    s.append(recto(COL_SERVIDOR + 120, 580, COL_SERVIDOR + 120, 540, TXT3, None, 0.8))
    # Y del servidor salen las dos vias, de UN mismo punto.
    s.append(f'<line x1="{COL_SERVIDOR + W_COL}" y1="492" x2="{COL_VIA - 30}" y2="492" '
             f'stroke="{REGLA}" stroke-width="1.6"/>')
    s.append(f'<circle cx="{COL_VIA - 30}" cy="492" r="4.5" fill="{PAPEL}" '
             f'stroke="{REGLA}" stroke-width="1.8"/>')
    s.append(bezier(COL_VIA - 30, 492, CENTRO, 340, REGLA, "sí · puntúa las opciones"))
    s.append(bezier(COL_VIA - 30, 492, CENTRO, 452, CHAT, "no · relevo al chat", 0.85))
    s.append(recto(CENTRO, 432, CENTRO, 590, REGLA))
    s.append(recto(CENTRO, 544, CENTRO, 700, CHAT, opacidad=0.85))

    # ---------------------------------------------------------- leyenda
    ly = ALTO - 46
    s.append(f'<line x1="48" y1="{ly-30}" x2="{ANCHO-48}" y2="{ly-30}" '
             f'stroke="{HAIRLINE}" stroke-width="1"/>')
    s.append(f'<text x="48" y="{ly}" font-family="{SANS}" font-size="11.5" '
             f'font-weight="600" letter-spacing="1.6" fill="{TXT3}">LEYENDA</text>')
    x = 168
    for nombre, col, dest in (("Entrada del usuario", TXT3, False),
                              ("Vía de decisión · 0 tokens", REGLA, True),
                              ("Vía de chat · respaldo", CHAT, False)):
        s.append(f'<rect x="{x}" y="{ly-13}" width="20" height="17" rx="2" '
                 f'fill="{PAPEL}" stroke="{col}" '
                 f'stroke-opacity="{0.55 if dest else 0.3}" '
                 f'stroke-width="{2 if dest else 1}"/>')
        s.append(f'<rect x="{x+4}" y="{ly-9}" width="12" height="9" rx="1" '
                 f'fill="{col}" fill-opacity="{0.25 if dest else 0.12}"/>')
        s.append(f'<text x="{x+29}" y="{ly}" font-family="{SANS}" font-size="12" '
                 f'fill="{TXT2}">{esc(nombre)}</text>')
        x += 29 + ancho_texto(nombre, 12) + 40
    s.append(f'<text x="{ANCHO-48}" y="{ly}" text-anchor="end" font-family="{MONO}" '
             f'font-size="11" fill="{TXT3}">cifras medidas aquí · results/</text>')

    s.append("</svg>")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(s))
    print(f"  escrito {SALIDA}  ({ANCHO}x{ALTO})")
    print(f"  {len(CAJAS)} tarjetas: ninguna se sale, ninguna pisa a otra, "
          f"la frontera las contiene")
    print("  rotulos de columna y de bifurcacion sin solapes: verificado")


if __name__ == "__main__":
    main()
