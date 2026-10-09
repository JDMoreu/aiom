"""Saca el texto de un documento para poder preguntarle cosas.

Un caso no tiene por que escribirse a mano: puede ser una carta, un informe o un
correo que ya existe. Esto lo convierte en texto para que sea la `entrada` de la
pregunta.

Que se puede leer y con que:

    .txt .md .markdown .csv .json .log   texto plano, se lee tal cual
    .docx                                se abre el ZIP y se lee su XML
    .pdf                                 hace falta pymupdf

Los tres primeros son biblioteca estandar de Python, sin instalar nada. El `.docx`
TAMBIEN: un .docx es un ZIP con XML dentro, y eso se abre con `zipfile`.

El `.pdf` es el unico que pide una dependencia, y es opcional (como matplotlib para
los graficos): si no esta, se dice que falta en vez de fallar por dentro.

    pip install pymupdf

El `.doc` y el `.rtf` antiguos NO se leen: hay que convertirlos antes (a .docx, a
.pdf o a texto). Se dice claramente en vez de devolver basura.
"""

import os
import re
import zipfile

# extension -> (como se lee, hace falta algo?)
SOPORTADOS = {
    ".txt": ("texto", None),
    ".md": ("texto", None),
    ".markdown": ("texto", None),
    ".csv": ("texto", None),
    ".json": ("texto", None),
    ".log": ("texto", None),
    ".docx": ("docx", None),
    ".pdf": ("pdf", "pymupdf"),
}

NO_SOPORTADOS = {
    ".doc": "el .doc antiguo es binario; guardalo como .docx o .pdf y vuelve a probar",
    ".rtf": "el .rtf hay que convertirlo; guardalo como .txt, .docx o .pdf",
    ".odt": "el .odt hay que convertirlo; guardalo como .docx o .pdf",
    ".xlsx": "para hojas de calculo exporta la hoja a .csv",
}


def extension(nombre):
    """La extension en minusculas, con el punto. '' si no tiene."""
    return os.path.splitext(nombre or "")[1].lower()


def puede(nombre):
    """(se_puede, motivo). El motivo solo cuando NO se puede."""
    ext = extension(nombre)
    if ext in SOPORTADOS:
        modo, necesita = SOPORTADOS[ext]
        if necesita and not _hay(necesita):
            return False, (f"para leer {ext} hace falta {necesita}: "
                           f"pip install {necesita}")
        return True, None
    if ext in NO_SOPORTADOS:
        return False, NO_SOPORTADOS[ext]
    return False, (f"no se leer '{ext or 'sin extension'}'. Se puede: "
                   + ", ".join(sorted(SOPORTADOS))
                   + ". O pega el texto a mano.")


def _hay(modulo):
    """Si el modulo esta instalado, sin importarlo del todo."""
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------- #
# limpieza
# --------------------------------------------------------------------------- #
def limpiar(texto):
    """Deja el texto legible sin cambiarle el sentido.

    Lo justo y nada mas. Un PDF trae la linea partida donde le cabia, y a veces con
    guion al final; se vuelven a juntar esas dos. Nada de reflow agresivo: el modelo
    lee los saltos de linea sin problema, y reordenar el texto si puede cambiarlo.
    """
    lineas = [l.rstrip() for l in (texto or "").replace("\r\n", "\n").split("\n")]
    unidas = []
    for l in lineas:
        # "infor-" + "macion" -> "informacion"
        if unidas and unidas[-1].endswith("-") and l[:1].islower():
            unidas[-1] = unidas[-1][:-1] + l.lstrip()
        else:
            unidas.append(l)
    texto = "\n".join(unidas)
    texto = re.sub(r"\n{3,}", "\n\n", texto)      # 3+ saltos -> uno en blanco
    texto = re.sub(r"[ \t]{2,}", " ", texto)      # espacios de mas
    return texto.strip()


# --------------------------------------------------------------------------- #
# los lectores
# --------------------------------------------------------------------------- #
def _de_texto(datos):
    for codec in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
    return datos.decode("utf-8", "replace")


