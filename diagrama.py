"""Diagrama de arquitectura de AIOM, en el lenguaje visual de Linear.

El diagrama anterior era cajas blancas con texto: correcto pero plano. Esto aplica un
sistema de diseno real (los tokens estan sacados del sistema de Linear, no inventados):

  - Fondo near-black (#08090a) y ELEVACION POR PASOS DE LUMINANCIA, no por sombras:
    cada nivel sube un poco la opacidad del blanco (0.02 -> 0.04 -> 0.06).
  - Bordes semi-transparentes (rgba(255,255,255,0.06/0.08)) en vez de bordes solidos:
    dan estructura sin ruido.
  - Tipografia con tracking NEGATIVO en los tamanos grandes y pesos 400/510/590
    (nunca 700, que es el tell de un diagrama hecho a mano).
  - Monoespaciada para los identificadores tecnicos (llama-server, /v1/decision).
  - UN SOLO acento cromatico: el indigo #7170ff para la via de decision. El chat va
    en gris apagado porque ES el respaldo: de-enfatizarlo es lo honesto, y ademas
    es lo que hace el sistema (un acento, no dos colores compitiendo).

Se autocomprueba antes de escribir: si una etiqueta no cabe en su tarjeta, si algo
cruza la frontera o si los dos rotulos de la bifurcacion se pisan, falla.

    python diagrama.py     # escribe docs/arquitectura.svg
"""

import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "docs", "arquitectura.svg")

# --- tokens de Linear ---------------------------------------------------------
FONDO = "#08090a"          # marketing black
PANEL = "#0f1011"          # panel dark
SUPERFICIE = "#191a1b"     # level 3
ELEVADO = "#28282c"        # secondary surface
TXT = "#f7f8f8"            # primary text (no blanco puro)
TXT2 = "#d0d6e0"           # secondary
TXT3 = "#8a8f98"           # tertiary
TXT4 = "#62666d"           # quaternary
ACENTO = "#7170ff"         # accent violet
ACENTO2 = "#828fff"        # accent hover
INDIGO = "#5e6ad2"         # brand indigo
BORDE = "rgba(255,255,255,0.08)"
BORDE_SUAVE = "rgba(255,255,255,0.05)"

SANS = "Segoe UI Variable, Segoe UI, system-ui, -apple-system, sans-serif"
MONO = "Consolas, ui-monospace, SFMono-Regular, Menlo, monospace"

ANCHO, ALTO = 1400, 1120
# La frontera de "tu equipo". Su borde izquierdo (340) tiene que quedar a la derecha
# de la pildora de la flecha de entrada, o la pildora la cruza.
ZX, ZY, ZW, ZH = 340, 262, 920, 750


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ancho_texto(t, tam=13, negrita=False):
    """Ancho aproximado, para no dibujar etiquetas que no caben."""
    return len(t) * tam * (0.58 if negrita else 0.55)


