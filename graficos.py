"""Graficos del estudio con matplotlib, en SVG.

Antes se construian a mano con cadenas de SVG: funcionaba, pero salian planos y sin
las convenciones de un grafico de verdad (ejes rotulados, rejilla, unidades). Aqui se
hace con matplotlib y un estilo unico para que todos los graficos del repositorio se
lean igual.

El SVG se guarda con el texto como texto (no como trazados), para que se pueda buscar
y para que pese poco. El fondo es opaco y los colores son fijos: asi se ve igual en
GitHub en tema claro y en oscuro, y no depende del tema de donde se abra.

Para regenerarlos hace falta matplotlib, que no es dependencia del cliente del
proyecto (ese solo usa la biblioteca estandar). Estan en results/graf/ ya generados.

    python graficos.py
"""

import os
import sys

# matplotlib NO es dependencia del cliente del proyecto (ese usa solo la biblioteca
# estandar): solo hace falta para REGENERAR los graficos. Si no esta instalado, se
# avisa con claridad en vez de soltar un volcado, y los graficos ya generados se
# reutilizan tal cual.
try:
    import matplotlib
    matplotlib.use("Agg")            # sin ventana: solo se escriben ficheros
    import matplotlib.pyplot as plt  # noqa: E402
    from matplotlib.ticker import MaxNLocator  # noqa: E402
    HAY_MATPLOTLIB = True
except ImportError:
    HAY_MATPLOTLIB = False

AQUI = os.path.dirname(os.path.abspath(__file__))
GRAF = os.path.join(AQUI, "results", "graf")

_AVISADO = [False]


def _sin_matplotlib(nombre):
    """Se reutiliza el SVG ya generado, o se explica por que no se puede."""
    ruta = os.path.join(GRAF, nombre)
    if os.path.exists(ruta):
        if not _AVISADO[0]:
            print("  aviso: sin matplotlib, se reutilizan los graficos ya generados.")
            print("         para regenerarlos:  pip install matplotlib")
            _AVISADO[0] = True
        return f"../results/graf/{nombre}"
    print(f"  FALTA matplotlib y no existe {nombre}: no se puede generar el grafico.")
    print(f"         instala matplotlib (pip install matplotlib) y vuelve a intentarlo.")
    return f"../results/graf/{nombre}"

# Paleta. Azules para el modo de decision, naranja para el chat: el color sigue
# significando lo mismo en todos los graficos.
AZUL = "#1f5c99"
AZUL_CLARO = "#6ba3d6"
NARANJA = "#c9762b"
GRIS = "#6b7280"
GRIS_CLARO = "#d1d5db"
TINTA = "#111827"

COLOR = {"tipado": AZUL, "tipada": AZUL, "natural": AZUL_CLARO,
         "llm": NARANJA, "chat": NARANJA, "decision": AZUL, "decisión": AZUL,
         # Nombres completos de las series, tal como salen en la leyenda: sin esto
         # caian al color de reserva y la leyenda no distinguia nada.
         "decisión natural": AZUL_CLARO, "decision natural": AZUL_CLARO,
         "decisión tipada": AZUL, "decision tipada": AZUL,
         "dec. natural": AZUL_CLARO, "dec. tipada": AZUL}
# La lista de colores que se usa cuando el nombre de la serie no esta en COLOR, para
# que una serie desconocida no se quede gris y se confunda con las demas.
RESERVA = [AZUL, NARANJA, AZUL_CLARO, "#7c3aed", "#0f766e", GRIS]


def color_de(nombre, indice=0):
    """Color de una serie.

    Se busca el nombre tal cual y en minusculas: pasar "Natural" cuando la tabla tiene
    "natural" hacia que TODAS las series cayeran al color por defecto y el grafico
    saliera de un solo color, con una leyenda que no distinguia nada.
    """
    if nombre in COLOR:
        return COLOR[nombre]
    if str(nombre).lower() in COLOR:
        return COLOR[str(nombre).lower()]
    return RESERVA[indice % len(RESERVA)]