def _de_docx(datos):
    """Un .docx es un ZIP. El texto esta en word/document.xml, en <w:t>.

    Se hace con la biblioteca estandar: no hace falta python-docx.
    """
    import io
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        if "word/document.xml" not in z.namelist():
            raise ValueError("el .docx no trae word/document.xml: puede estar corrupto")
        xml = z.read("word/document.xml").decode("utf-8", "replace")

    # Cada parrafo es un <w:p>. Dentro, los trozos de texto son <w:t>.
    parrafos = []
    for bloque in re.split(r"</w:p>", xml):
        trozos = re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", bloque, re.S)
        if not trozos:
            continue
        # <w:tab/> y <w:br/> no son texto: se limpian antes de unir
        linea = "".join(trozos)
        linea = (linea.replace("&amp;", "&").replace("&lt;", "<")
                      .replace("&gt;", ">").replace("&quot;", '"')
                      .replace("&apos;", "'"))
        if linea.strip():
            parrafos.append(linea.strip())
    if not parrafos:
        raise ValueError("el .docx no tiene texto en el cuerpo "
                         "(puede que sea solo imagenes)")
    return "\n\n".join(parrafos)


def _de_pdf(datos):
    """PDF -> texto. Necesita pymupdf; si no esta, se dice y se para.

    `fitz` es el nombre viejo del modulo y sigue funcionando, pero pymupdf avisa de
    que va a desaparecer. Se prefiere el nombre nuevo y se deja el viejo como respaldo
    para versiones antiguas, que es lo que hace el propio proyecto.
    """
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf                 # nombre antiguo
        except ImportError:
            raise ValueError("para leer PDF hace falta pymupdf: pip install pymupdf")
    with pymupdf.open(stream=datos, filetype="pdf") as doc:
        paginas = []
        for pagina in doc:
            t = pagina.get_text()
            if t.strip():
                paginas.append(t)
        if not paginas:
            raise ValueError("el PDF no tiene capa de texto (sera un escaneo): "
                             "habria que pasarle un OCR antes")
    # El numero de paginas solo es un dato REAL en un PDF. En un .txt o un .docx no
    # hay paginas hasta que alguien lo maqueta, asi que ahi no se inventa.
    return "\n\n".join(paginas), {"paginas": len(paginas)}


# Cada lector devuelve (texto, extras). Los extras son los datos que SOLO ese formato
# puede saber de verdad -- hoy, las paginas de un PDF.
LECTORES = {"texto": lambda d: (_de_texto(d), {}),
            "docx": lambda d: (_de_docx(d), {}),
            "pdf": _de_pdf}


# --------------------------------------------------------------------------- #
# la puerta
# --------------------------------------------------------------------------- #
def extraer_bytes(datos, nombre):
    """Bytes + nombre del fichero -> texto limpio.

    Devuelve un dict con el texto y lo que hay que saber de el, en vez de solo el
    texto: quien lo llame necesita poder decir cuanto ocupa y de donde salio.
    """
    ok, motivo = puede(nombre)
    if not ok:
        raise ValueError(motivo)
    modo = SOPORTADOS[extension(nombre)][0]
    crudo, extras = LECTORES[modo](datos)
    texto = limpiar(crudo)
    if not texto:
        raise ValueError(f"'{nombre}' se leyo bien pero no tiene texto")
    datos = {"texto": texto, "nombre": os.path.basename(nombre or ""),
             "tipo": modo, "caracteres": len(texto),
             "palabras": len(texto.split()), "lineas": texto.count("\n") + 1}
    datos.update(extras)
    return datos


def extraer(ruta):
    """Lo mismo, desde una ruta del disco."""
    if not os.path.isfile(ruta):
        raise ValueError(f"no encuentro el fichero: {ruta}")
    with open(ruta, "rb") as f:
        return extraer_bytes(f.read(), os.path.basename(ruta))


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="documento",
                                 description="Saca el texto de un documento")
    ap.add_argument("ruta")
    ap.add_argument("--json", action="store_true", help="con los metadatos")
    ap.add_argument("--guardar", help="escribe el texto limpio en este fichero")
    a = ap.parse_args()

    try:
        r = extraer(a.ruta)
    except ValueError as e:
        print(f"no puedo: {e}")
        return 1

    if a.guardar:
        with open(a.guardar, "w", encoding="utf-8", newline="") as f:
            f.write(r["texto"])
        print(f"{r['nombre']}: {r['caracteres']} caracteres -> {a.guardar}")
    elif a.json:
        print(json.dumps({k: v for k, v in r.items() if k != "texto"},
                         ensure_ascii=False, indent=2))
    else:
        print(r["texto"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