def icono(cx, cy, tipo, color):
    """Iconos dibujados a mano: SVG puro, sin dependencias."""
    if tipo == "terminal":
        return (f'<rect x="{cx-12}" y="{cy-10}" width="24" height="20" rx="3" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<path d="M {cx-7} {cy-4} l 3.5 4 l -3.5 4" fill="none" '
                f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
                f'<line x1="{cx+1}" y1="{cy+4}" x2="{cx+7}" y2="{cy+4}" '
                f'stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>')
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
        return (patas + f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="3" '
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
    if tipo == "sobre":
        return (f'<rect x="{cx-13}" y="{cy-8}" width="26" height="17" rx="3" '
                f'fill="none" stroke="{color}" stroke-width="1.6"/>'
                f'<path d="M {cx-13} {cy-6} l 13 8 l 13 -8" fill="none" '
                f'stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>')
    if tipo == "objetivo":
        return (f'<circle cx="{cx}" cy="{cy}" r="11" fill="none" stroke="{color}" '
                f'stroke-width="1.6"/>'
                f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{color}"/>')
    return ""


def tarjeta(x, y, w, h, titulo, lineas, color, tipo=None, etiqueta=None,
            mono=None, destacada=False):
    """Tarjeta sobre el fondo oscuro.

    La elevacion se hace subiendo la opacidad del blanco, no con sombras: sobre negro
    una sombra negra no se ve.
    """
    fondo = "rgba(255,255,255,0.045)" if destacada else "rgba(255,255,255,0.022)"
    borde = f'stroke="{color}" stroke-opacity="0.45"' if destacada else f'stroke="{BORDE}"'
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fondo}" '
         f'{borde} stroke-width="1"/>']
    if destacada:
        # Halo tenue por dentro del borde: el acento se nota sin gritar.
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
                 f'fill="none" stroke="{color}" stroke-opacity="0.10" '
                 f'stroke-width="3"/>')

    xi = x + (60 if tipo else 18)
    if tipo:
        p.append(f'<circle cx="{x+32}" cy="{y+h/2}" r="17" '
                 f'fill="{color}" fill-opacity="0.12"/>')
        p.append(icono(x + 32, y + h / 2, tipo, color))

    # Titulo: si es un identificador tecnico va en monoespaciada.
    fam = MONO if mono else SANS
    tam_tit = 13.5 if mono else 14
    alto_txt = 18 + len(lineas) * 15
    y0 = y + (h - alto_txt) / 2 + 13
    p.append(f'<text x="{xi}" y="{y0}" font-family="{fam}" font-size="{tam_tit}" '
             f'font-weight="590" letter-spacing="-0.2" fill="{TXT}">'
             f'{esc(titulo)}</text>')
    for i, ln in enumerate(lineas):
        p.append(f'<text x="{xi}" y="{y0 + 17 + i*15}" font-family="{SANS}" '
                 f'font-size="11.5" fill="{TXT3}">{esc(ln)}</text>')

    if etiqueta:
        tw = ancho_texto(etiqueta, 9.5, True) + 18
        p.append(f'<rect x="{x + w - tw - 10}" y="{y + 9}" width="{tw}" height="18" '
                 f'rx="9" fill="{color}" fill-opacity="0.14"/>')
        p.append(f'<text x="{x + w - tw/2 - 10}" y="{y + 21.5}" text-anchor="middle" '
                 f'font-family="{MONO}" font-size="9.5" fill="{color}">'
                 f'{esc(etiqueta)}</text>')
    return "\n".join(p)


def metrica(x, y, valor, pie, color, tipo):
    """Tarjeta de metrica: el numero grande, en monoespaciada como Linear."""
    w, h = 300, 92
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
        f'fill="rgba(255,255,255,0.022)" stroke="{BORDE}" stroke-width="1"/>',
        icono(x + 34, y + h / 2, tipo, color),
        f'<text x="{x + 62}" y="{y + 44}" font-family="{MONO}" font-size="28" '
        f'font-weight="590" letter-spacing="-1" fill="{color}">{esc(valor)}</text>',
        f'<text x="{x + 62}" y="{y + 66}" font-family="{SANS}" font-size="11.5" '
        f'fill="{TXT3}">{esc(pie)}</text>',
    ])


def bezier(x1, y1, x2, y2, color, etiqueta=None, opacidad=1.0):
    """Curva S: mas elegante que un codo y deja claro de donde sale cada rama."""
    dy = (y2 - y1) * 0.5
    p = [f'<path d="M {x1} {y1} C {x1} {y1+dy} {x2} {y2-dy} {x2} {y2}" fill="none" '
         f'stroke="{color}" stroke-opacity="{opacidad}" stroke-width="1.6" '
         f'marker-end="url(#punta-{color[1:]})"/>']
    if etiqueta:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        an = ancho_texto(etiqueta, 11, True) + 22
        p.append(f'<rect x="{mx - an/2}" y="{my - 12}" width="{an}" height="24" '
                 f'rx="12" fill="{PANEL}" stroke="{BORDE}" stroke-width="1"/>')
        p.append(f'<text x="{mx}" y="{my + 4}" text-anchor="middle" '
                 f'font-family="{SANS}" font-size="11" font-weight="510" '
                 f'fill="{color}">{esc(etiqueta)}</text>')
    return "\n".join(p)