def _estilo():
    """Estilo comun: sin caja, rejilla suave y tipografia del sistema."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Calibri", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": GRIS_CLARO,
        "axes.labelcolor": TINTA,
        "axes.titlecolor": TINTA,
        "text.color": TINTA,
        "xtick.color": GRIS,
        "ytick.color": GRIS,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "svg.fonttype": "none",      # el texto sigue siendo texto en el SVG
    })


def _sin_borde(ax, rejilla="y"):
    """Quita los bordes que no aportan y deja una rejilla suave."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRIS_CLARO)
    ax.grid(axis=rejilla, color=GRIS_CLARO, linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)


def _titulo(fig, titulo, subtitulo=None):
    fig.text(0.01, 0.98, titulo, ha="left", va="top", fontsize=12.5,
             fontweight="bold", color=TINTA)
    if subtitulo:
        fig.text(0.01, 0.90, subtitulo, ha="left", va="top", fontsize=9.5,
                 color=GRIS)


def _guardar(fig, nombre):
    os.makedirs(GRAF, exist_ok=True)
    fig.savefig(os.path.join(GRAF, nombre), format="svg",
                bbox_inches="tight", pad_inches=0.25, facecolor="white")
    plt.close(fig)
    # La ruta que se pone en el markdown se resuelve desde docs/, no desde la raiz.
    return f"../results/graf/{nombre}"


def barras_h(nombre, titulo, etiquetas, valores, colores, unidad="", subtitulo=None,
             ancho=6.6, eje=None):
    """Barras horizontales: se leen mejor que las verticales con nombres largos.

    `unidad` es el sufijo del numero (\" ms\") y `eje` la etiqueta del eje. Antes eran la
    misma cosa y el eje acababa rotulado solo \"ms\", que no dice que se mide.
    """
    if not HAY_MATPLOTLIB:
        return _sin_matplotlib(nombre)
    _estilo()
    fig, ax = plt.subplots(figsize=(ancho, 0.62 * len(valores) + 1.5))
    y = range(len(valores))
    ax.barh(list(y), valores, color=colores, height=0.62, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(etiquetas)
    ax.invert_yaxis()
    _sin_borde(ax, rejilla="x")

    tope = max(valores) if valores else 1
    ax.set_xlim(0, tope * 1.22)
    for i, v in enumerate(valores):
        ax.text(v + tope * 0.02, i, f"{v:,.1f}{unidad}".replace(",", " "),
                va="center", fontsize=10, fontweight="bold", color=TINTA)
    ax.set_xlabel(eje or unidad.strip() or "valor", fontsize=9.5, color=GRIS)
    _titulo(fig, titulo, subtitulo)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    return _guardar(fig, nombre)


def barras_agrupadas(nombre, titulo, grupos, series, unidad="", subtitulo=None,
                     ancho=7.0, eje=None):
    """Series comparadas dentro de cada grupo."""
    if not HAY_MATPLOTLIB:
        return _sin_matplotlib(nombre)
    _estilo()
    fig, ax = plt.subplots(figsize=(ancho, 4.0))
    n = len(series)
    ancho_b = 0.78 / n
    xs = range(len(grupos))

    for k, (nombre_s, valores) in enumerate(series.items()):
        pos = [x - 0.39 + ancho_b * (k + 0.5) for x in xs]
        ax.bar(pos, valores, width=ancho_b * 0.92, label=nombre_s,
               color=color_de(nombre_s, k), zorder=3)
        for x, v in zip(pos, valores):
            ax.text(x, v + 1.2, f"{v:.0f}", ha="center", fontsize=9,
                    fontweight="bold", color=color_de(nombre_s, k))

    ax.set_xticks(list(xs))
    ax.set_xticklabels(grupos)
    ax.set_ylim(0, 108)
    ax.set_ylabel(eje or unidad or "valor", fontsize=9.5, color=GRIS)
    _sin_borde(ax)
    # La leyenda va DEBAJO del area del grafico, no encima: sobre las barras tapaba
    # justo los valores mas altos, que son los que interesa leer.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=n,
              fontsize=9.5, frameon=False, handlelength=1.4, columnspacing=2.2)
    _titulo(fig, titulo, subtitulo)
    fig.tight_layout(rect=(0, 0.04, 1, 0.86))
    return _guardar(fig, nombre)


