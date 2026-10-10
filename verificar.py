"""Comprueba que el repositorio cuadra consigo mismo.

Seis cosas, y son las que se rompen solas al mover ficheros o al cambiar el codigo y
olvidarse de la documentacion:

  1. Que los modulos importen. Un import roto no se ve hasta que alguien ejecuta.
  2. Que los enlaces internos de los documentos apunten a ficheros que existen.
  3. Que no haya modulos huerfanos: ninguno que no lo use nadie.
  4. Que el arbol de ficheros del README sea el de verdad, en los dos sentidos.
  5. Que las rutas que la API expone sean las que nombra la documentacion.
  6. Que los campos que devuelve /documento sean los que documenta la API.

Las tres ultimas son las que evitan que la documentacion se quede atras sin que nadie se
entere: son afirmaciones concretas y comprobables, asi que se comprueban.

    python verificar.py
"""

import importlib
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
MODULOS = ("aiom", "api", "documento", "preguntar", "tipado", "diagrama")
DOCS = ("README.md", "CREDITOS.md", "DESIGN.md", "PRODUCT.md",
        "docs/API.md", "docs/ARRANCAR.md", "docs/CLIENTE.md", "docs/MANUAL.md")

# Los enlaces a ficheros: [texto](ruta), sin URLs ni anclas.
ENLACE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)\)")
# Las rutas de la API tal como se declaran: @app.post("/ask") y compania.
RUTA_DECLARADA = re.compile(r"@app\.(?:get|post|put|delete)\(\s*\"([^\"]+)\"")
# Las rutas tal como se nombran en un documento: `GET /health`, POST /ask...
RUTA_NOMBRADA = re.compile(r"\b(?:GET|POST|PUT|DELETE)\s+(/[a-z0-9._/-]*)")
# Un nombre de fichero dentro del arbol del README.
FICHERO = re.compile(r"([A-Za-z0-9_.-]+\.(?:py|md|txt|json|html|svg|png|toml|cfg|ini))\b")


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


def ficheros_del_repo():
    """Lo que git conoce: es lo que se publica, ni mas ni menos."""
    salida = subprocess.run(["git", "ls-files"], cwd=AQUI, capture_output=True,
                            text=True, check=True).stdout
    return sorted(l.strip() for l in salida.splitlines() if l.strip())


def revisar_arbol():
    """El arbol del README, en los dos sentidos.

    Un fichero del repositorio que no aparezca en el arbol esta escondido: quien lee el
    README no sabe que existe. Y uno que el arbol nombre y no exista es una mentira. Se
    compara por NOMBRE y no por ruta, porque el arbol escribe `iot.json` indentado bajo
    `catalogs/` y eso se lee mejor que la ruta entera.
    """
    with open(os.path.join(AQUI, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    bloques = re.findall(r"```[a-z]*\n(.*?)```", readme, re.S)
    # El bloque del arbol es en el que `preguntar.py` EMPIEZA una linea: en el de los
    # comandos tambien aparece, pero dentro de un comando.
    arbol = next((b for b in bloques if re.search(r"^preguntar\.py", b, re.M)), "")
    if not arbol:
        return ["README.md: no encuentro el bloque del arbol de ficheros"], 0

    # El arbol escribe `nombre` y luego espacios y la descripcion. Se toma ese primer
    # token -fichero o carpeta- y nada mas: las palabras de las descripciones no cuentan.
    nombrados = set(FICHERO.findall(arbol))
    nombrados |= set(re.findall(r"(?m)^[ \t]*([A-Za-z0-9_.-]+/)[ \t]{2,}", arbol))
    nombrados |= set(re.findall(r"(?m)^[ \t]*([A-Za-z0-9_.-]+)[ \t]{2,}", arbol))
    # Las carpetas cuentan sin la barra: `catalogs/` nombra a catalogs.
    nombrados |= {n.rstrip("/") for n in list(nombrados) if n.endswith("/")}

    reales = ficheros_del_repo()
    por_nombre = {os.path.basename(f): f for f in reales}

    fallos = []
    for f in reales:
        if f == "README.md":
            continue                  # el arbol no hace falta que se nombre a si mismo
        carpeta = os.path.dirname(f)
        if (os.path.basename(f) not in nombrados and f not in nombrados
                and carpeta not in nombrados):
            fallos.append(f"README.md: el arbol no nombra {f}")
    # Y al reves, pero solo con los nombres que llevan extension: un token sin punto es
    # una palabra, y las palabras de las descripciones no son ficheros.
    for n in sorted(nombrados):
        if "." not in n:
            continue
        if n not in por_nombre and n not in reales:
            fallos.append(f"README.md: el arbol nombra {n}, que no existe")
    return fallos, len(nombrados)


def revisar_rutas():
    """Las rutas que la API expone tienen que estar en la documentacion.

    Las que FastAPI pone solas (/docs, /redoc, /openapi.json, /docs/oauth2-redirect) no
    se cuentan: no las declara este proyecto.
    """
    with open(os.path.join(AQUI, "api.py"), encoding="utf-8") as f:
        codigo = f.read()
    propias = set(RUTA_DECLARADA.findall(codigo))

    nombradas = set()
    for doc in DOCS:
        ruta = os.path.join(AQUI, doc)
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                nombradas |= set(RUTA_NOMBRADA.findall(f.read()))

    fallos = []
    for r in sorted(propias):
        if r not in nombradas:
            fallos.append(f"la API expone {r} y ningun documento lo nombra")
    return fallos, len(propias)


def revisar_campos():
    """Los campos de /documento que documenta la API tienen que ser los que devuelve.

    Se comprueba con un .txt, que es lo unico que se puede extraer sin las dependencias
    opcionales: sin pymupdf un PDF no se lee, y la comprobacion fallaria por algo que no
    tiene que ver con la documentacion.
    """
    import documento
    r = documento.extraer(os.path.join(AQUI, "ejemplos", "1_opciones.txt"))
    reales = set(r)

    with open(os.path.join(AQUI, "docs", "API.md"), encoding="utf-8") as f:
        api_md = f.read()
    nombrados = set(re.findall(r'"(texto|nombre|tipo|caracteres|palabras|lineas|'
                              r'paginas|paginas_con_texto|paginas_con_ocr|'
                              r'paginas_ilegibles|paginas_sin_texto|aviso)"', api_md))

    fallos = []
    for c in sorted(reales):
        if c not in nombrados:
            fallos.append(f"POST /documento devuelve '{c}' y API.md no lo documenta")
    return fallos, len(reales)


def main() -> int:
    fallos = revisar_imports()
    fallos_enl, n = revisar_enlaces()
    fallos += fallos_enl
    huerfanos = revisar_huerfanos()
    fallos_arbol, n_arbol = revisar_arbol()
    fallos += fallos_arbol
    fallos_rutas, n_rutas = revisar_rutas()
    fallos += fallos_rutas
    fallos_campos, n_campos = revisar_campos()
    fallos += fallos_campos

    print(f"  modulos comprobados          : {len(MODULOS)}")
    print(f"  enlaces internos comprobados : {n}")
    print(f"  ficheros en el arbol         : {n_arbol}")
    print(f"  rutas de la API comprobadas  : {n_rutas}")
    print(f"  campos de /documento         : {n_campos}")
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
