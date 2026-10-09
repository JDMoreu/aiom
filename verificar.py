"""Comprueba que lo que dicen los documentos coincide con lo que dicen los datos.

Existe por un motivo concreto: los numeros de un README escrito a mano se quedan
viejos en cuanto se vuelve a medir, y nadie se entera. Aqui se comparan las cifras que
aparecen en los documentos con results/ y se avisa si discrepan. Ademas revisa que los
enlaces internos existan y que los SVG sean validos.

    python verificar.py            # informe
    python verificar.py --estricto # sale con codigo 1 si algo falla
"""

import argparse
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
fallos = []
avisos = []


def _leer_json(nombre):
    ruta = os.path.join(AQUI, "results", nombre)
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _texto(relativo):
    ruta = os.path.join(AQUI, relativo)
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------- enlaces
def revisar_enlaces():
    patron = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    revisados = 0
    for base, _, ficheros in os.walk(AQUI):
        if ".git" in base:
            continue
        for f in ficheros:
            if not f.endswith(".md"):
                continue
            ruta = os.path.join(base, f)
            with open(ruta, encoding="utf-8") as fh:
                for n, linea in enumerate(fh, 1):
                    for destino in patron.findall(linea):
                        if destino.startswith(("http://", "https://", "mailto:", "#")):
                            continue
                        limpio = destino.split("#")[0].strip()
                        if not limpio:
                            continue
                        revisados += 1
                        objetivo = os.path.normpath(os.path.join(base, limpio))
                        if not os.path.exists(objetivo):
                            fallos.append(
                                f"enlace roto: {os.path.relpath(ruta, AQUI)}:{n} -> "
                                f"{destino}")
    return revisados


# ---------------------------------------------------------------------- graficos
def revisar_graficos():
    svgs = sorted(glob.glob(os.path.join(AQUI, "results", "graf", "*.svg")))
    for ruta in svgs:
        nombre = os.path.basename(ruta)
        with open(ruta, encoding="utf-8") as f:
            s = f.read()
        try:
            ET.fromstring(s)
        except ET.ParseError as e:
            fallos.append(f"SVG invalido: {nombre}: {e}")
            continue
        if not s.lstrip().startswith("<svg") and "<?xml" not in s.split("<svg")[0]:
            fallos.append(f"SVG no empieza por <svg>: {nombre}")
        if "var(--" in s:
            fallos.append(f"SVG depende de variables CSS del tema: {nombre} "
                          f"(no se vera igual fuera de este chat)")
    return len(svgs)


# ------------------------------------------------------------------- cifras
def revisar_cifras():
    """Compara las tablas que se copian a mano con lo que dicen los datos."""
    casc = _leer_json("cascada.json")
    if not casc:
        avisos.append("no hay results/cascada.json; no se comprueban sus cifras")
        return 0

    def media(n, modo):
        v = [x["ms"] for x in casc if x["n"] == n and x["modo"] == modo]
        return sum(v) / len(v) if v else None

    comprobadas = 0
    # README.md: tabla "decision | chat | ventaja"
    txt = _texto("README.md")
    if txt:
        bloque = re.search(r"\| preguntas encadenadas \|(.+?)\n\n", txt, re.S)
        if bloque:
            for linea in bloque.group(1).splitlines():
                campos = [c.strip() for c in linea.strip("|").split("|")]
                if len(campos) < 4 or not campos[0].isdigit():
                    continue
                n = int(campos[0])
                for col, modo in ((1, "tipado"), (2, "llm")):
                    m = re.match(r"\*{0,2}(\d+)\s*ms", campos[col])
                    if not m:
                        continue
                    dicho, real = int(m.group(1)), media(n, modo)
                    comprobadas += 1
                    if real is not None and abs(dicho - real) > 1.5:
                        fallos.append(
                            f"README.md: con {n} preguntas dice que {modo} tarda "
                            f"{dicho} ms y los datos dicen {real:.0f} ms")
    return comprobadas


# ------------------------------------------------------------- ningun dato suelto
def revisar_trazabilidad():
    """Los documentos generados deben decir de donde salen."""
    for relativo in ("docs/ESTUDIO.md", "docs/DETALLE.md", "docs/METRICAS.md"):
        txt = _texto(relativo)
        if txt is None:
            fallos.append(f"falta el documento {relativo}")
        elif "generad" not in txt.lower():
            avisos.append(f"{relativo} no dice que es generado")


def main():
    ap = argparse.ArgumentParser(prog="verificar")
    ap.add_argument("--estricto", action="store_true",
                    help="codigo de salida 1 si hay algun fallo")
    a = ap.parse_args()

    enlaces = revisar_enlaces()
    svgs = revisar_graficos()
    cifras = revisar_cifras()
    revisar_trazabilidad()

    print(f"  enlaces internos comprobados : {enlaces}")
    print(f"  graficos comprobados         : {svgs}")
    print(f"  cifras cruzadas con los datos: {cifras}")
    print()
    for av in avisos:
        print(f"  aviso: {av}")
    if fallos:
        print(f"  FALLOS: {len(fallos)}")
        for f in fallos:
            print(f"    {f}")
        return 1 if a.estricto else 0
    print("  todo coincide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