def lineas(nombre, titulo, x_etiquetas, series, unidad="", subtitulo=None,
           ancho=7.2, eje=None):
    """Evolucion con el eje X ordenado NUMERICAMENTE.

    Las etiquetas del eje son texto, asi que ordenarlas tal cual daria 1, 10, 15, 5 y
    el grafico aparentaria una subida y bajada que no existe.
    """
    if not HAY_MATPLOTLIB:
        return _sin_matplotlib(nombre)
    _estilo()
    fig, ax = plt.subplots(figsize=(ancho, 4.0))

    def clave(v):
        try:
            return (0, float(v))
        except (TypeError, ValueError):
            return (1, 0)

    xs = sorted(set(x_etiquetas), key=clave)
    numerico = [float(x) for x in xs]
    todos = []

    for k, (nombre_s, valores) in enumerate(series.items()):
        ys = [valores[x] for x in xs]
        todos += ys
        ax.plot(numerico, ys, marker="o", markersize=6, linewidth=2.2,
                label=nombre_s, color=color_de(nombre_s, k), zorder=3)
        for x, y in zip(numerico, ys):
            ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=9,
                        fontweight="bold", color=color_de(nombre_s, k))

    ax.set_xticks(numerico)
    ax.set_xticklabels([f"{int(x)}" for x in numerico])
    ax.set_ylim(0, max(todos) * 1.22)
    ax.set_xlabel("preguntas encadenadas por caso", fontsize=9.5, color=GRIS)
    ax.set_ylabel(eje or unidad or "valor", fontsize=9.5, color=GRIS)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    _sin_borde(ax)
    # Leyenda debajo del area: encima quedaba sobre la linea del chat segun donde caiga.
    # El anclaje va mas abajo que en los otros graficos porque este lleva ademas la
    # etiqueta del eje X, y a -0.09 la leyenda se le pegaba encima.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17),
              ncol=len(series), fontsize=9.5, frameon=False, handlelength=1.6,
              columnspacing=2.2)
    _titulo(fig, titulo, subtitulo)
    fig.tight_layout(rect=(0, 0.08, 1, 0.86))
    return _guardar(fig, nombre)


def barras_agrupadas_h(nombre, titulo, etiquetas, series, unidad="", subtitulo=None,
                       ancho=7.2, eje=None):
    """Como las agrupadas pero en horizontal, para etiquetas largas."""
    if not HAY_MATPLOTLIB:
        return _sin_matplotlib(nombre)
    _estilo()
    fig, ax = plt.subplots(figsize=(ancho, 0.62 * len(etiquetas) + 1.6))
    n = len(series)
    alto = 0.78 / n
    ys = range(len(etiquetas))

    for k, (nombre_s, valores) in enumerate(series.items()):
        pos = [y - 0.39 + alto * (k + 0.5) for y in ys]
        ax.barh(pos, valores, height=alto * 0.92, label=nombre_s,
                color=color_de(nombre_s, k), zorder=3)
        for y, v in zip(pos, valores):
            ax.text(v + 1.5, y, f"{v:.1f}".replace(".", ","), va="center",
                    fontsize=9, fontweight="bold", color=color_de(nombre_s, k))

    ax.set_yticks(list(ys))
    ax.set_yticklabels(etiquetas)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xlabel(eje or unidad or "valor", fontsize=9.5, color=GRIS)
    _sin_borde(ax, rejilla="x")
    # Leyenda debajo, igual que en el resto: encima tapaba las barras mas largas.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=n,
              fontsize=9.5, frameon=False, handlelength=1.4, columnspacing=2.2)
    _titulo(fig, titulo, subtitulo)
    fig.tight_layout(rect=(0, 0.08, 1, 0.88))
    return _guardar(fig, nombre)