def recto(x1, y1, x2, y2, color, etiqueta=None, opacidad=1.0, dx=0):
    p = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
         f'stroke-opacity="{opacidad}" stroke-width="1.6" '
         f'marker-end="url(#punta-{color[1:]})"/>']
    if etiqueta:
        mx, my = (x1 + x2) / 2 + dx, (y1 + y2) / 2
        an = ancho_texto(etiqueta, 11, True) + 22
        p.append(f'<rect x="{mx - an/2}" y="{my - 12}" width="{an}" height="24" '
                 f'rx="12" fill="{PANEL}" stroke="{BORDE}" stroke-width="1"/>')
        p.append(f'<text x="{mx}" y="{my + 4}" text-anchor="middle" '
                 f'font-family="{SANS}" font-size="11" font-weight="510" '
                 f'fill="{color}">{esc(etiqueta)}</text>')
    return "\n".join(p)


# (titulo, x, y, w, h, lineas, color, icono, etiqueta, mono, destacada, dentro)
CAJAS = [
    ("Catálogo de campos", 380, 300, 240, 78, ["qué se puede preguntar"],
     TXT3, "lista", "catalogs/*.json", False, False, True),
    ("Spark-X2.5-4B", 760, 300, 240, 78, ["Q8_0 · ~9 GB en VRAM"],
     TXT3, "chip", None, False, False, True),
    ("Tú escribes", 80, 500, 180, 88, ["lenguaje natural"],
     TXT3, "terminal", None, False, False, False),
    ("preguntar.py", 380, 500, 240, 88, ["lee la cabecera", "y deduce el tipo"],
     ACENTO, "lista", "cliente", True, True, True),
    ("llama-server", 760, 500, 240, 88, ["un solo proceso · Vulkan"],
     ACENTO, "servidor", "RX 9070", True, True, True),
    ("/v1/decision", 380, 760, 260, 100, ["PUNTÚA las opciones", "no genera ni un token"],
     ACENTO, "rayo", "0 tokens", True, True, True),
    ("/v1/chat/completions", 940, 760, 260, 100, ["GENERA texto", "token a token"],
     TXT3, "burbuja", "respaldo", True, False, True),
    ("Valor listo para usar", 380, 900, 260, 78, ["+ probabilidad + confianza"],
     ACENTO, "sobre", None, False, False, True),
    ("Prosa", 940, 900, 260, 78, ["hay que interpretarla"],
     TXT3, "burbuja", None, False, False, True),
]


