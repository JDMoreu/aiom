"""Comprueba que el repositorio cuadra consigo mismo.

Tres cosas, que son las que se rompen solas al mover ficheros:

  1. Que los modulos importen. Un import roto no se ve hasta que alguien ejecuta.
  2. Que los enlaces internos de los documentos apunten a ficheros que existen.
  3. Que no haya modulos huerfanos: ninguno que no lo use nadie.

    python verificar.py
"""

import importlib
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
MODULOS = ("aiom", "api", "documento", "preguntar", "tipado", "diagrama")
DOCS = ("README.md", "CREDITOS.md", "DESIGN.md", "PRODUCT.md",
        "docs/API.md", "docs/ARRANCAR.md", "docs/CLIENTE.md", "docs/MANUAL.md")

# Los enlaces a ficheros: [texto](ruta), sin URLs ni anclas.
ENLACE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)\)")


def revisar_imports():
    fallos = []
    for m in MODULOS:
        try:
            importlib.import_module(m)
        except Exception as e:                                    # noqa: BLE001
            fallos.append(f"{m}: {type(e).__name__}: {e}")
    return fallos


def revisar_enlaces():
    fallos, vistos = [], 0
    for doc in DOCS:
        ruta = os.path.join(AQUI, doc)
        if not os.path.exists(ruta):
            fallos.append(f"falta el documento {doc}")
            continue
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
        for destino in ENLACE.findall(texto):
            if destino.startswith(("http://", "https://", "mailto:")):
                continue
            vistos += 1
            objetivo = os.path.normpath(os.path.join(os.path.dirname(ruta), destino))
            if not os.path.exists(objetivo):
                fallos.append(f"{doc} -> {destino} (no existe)")
    return fallos, vistos


def revisar_huerfanos():
    """Un modulo que no menciona nadie es un modulo que sobra."""
    fuentes = {}
    for f in os.listdir(AQUI):
        if f.endswith(".py"):
            with open(os.path.join(AQUI, f), encoding="utf-8") as fh:
                fuentes[f] = fh.read()
    textos_docs = ""
    for d in DOCS:
        ruta = os.path.join(AQUI, d)
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as fh:
                textos_docs += fh.read()

    huerfanos = []
    for f in fuentes:
        if f == "verificar.py":
            continue
        nombre = f[:-3]
        usado = any(nombre in t for otro, t in fuentes.items() if otro != f)
        if not usado and nombre not in textos_docs:
            huerfanos.append(f)
    return huerfanos


def main() -> int:
    fallos = revisar_imports()
    fallos_enl, n = revisar_enlaces()
    fallos += fallos_enl
    huerfanos = revisar_huerfanos()

    print(f"  modulos comprobados          : {len(MODULOS)}")
    print(f"  enlaces internos comprobados : {n}")
    print(f"  modulos huerfanos            : {len(huerfanos)}"
          + (f"  ({', '.join(huerfanos)})" if huerfanos else ""))
    print()

    if fallos or huerfanos:
        for f in fallos:
            print("   -", f)
        for f in huerfanos:
            print("   -", f, "(no lo usa nadie)")
        return 1
    print("    todo coincide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
