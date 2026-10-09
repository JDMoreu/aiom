#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot.py — reune las metricas internas en results/internos.json.

Es el artefacto que consume reports.py para la parte de catalogo propio: latencia
con desviacion, coste del esquema, acierto del set adversario por categoria y
calibracion. Se regenera con `python snapshot.py`.

Existe para que la documentacion no tenga ninguna cifra escrita a mano.
"""
from __future__ import annotations

import json, statistics, time, urllib.request

import dataset
import dataset_stress as ds
import metrics

BASE = "http://127.0.0.1:8096"
CAT = json.load(open("catalogs/iot.json", encoding="utf-8"))


def decision(q, timeout=300):
    p = {"instructions": CAT["instructions"], "schema": CAT["fields"], "contexts": [q]}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = json.loads(r.read().decode())
    return b["results"][0], b, (time.perf_counter() - t0) * 1000


def main(reps=20):
    base_cases = dataset.cases()
    stress = ds.casos()
    print(f"latencia y esquema: {reps} reps x {len(base_cases)} consultas")
    lat, nodos, rondas = [], [], []
    for i in range(reps + 2):
        for c in base_cases:
            r, b, w = decision(c["q"])
            if i < 2:
                continue
            lat.append(w)
            nodos.append(sum(f.get("scored_nodes", 0) for f in r["fields"].values()))
            t = b.get("timings", {})
            if t.get("rounds"):
                rondas.append(t["rounds"])
    lat_s = sorted(lat)

    print(f"calibracion y acierto base: {len(base_cases)} consultas x 5 reps")
    pares, pares_conf = [], []
    for _ in range(5):
        for c in base_cases:
            r, _, _ = decision(c["q"])
            for f, esp in c["esperado"].items():
                got = r["decision"].get(f)
                ok = str(got) == str(esp)
                pares.append((str(got), str(esp)))
                cf = r["fields"].get(f, {}).get("probability")
                if cf is not None:
                    pares_conf.append((cf, ok))
    m_base = metrics.resumen(pares, pares_conf, nombre="base")

    print(f"set adversario: {len(stress)} casos")
    s_pares, s_conf, por_cat = [], [], {}
    for c in stress:
        r, _, _ = decision(c["q"])
        okn, ev = ds.score(r["decision"], c)
        g = por_cat.setdefault(c["cat"], {"ok": 0, "n": 0})
        g["ok"] += okn
        g["n"] += ev
        for f, esp in c["esperado"].items():
            got = r["decision"].get(f)
            ok = str(got) == str(esp)
            s_pares.append((str(got), str(esp)))
            cf = r["fields"].get(f, {}).get("probability")
            if cf is not None:
                s_conf.append((cf, ok))
    m_stress = metrics.resumen(s_pares, s_conf, nombre="adversario")

    out = {
        "latencia": {"media": round(statistics.mean(lat), 1),
                     "desv": round(statistics.stdev(lat), 1),
                     "p50": round(lat_s[len(lat_s) // 2], 1),
                     "p95": round(lat_s[int(0.95 * len(lat_s))], 1),
                     "min": round(lat_s[0], 1), "max": round(lat_s[-1], 1),
                     "reps": reps, "n": len(lat)},
        "esquema": {"nodos": round(statistics.mean(nodos), 1),
                    "rondas": round(statistics.mean(rondas), 1) if rondas else None},
        "base": {"ok": m_base["aciertos"], "n": m_base["n"],
                 "exactitud": m_base["exactitud"],
                 "ic95": list(m_base["exactitud_ic95"])},
        "adversario": {"ok": m_stress["aciertos"], "n": m_stress["n"],
                       "exactitud": m_stress["exactitud"],
                       "ic95": list(m_stress["exactitud_ic95"]),
                       "exactitud_balanceada": m_stress["exactitud_balanceada"]},
        "adversario_categorias": {k: v for k, v in sorted(por_cat.items())},
        "calibracion": {"ece": round(m_base["ece"], 4),
                        "brier": round(m_base["brier"], 4),
                        "sesgo": round(m_base["sesgo"], 4),
                        "conf_media": round(m_base["conf_media"], 4),
                        "fiabilidad": [list(x) for x in m_base["fiabilidad"]],
                        "nota": "tarea saturada: evidencia debil"},
    }
    with open("results/internos.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nescrito results/internos.json")
    print(f"  latencia  {out['latencia']['media']} ms (desv {out['latencia']['desv']})")
    print(f"  base      {out['base']['ok']}/{out['base']['n']}")
    print(f"  adversario {out['adversario']['ok']}/{out['adversario']['n']} "
          f"({100*out['adversario']['exactitud']:.0f}%)")
    print(f"  ECE       {out['calibracion']['ece']}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
