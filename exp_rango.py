#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp_rango.py — el recorte silencioso y como detectarlo.

Hallazgo: con `predio` acotado a 1-12, un predio inexistente (30, 45, 99) no se
rechaza: se recorta a un valor valido CON CONFIANZA 1.0. Es el peor modo de fallo
para automatizar, porque nadie se entera.

Hipotesis de arreglo: un campo booleano explicito (`predio_valido`) hace que el
modelo declare la invalidez en vez de disimularla. Aqui se mide si funciona Y
cuanto cuesta, porque anadir un campo anade nodos y latencia.

Controles: predios validos (1, 7, 12) no deben dar predio_valido=False.
"""
from __future__ import annotations

import copy, json, statistics, time, urllib.request

BASE = "http://127.0.0.1:8096"
CAT = json.load(open("catalogs/iot.json", encoding="utf-8"))

INVALIDOS = [
    "el predio 30 lleva dias sin reportar humedad",
    "revisen la temperatura del predio 45",
    "el predio 99 manda datos raros",
    "alerta de bateria en el predio 18",
    "el sensor del predio 57 no responde",
]
# Control: dentro de rango, predio_valido debe ser True
VALIDOS = [
    ("el predio 1 lleva dias sin reportar humedad", 1),
    ("revisen la temperatura del predio 7", 7),
    ("alerta de bateria en el predio 12", 12),
    ("el predio 5 manda datos raros", 5),
    ("la humedad del predio 9 esta rara", 9),
]


def decide(q, cat, timeout=300):
    p = {"instructions": cat["instructions"], "schema": cat["fields"], "contexts": [q]}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = json.loads(r.read().decode())
    return b["results"][0], b, (time.perf_counter() - t0) * 1000


def con_validez(cat):
    """Copia del catalogo con el campo predio_valido anadido."""
    c = copy.deepcopy(cat)
    c["fields"]["predio_valido"] = {
        "type": "boolean",
        "description": ("El numero de predio mencionado esta entre 1 y 12? "
                        "false si la consulta menciona un predio que no existe, "
                        "aunque no mencione ninguno usa true."),
    }
    return c


def coste(cat, qs, reps=5):
    lats, nodos = [], []
    for _ in range(reps):
        for q in qs:
            _, b, wall = decide(q, cat)
            lats.append(wall)
            nodos.append(sum(f.get("scored_nodes", 0)
                             for f in b["results"][0]["fields"].values()))
    return statistics.mean(lats), statistics.mean(nodos)


def main():
    cat_v = con_validez(CAT)
    print("=" * 88)
    print("A) SIN arreglo -- que hace hoy con un predio fuera del esquema")
    print("=" * 88)
    print(f"  {'consulta':<48} {'predio':>7} {'conf':>7}")
    for q in INVALIDOS:
        r, _, _ = decide(q, CAT)
        f = r["fields"].get("predio", {})
        print(f"  {q[:48]:<48} {str(r['decision'].get('predio')):>7} "
              f"{f.get('probability', 0):>7.3f}")

    print("\n" + "=" * 88)
    print("B) CON `predio_valido` -- detecta la invalidez?")
    print("=" * 88)
    print(f"  {'consulta':<48} {'valido':>7} {'conf':>7} {'predio':>7}  veredicto")
    detectados = 0
    for q in INVALIDOS:
        r, _, _ = decide(q, cat_v)
        d = r["decision"]
        v = d.get("predio_valido")
        conf = r["fields"].get("predio_valido", {}).get("probability", 0)
        ok = v is False
        detectados += ok
        print(f"  {q[:48]:<48} {str(v):>7} {conf:>7.3f} {str(d.get('predio')):>7}"
              f"  {'DETECTADO' if ok else 'FALLO'}")
    print(f"\n  -> {detectados}/{len(INVALIDOS)} detectados "
          f"({100*detectados/len(INVALIDOS):.0f}%)")

    print("\n" + "=" * 88)
    print("C) CONTROLES -- predios validos no deben marcarse invalidos")
    print("=" * 88)
    print(f"  {'consulta':<48} {'valido':>7} {'predio':>7}  veredicto")
    fp = 0
    for q, esperado in VALIDOS:
        r, _, _ = decide(q, cat_v)
        d = r["decision"]
        v = d.get("predio_valido")
        malo = v is False or str(d.get("predio")) != str(esperado)
        fp += malo
        print(f"  {q[:48]:<48} {str(v):>7} {str(d.get('predio')):>7}"
              f"  {'FALSO POSITIVO' if malo else 'ok'}")
    print(f"\n  -> {fp}/{len(VALIDOS)} falsos positivos")

    print("\n" + "=" * 88)
    print("D) COSTE de anadir el campo (5 reps x 10 consultas)")
    print("=" * 88)
    qs = [c["q"] for c in __import__("dataset").cases()]
    lb, nb = coste(CAT, qs)
    lv, nv = coste(cat_v, qs)
    print(f"  sin predio_valido : {lb:>7.1f} ms   {nb:>5.1f} nodos puntuados")
    print(f"  con predio_valido : {lv:>7.1f} ms   {nv:>5.1f} nodos puntuados")
    print(f"  coste             : {lv-lb:>+7.1f} ms   {nv-nb:>+5.1f} nodos "
          f"({100*(lv/lb-1):+.1f}%)")
    print("=" * 88)


if __name__ == "__main__":
    main()
