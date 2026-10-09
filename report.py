#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report.py — convierte results/bench.json en la documentacion del repo.

Genera:
  docs/RESULTADOS.md   tablas de metricas + lectura de los datos
  results/bench.html   graficas en SVG (sin dependencias, un solo archivo)

Sin librerias externas: el SVG se construye a mano para que el repo no arrastre
dependencias solo por graficar.
"""
from __future__ import annotations

import json
import os

MODO_COLOR = {"decision": "#2563eb", "chat": "#dc2626"}
# Etiquetas explicitas: la leyenda debe responder "cual es cual" sin ambiguedad.
MODO_NOMBRE = {"decision": "modo decision (pregunta, 0 tokens)",
               "chat": "modo chat (escribe texto)"}


def serie(res, modo, campo):
    """[(concurrencia, valor)] de un modo, ordenado por concurrencia."""
    out = []
    for b in res["bloques"]:
        if b["modo"] != modo:
            continue
        if campo.startswith("latencia_ms."):
            v = b["latencia_ms"][campo.split(".")[1]]
        else:
            v = b.get(campo)
        out.append((b["concurrencia"], v))
    return sorted(out)


def svg_lineas(titulo, series, ylabel, unidad="", ancho=680, alto=300):
    """Grafica de lineas SVG con varios modos. series: {modo: [(x, y)]}

    La leyenda va ARRIBA en horizontal, no a la derecha: puesta a la derecha con
    coordenada fija se recortaba al escalar el SVG y solo se leia "modo".
    """
    ml, mr, mt, mb = 78, 24, 78, 54
    pw, ph = ancho - ml - mr, alto - mt - mb
    xs = sorted({x for s in series.values() for x, _ in s})
    ys = [y for s in series.values() for _, y in s]
    if not xs or not ys:
        return ""
    ymin, ymax = 0, max(ys) * 1.15
    px = lambda x: ml + (xs.index(x) / max(1, len(xs) - 1)) * pw
    py = lambda y: mt + ph - (y - ymin) / (ymax - ymin) * ph

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
         f'width="100%" preserveAspectRatio="xMidYMid meet" '
         f'font-family="inherit" font-size="11">']
    p.append(f'<text x="{ml}" y="20" font-size="13" font-weight="600" '
             f'fill="var(--foreground,#111)">{titulo}</text>')
    # rejilla + eje Y
    for i in range(5):
        y = mt + ph * i / 4
        v = ymax - (ymax - ymin) * i / 4
        p.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" '
                 f'stroke="var(--border,#e5e7eb)" stroke-width="1"/>')
        p.append(f'<text x="{ml-8}" y="{y+4:.1f}" text-anchor="end" '
                 f'fill="var(--muted-foreground,#6b7280)">{v:.0f}{unidad}</text>')
    # eje X
    for x in xs:
        p.append(f'<text x="{px(x):.1f}" y="{mt+ph+18}" text-anchor="middle" '
                 f'fill="var(--muted-foreground,#6b7280)">{x}</text>')
    p.append(f'<text x="{ml+pw/2:.0f}" y="{mt+ph+38}" text-anchor="middle" '
             f'fill="var(--muted-foreground,#6b7280)">consultas en paralelo</text>')
    # series
    for modo, pts in series.items():
        col = MODO_COLOR.get(modo, "#888")
        d = " ".join(f"{'M' if i==0 else 'L'}{px(x):.1f},{py(y):.1f}"
                     for i, (x, y) in enumerate(pts))
        p.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        for x, y in pts:
            p.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3.5" fill="{col}"/>')
    # leyenda horizontal bajo el titulo: al ir dentro del ancho, nunca se recorta
    ly, lx = 48, ml
    for modo in series:
        col = MODO_COLOR.get(modo, "#888")
        etq = MODO_NOMBRE.get(modo, modo)
        p.append(f'<rect x="{lx}" y="{ly-9}" width="11" height="11" rx="2.5" fill="{col}"/>')
        p.append(f'<text x="{lx+17}" y="{ly}" fill="var(--foreground,#111)">{etq}</text>')
        lx += 26 + len(etq) * 6.4
    p.append("</svg>")
    return "\n".join(p)


def html_charts(res):
    titulos = [
        ("Caudal (consultas por segundo)", "caudal_qs", " q/s", ""),
        ("Latencia p50", "latencia_ms.p50", " ms", ""),
        ("Latencia p95 (la cola)", "latencia_ms.p95", " ms", ""),
        ("Tokens generados por consulta", "tokens_por_consulta", " tok", ""),
    ]
    partes = []
    for titulo, campo, unidad, _ in titulos:
        series = {m: serie(res, m, campo) for m in ("decision", "chat")}
        series = {k: v for k, v in series.items() if v}
        partes.append(svg_lineas(titulo, series, campo, unidad))
    d = res["dataset"]
    cfg = res["config"]
    cab = (f'<div style="font-size:13px;color:var(--muted-foreground,#6b7280);margin-bottom:6px">'
           f'{d["total"]} consultas etiquetadas &middot; {d["respondibles"]} respondibles + '
           f'{d["no_respondibles"]} para chat &middot; servidor {cfg.get("server","")}'
           f'{(" &middot; " + str(cfg.get("model"))) if cfg.get("model") else ""}</div>')
    return ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));'
            'gap:10px">' + cab + "".join(f"<div>{x}</div>" for x in partes) + "</div>")


def tabla_md(res, campo, nombre, unidad="", fmt="{:.1f}"):
    """Tabla markdown: filas = concurrencia, columnas = modo."""
    niveles = sorted({b["concurrencia"] for b in res["bloques"]})
    modos = ["decision", "chat"]
    enc = "| consultas en paralelo | " + " | ".join(MODO_NOMBRE[m] for m in modos) + " |"
    sep = "|---|" + "---|" * len(modos)
    filas = []
    for n in niveles:
        celdas = []
        for m in modos:
            v = None
            for b in res["bloques"]:
                if b["modo"] == m and b["concurrencia"] == n:
                    v = (b["latencia_ms"][campo.split(".")[1]] if campo.startswith("latencia_ms.")
                         else b.get(campo))
            celdas.append(fmt.format(v) + unidad if isinstance(v, (int, float)) else "n/d")
        filas.append(f"| {n} | " + " | ".join(celdas) + " |")
    return "\n".join([f"**{nombre}**", "", enc, sep] + filas)


def resumen_md(res):
    d, cfg = res["dataset"], res["config"]
    def buscar(modo, conc, campo):
        for b in res["bloques"]:
            if b["modo"] == modo and b["concurrencia"] == conc:
                return (b["latencia_ms"][campo] if campo in b["latencia_ms"] else b.get(campo))
        return None

    L = []
    L.append("# Resultados del benchmark\n")
    L.append("Generado por `report.py` a partir de `results/bench.json`. "
             "Todo numero de este documento sale de una ejecucion real; "
             "reproducelo con `python bench.py`.\n")
    L.append("## Configuracion\n")
    L.append(f"- Servidor: `{cfg.get('server')}`")
    L.append(f"- Modelo: `{cfg.get('model') or 'preset del servidor'}`")
    L.append(f"- Estado: `{cfg.get('health', 'n/d')}`")
    L.append(f"- Dataset: {d['total']} consultas etiquetadas "
             f"({d['respondibles']} respondibles, {d['no_respondibles']} no respondibles)\n")
    L.append("## Caudal\n")
    L.append(tabla_md(res, "caudal_qs", "Consultas por segundo", " q/s", "{:.2f}"))
    L.append("\n## Latencia p50\n")
    L.append(tabla_md(res, "latencia_ms.p50", "Mediana de latencia", " ms"))
    L.append("\n## Latencia p95\n")
    L.append(tabla_md(res, "latencia_ms.p95", "Cola p95", " ms"))
    L.append("\n## Tokens\n")
    L.append(tabla_md(res, "tokens_por_consulta", "Tokens generados por consulta", " tok"))
    L.append("\n## Acierto\n")
    L.append("| consultas en paralelo | " +
             " | ".join(MODO_NOMBRE[m] for m in ("decision", "chat")) + " |")
    L.append("|---|---|---|")
    for n in sorted({b["concurrencia"] for b in res["bloques"]}):
        cel = []
        for m in ("decision", "chat"):
            v = None
            for b in res["bloques"]:
                if b["modo"] == m and b["concurrencia"] == n:
                    v = b["acierto_campos"]
            cel.append(str(v))
        L.append(f"| {n} | " + " | ".join(cel) + " |")
    return "\n".join(L) + "\n"


def main():
    raiz = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(raiz, "results", "bench.json"), encoding="utf-8") as f:
        res = json.load(f)
    os.makedirs(os.path.join(raiz, "docs"), exist_ok=True)
    with open(os.path.join(raiz, "docs", "RESULTADOS.md"), "w", encoding="utf-8") as f:
        f.write(resumen_md(res))
    with open(os.path.join(raiz, "results", "bench.html"), "w", encoding="utf-8") as f:
        f.write(html_charts(res))
    print("escrito docs/RESULTADOS.md y results/bench.html")


if __name__ == "__main__":
    main()
