"""Depura el repositorio: encuentra lo que ya no se usa y lo elimina con validacion.

No borra a ciegas. Para cada candidato comprueba que **ningun fichero de codigo o
documentacion lo mencione**, y solo entonces lo quita. Si algo se menciona, lo deja y
lo dice.

    python depurar.py                 # solo informa, no toca nada
    python depurar.py --aplicar       # elimina lo validado
"""

import argparse
import os
import re
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# (ruta, motivo). Todas se comprobaron a mano; el script vuelve a comprobarlo.
CANDIDATOS = [
    ("__pycache__", "cache de bytecode; se regenera solo"),
    ("x.log", "0 bytes; resto de una prueba de arranque"),
    ("fallidas.txt", "nota de trabajo con las suites que fallaron; ya resuelto"),
    ("test_out.txt", "salida guardada de test_official.py; se regenera ejecutandolo"),
    ("oficial.txt", "salida guardada del scoring oficial; se regenera"),
    ("s1mb_falt.log", "log de una corrida ya procesada"),
    ("s1mb_full.log", "log de una corrida ya procesada"),
    ("s1mb_run.log", "log de una corrida ya procesada"),
    ("wanli_full.log", "log de una corrida ya procesada"),
    ("modos.log", "log; su contenido pasa a docs/ESTUDIO.md"),
    ("multi.log", "log; su contenido pasa a docs/ESTUDIO.md"),
    ("ejemplos_jev.py", "superado por ejemplos_typesafe.py, que acepta el mismo formato"),
]

# ficheros donde se busca una mencion. Si aparece aqui, NO se borra.
FUENTES = (".py", ".md", ".json", ".txt", ".sh", ".cfg", ".toml", ".yaml", ".yml")


def mencionado(ruta, raiz=AQUI):
    """¿Algun fichero de codigo o doc menciona esta ruta (por nombre o por ruta)?

    Se excluye el propio candidato y los directorios que no son fuente.
    """
    nombre = os.path.basename(ruta)
    rel = ruta.replace("\\", "/")
    patron = re.compile(re.escape(nombre) + r"|" + re.escape(rel))
    excluir = ("__pycache__", ".git", "results")
    # El propio script lista los candidatos, asi que se menciona a si mismo: hay que
    # saltarselo o ninguna comprobacion pasa nunca.
    yo = os.path.basename(__file__)

    for base, dirs, ficheros in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in excluir]
        for f in ficheros:
            if not f.endswith(FUENTES) or f == yo:
                continue
            p = os.path.join(base, f)
            rp = os.path.relpath(p, raiz).replace("\\", "/")
            if rp == rel or rp == nombre:
                continue
            try:
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    if patron.search(fh.read()):
                        return rp
            except OSError:
                continue
    return None


def tamano(ruta):
    p = os.path.join(AQUI, ruta)
    if os.path.isdir(p):
        return sum(os.path.getsize(os.path.join(b, f))
                   for b, _, fs in os.walk(p) for f in fs)
    return os.path.getsize(p) if os.path.exists(p) else 0


def main():
    ap = argparse.ArgumentParser(prog="depurar")
    ap.add_argument("--aplicar", action="store_true", help="elimina lo validado")
    a = ap.parse_args()

    print()
    print("  DEPURACION" + ("  (aplicando)" if a.aplicar else "  (solo informa)"))
    print("  " + "=" * 70)

    borrados, salvados, ahorro = [], [], 0

    for ruta, motivo in CANDIDATOS:
        p = os.path.join(AQUI, ruta)
        if not os.path.exists(p):
            print(f"\n  --  {ruta:<24} ya no existe")
            continue

        quien = mencionado(ruta)
        if quien:
            salvados.append(ruta)
            print(f"\n  !!  {ruta:<24} SE CONSERVA: lo menciona {quien}")
            continue

        kb = tamano(ruta) / 1024
        print(f"\n  ok  {ruta:<24} {kb:>7.1f} KB")
        print(f"      {motivo}")
        if a.aplicar:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            print("      eliminado")
            ahorro += tamano(ruta) or kb * 1024
        borrados.append(ruta)

    print("\n  " + "-" * 70)
    print(f"  {'eliminados' if a.aplicar else 'a eliminar'}: {len(borrados)}"
          f"   conservados: {len(salvados)}")
    if not a.aplicar and borrados:
        print("  para aplicarlo:  python depurar.py --aplicar")
    print()


if __name__ == "__main__":
    raise SystemExit(main())