def main():
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" '
         f'width="{ANCHO}" height="{ALTO}">', "<defs>",
         # Rejilla de puntos: textura sutil, casi invisible, que quita la sensacion
         # de folio en blanco.
         f'<pattern id="rejilla" width="28" height="28" patternUnits="userSpaceOnUse">'
         f'<circle cx="1.2" cy="1.2" r="1.2" fill="#ffffff" fill-opacity="0.030"/></pattern>',
         # Halo indigo muy tenue arriba: da foco sin ser un degradado de adorno.
         f'<radialGradient id="halo" cx="0.5" cy="0" r="0.75">'
         f'<stop offset="0" stop-color="{ACENTO}" stop-opacity="0.13"/>'
         f'<stop offset="1" stop-color="{ACENTO}" stop-opacity="0"/>'
         f'</radialGradient>']
    for c in (ACENTO, TXT3):
        s.append(f'<marker id="punta-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
    s.append("</defs>")

    # ---------------------------------------------------------- fondo
    s.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="{FONDO}"/>')
    s.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="url(#rejilla)"/>')
    s.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="url(#halo)"/>')

    # ---------------------------------------------------------- cabecera
    s.append(f'<rect x="48" y="40" width="42" height="42" rx="11" '
             f'fill="url(#halo)" stroke="{ACENTO}" stroke-opacity="0.5" '
             f'stroke-width="1"/>')
    s.append(f'<path d="M 62 54 h 14 M 62 62 h 14 M 62 70 h 8" stroke="{ACENTO2}" '
             f'stroke-width="2.2" stroke-linecap="round"/>')
    s.append(f'<text x="108" y="62" font-family="{SANS}" font-size="25" '
             f'font-weight="590" letter-spacing="-0.9" fill="{TXT}">'
             f'AIOM: un modelo, dos formas de preguntar</text>')
    s.append(f'<text x="108" y="84" font-family="{SANS}" font-size="13" '
             f'letter-spacing="-0.1" fill="{TXT3}">El mismo servidor atiende las dos. '
             f'El modo no es del sistema: es una propiedad de la petición.</text>')
    s.append(f'<rect x="{ANCHO-232}" y="48" width="184" height="26" rx="13" '
             f'fill="rgba(255,255,255,0.03)" stroke="{BORDE}" stroke-width="1"/>')
    s.append(f'<circle cx="{ANCHO-212}" cy="61" r="3.5" fill="{ACENTO}"/>')
    s.append(f'<text x="{ANCHO-200}" y="65" font-family="{MONO}" font-size="11" '
             f'fill="{TXT2}">local · sin red · sin nube</text>')

    # ---------------------------------------------------------- metricas
    for k, (val, pie, col, ic) in enumerate((
            ("0 tokens", "por respuesta de decisión", ACENTO2, "rayo"),
            ("2,7×", "más rápido que el chat, 1 pregunta", ACENTO2, "objetivo"),
            ("9,8×", "más rápido con 15 encadenadas", ACENTO2, "objetivo"),
            ("85,6%", "de acierto con una pregunta", TXT2, "sobre"))):
        s.append(metrica(48 + k * 326, 130, val, pie, col, ic))

    # ---------------------------------------------------------- frontera
    s.append(f'<rect x="{ZX}" y="{ZY}" width="{ZW}" height="{ZH}" rx="14" '
             f'fill="rgba(255,255,255,0.014)" stroke="{BORDE_SUAVE}" stroke-width="1" '
             f'stroke-dasharray="7,6"/>')
    s.append(f'<text x="{ZX+22}" y="{ZY+26}" font-family="{MONO}" font-size="10.5" '
             f'letter-spacing="1.4" fill="{TXT4}">TU EQUIPO</text>')

    # ---------------------------------------------------------- tarjetas
    for (tit, x, y, w, h, lns, col, ic, etq, mono, dest, _d) in CAJAS:
        s.append(tarjeta(x, y, w, h, tit, lns, col, ic, etq, mono, dest))

    # ---------------------------------------------------------- conexiones
    # La pildora de entrada va desplazada a la izquierda: centrada, cruzaba la
    # frontera de puntos de TU EQUIPO.
    s.append(recto(260, 544, 380, 544, TXT3, "tu caso", dx=-24))
    s.append(recto(500, 378, 500, 500, TXT3, "define los campos"))
    s.append(recto(620, 544, 760, 544, ACENTO, "esquema + texto"))
    s.append(recto(880, 378, 880, 500, TXT3, "cargado una vez"))
    s.append(f'<line x1="880" y1="588" x2="880" y2="650" stroke="{ACENTO}" '
             f'stroke-width="1.6"/>')
    # Punto de union: deja claro que la bifurcacion sale de UN sitio.
    s.append(f'<circle cx="880" cy="650" r="4.5" fill="{PANEL}" stroke="{ACENTO}" '
             f'stroke-width="1.8"/>')
    s.append(bezier(880, 650, 510, 760, ACENTO, "sí · puntúa las opciones"))
    s.append(bezier(880, 650, 1070, 760, TXT3, "no · relevo al chat", 0.85))
    s.append(recto(510, 860, 510, 900, ACENTO))
    s.append(recto(1070, 860, 1070, 900, TXT3, opacidad=0.85))

    # ---------------------------------------------------------- leyenda
    ly = 1064
    s.append(f'<line x1="48" y1="1024" x2="{ANCHO-48}" y2="1024" stroke="{BORDE_SUAVE}" '
             f'stroke-width="1"/>')
    s.append(f'<text x="48" y="{ly}" font-family="{MONO}" font-size="10.5" '
             f'letter-spacing="1.4" fill="{TXT4}">LEYENDA</text>')
    x = 168
    for nombre, col, dest in (("Entrada del usuario", TXT3, False),
                              ("Vía de decisión · 0 tokens", ACENTO, True),
                              ("Vía de chat · respaldo", TXT3, False)):
        # La muestra se dibuja como una tarjeta en miniatura (mismo relleno y borde),
        # no como un cuadro de color: asi se ve a que corresponde cada uno.
        s.append(f'<rect x="{x}" y="{ly-13}" width="20" height="17" rx="5" '
                 f'fill="{"rgba(255,255,255,0.045)" if dest else "rgba(255,255,255,0.022)"}" '
                 f'stroke="{col}" stroke-opacity="{0.45 if dest else 0.3}" '
                 f'stroke-width="1"/>')
        s.append(f'<rect x="{x+4}" y="{ly-9}" width="12" height="9" rx="2" '
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

    # ------------------------------------------------------------ comprobaciones
    fallos = []
    for tit, x, y, w, h, lns, _c, ic, etq, mono, _d, dentro in CAJAS:
        necesita = (60 if ic else 18) + max(
            [ancho_texto(tit, 13.5 if mono else 14, True)]
            + [ancho_texto(l, 11.5) for l in lns])
        if necesita > w - 12:
            fallos.append(f"«{tit}»: el texto pide {necesita:.0f}px, la caja tiene {w}")
        if x < 10 or x + w > ANCHO - 10 or y < 0 or y + h > ALTO:
            fallos.append(f"«{tit}» se sale del lienzo")
        if dentro and (x < ZX or x + w > ZX + ZW or y < ZY or y + h > ZY + ZH):
            fallos.append(f"«{tit}» cruza la frontera de TU EQUIPO")
        if not dentro and x + w > ZX:
            fallos.append(f"«{tit}» deberia quedar fuera de la frontera")
    # El halo de la cabecera no debe tapar las metricas.
    if 130 < 82 + 42:
        fallos.append("las metricas pisan la cabecera")
    # La pildora de la flecha de entrada NO puede cruzar la frontera de TU EQUIPO:
    # es el fallo que tenia la version anterior.
    centro_p = (260 + 380) / 2 - 24
    ancho_p = ancho_texto("tu caso", 11, True) + 22
    if centro_p + ancho_p / 2 > ZX:
        fallos.append(f"la pildora de entrada (acaba en {centro_p + ancho_p/2:.0f}) "
                      f"cruza la frontera (empieza en {ZX})")
    # Las dos etiquetas de la bifurcacion
    l1, l2 = (880 + 510) / 2, (880 + 1070) / 2
    a1 = ancho_texto("sí · puntúa las opciones", 11, True) + 22
    a2 = ancho_texto("no · relevo al chat", 11, True) + 22
    if l1 + a1/2 > l2 - a2/2:
        fallos.append("los rotulos de la bifurcacion se solapan")

    if fallos:
        print("  FALLOS:")
        for f_ in fallos:
            print("   -", f_)
        raise SystemExit(1)
    print("  ninguna etiqueta se sale de su tarjeta ni del lienzo: verificado")
    print("  la frontera contiene las tarjetas de dentro: verificado")
    print("  los rotulos de la bifurcacion no se solapan: verificado")


if __name__ == "__main__":
    main()
