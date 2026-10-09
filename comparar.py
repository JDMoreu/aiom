"""Compara el mismo caso en modo decision y en modo chat, uno al lado del otro.

Decision manda LAS TRES preguntas en UNA peticion y devuelve valores.
Chat no sabe hacer varias: hay que preguntarle una a una, y devuelve prosa.

    python comparar.py ejemplos/5_correo_soporte.txt
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiom           # noqa: E402
import preguntar      # noqa: E402

CFG = {"server": aiom.DEFAULTS["server"], "model": aiom.DEFAULTS["model"],
       "timeout": 120}


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else "ejemplos/5_correo_soporte.txt"
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    with open(aiom.DEFAULTS["catalog"], encoding="utf-8") as f:
        catalogo = json.load(f)

    estado, preguntas = preguntar.parsear(texto)

    print("=" * 78)
    print("EL CASO (escrito una vez, en lenguaje natural)")
    print("=" * 78)
    print(estado)
    print()

    # ---------------------------------------------------------------- decision
    print("=" * 78)
    print(f"MODO DECISION  ·  {len(preguntas)} preguntas en UNA peticion, 0 tokens")
    print("=" * 78)
    t0 = time.perf_counter()
    cuerpo, _ = preguntar.ejecutar(estado, preguntas, timeout=CFG["timeout"])
    ms_dec = (time.perf_counter() - t0) * 1000
    campos = cuerpo["results"][0]["fields"]
    tipos = {"enum": "CHOICE", "number": "SCORE", "boolean": "PROBABILITY"}
    for nombre, spec in preguntas:
        f = campos.get(nombre)
        if not f:
            continue
        dist = f.get("probabilities") or {}
        print(f"\n  [{tipos.get(spec['type'], spec['type'])}] "
              f"{spec.get('pregunta') or spec['description'][:60]}")
        if spec["type"] == "number":
            for k, p in sorted(dist.items(), key=lambda kv: float(kv[0])):
                marca = "  <-" if float(k) == float(f["value"]) else ""
                print(f"      nivel {k:<3} {p:6.3f}{marca}")
            punt = sum(float(k) * float(p) for k, p in dist.items())
            print(f"      -> value = {f['value']}   puntuacion = {punt:.2f}")
        else:
            for k, p in sorted(dist.items(), key=lambda kv: -kv[1]):
                marca = "  <-" if str(k) == str(f["value"]) else ""
                print(f"      {k:<12} {p:6.3f}{marca}")
            print(f"      -> value = {f['value']}")
        print(f"      confianza = {f.get('confidence', float('nan')):.3f}")
    print(f"\n  tiempo total: {ms_dec:.0f} ms   ·   tokens escritos: 0")

    # -------------------------------------------------------------------- chat
    print()
    print("=" * 78)
    print(f"MODO CHAT  ·  {len(preguntas)} peticiones sueltas, escribe prosa")
    print("=" * 78)
    ms_chat = 0
    toks = 0
    for nombre, spec in preguntas:
        p = spec.get("pregunta") or spec["description"][:80]
        consulta = f"{estado}\n\nPregunta: {p}"
        r = aiom.chat(consulta, catalogo, CFG)
        ms_chat += r["timings"]["wall_ms"]
        toks += r["usage"].get("tokens_generated") or 0
        print(f"\n  Pregunta: {p}")
        print(f"  Respuesta: {r['text'][:600]}")
        print(f"  ({r['timings']['wall_ms']:.0f} ms, "
              f"{r['usage'].get('tokens_generated', 0)} tokens)")
    print(f"\n  tiempo total: {ms_chat:.0f} ms   ·   tokens escritos: {toks}")

    # ---------------------------------------------------------------- resumen
    print()
    print("=" * 78)
    print("COMPARACION")
    print("=" * 78)
    print(f"  {'':22s} {'decision':>12s} {'chat':>12s}")
    print(f"  {'peticiones al servidor':22s} {1:>12d} {len(preguntas):>12d}")
    print(f"  {'tiempo':22s} {ms_dec:>9.0f} ms {ms_chat:>9.0f} ms")
    print(f"  {'tokens escritos':22s} {0:>12d} {toks:>12d}")
    print(f"  {'formato de salida':22s} {'valores':>12s} {'prosa':>12s}")
    print(f"  {'se puede comparar?':22s} {'si, numeros':>12s} {'no, hay que leer':>12s}")
    print()
    if ms_dec > 0:
        print(f"  decision tardo {ms_chat/ms_dec:.1f}x menos y no gasto tokens.")


if __name__ == "__main__":
    main()
