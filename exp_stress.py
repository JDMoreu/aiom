#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp_stress.py — mide el set adversario por categoria.

Para los campos dentro del esquema: acierto por categoria con intervalo de Wilson.
Para `fuera_rango`: como NO hay valor esperado posible (el esquema tope en 12),
se reporta QUE devuelve el modelo. Si recorta a 12 en silencio, el sistema miente
con confianza, que es el peor modo de fallo para automatizar.
"""
from __future__ import annotations

import json, statistics, time, urllib.request

import dataset_stress as ds

BASE = "http://127.0.0.1:8096"
CAT = json.load(open("catalogs/iot.json", encoding="utf-8"))


def decision(q, timeout=300):
    p = {"instructions": CAT["instructions"], "schema": CAT["fields"], "contexts": [q]}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = json.loads(r.read().decode())
    return b["results"][0], (time.perf_counter() - t0) * 1000


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    import math
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    casos = ds.casos()
    print(f"set adversario: {len(casos)} casos, "
          f"{sum(len(c['esperado']) for c in casos)} campos evaluables\n")

    por_cat = {}
    salidas = []
    for c in casos:
        r, wall = decision(c["q"])
        d = r["decision"]
        ok, ev = ds.score(d, c)
        confs = [r["fields"].get(f, {}).get("probability") for f in c["esperado"]]
        entrada = {"caso": c, "d": d, "ok": ok, "ev": ev, "wall": wall,
                   "conf": statistics.mean(confs) if confs else None,
                   "gate": d.get(CAT.get("gate_field", "respondible"))}
        salidas.append(entrada)
        g = por_cat.setdefault(c["cat"], {"ok": 0, "ev": 0, "n": 0, "lat": [], "det": []})
        g["ok"] += ok
        g["ev"] += ev
        g["n"] += 1
        g["lat"].append(wall)
        g["det"].append((c["q"], d, ok, ev))

    print("=" * 84)
    print(f"{'categoria':<14} {'casos':>6} {'acierto':>12} {'IC95%':>18} {'lat media':>10} {'gate ok':>8}")
    print("=" * 84)
    for cat, g in por_cat.items():
        if g["ev"]:
            lo, hi = wilson(g["ok"], g["ev"])
            acc = f"{g['ok']}/{g['ev']} ({100*g['ok']/g['ev']:.0f}%)"
            ic = f"[{100*lo:.0f}%, {100*hi:.0f}%]"
        else:
            acc, ic = "n/d", "n/d"
        # para no_resp el acierto real es haber marcado respondible=False
        gates = [x for x in g["det"]]
        gate_ok = (sum(1 for _, d, _, _ in gates
                       if d.get("respondible") is False) / len(gates))
        print(f"{cat:<14} {g['n']:>6} {acc:>12} {ic:>18} "
              f"{statistics.mean(g['lat']):>9.0f}ms {100*gate_ok:>7.0f}%")

    # ---- detalle de los casos que importan ---------------------------------
    print("\n" + "=" * 84)
    print("DETALLE: fuera de rango (el predio supera el maximo del esquema, 12)")
    print("=" * 84)
    for e in salidas:
        if e["caso"]["cat"] != "fuera_rango":
            continue
        d = e["d"]
        p = e["d"].get("predio")
        conf = e.get("conf")
        aviso = ""
        if isinstance(p, int) and p > 12:
            aviso = " *** FUERA DEL ESQUEMA"
        elif p == 12:
            aviso = " *** RECORTADO AL TOPE (12)"
        print(f"  {e['caso']['q'][:52]:<52} predio={p!r:<5} conf={conf if conf is None else round(conf,3)}"
              f"{aviso}")

    print("\n" + "=" * 84)
    print("DETALLE: multi_predio y no_resp (donde no hay respuesta unica)")
    print("=" * 84)
    for e in salidas:
        if e["caso"]["cat"] not in ("multi_predio", "no_resp"):
            continue
        d = e["d"]
        print(f"  [{e['caso']['cat']:<12}] respondible={d.get('respondible')}  "
              f"{e['caso']['q'][:44]}")

    print("\n" + "=" * 84)
    print("DETALLE: fuera_cat (magnitud que el catalogo no cubre)")
    print("=" * 84)
    for e in salidas:
        if e["caso"]["cat"] != "fuera_cat":
            continue
        d = e["d"]
        print(f"  magnitud={str(d.get('magnitud')):<12} predio={d.get('predio')}   "
              f"conf={round(e['conf'],3) if e['conf'] else None}   {e['caso']['q'][:40]}")

    # ---- veredicto ---------------------------------------------------------
    tot_ok = sum(e["ok"] for e in salidas)
    tot_ev = sum(e["ev"] for e in salidas)
    print("\n" + "=" * 84)
    print(f"  GLOBAL set adversario: {tot_ok}/{tot_ev} campos ({100*tot_ok/tot_ev:.0f}%)")
    print(f"  (dataset base saturado: 53/53 = 100% -- esta es la cifra que informa)")
    print("=" * 84)


if __name__ == "__main__":
    main()
