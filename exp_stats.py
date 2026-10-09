#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp_stats.py — validacion estadistica y calibracion.

Tres cosas que el benchmark original no daba:

  1. INTERVALOS DE CONFIANZA. Una sola pasada no es un dato validado; aqui se
     repite N veces y se reporta la variacion entre corridas.
  2. CALIBRACION (ECE). El endpoint devuelve `probability` por campo. Eso permite
     responder la pregunta que de verdad importa para decidir con umbrales:
     cuando dice 0.9, ¿acierta el 90% de las veces?
  3. TABLA DE FIABILIDAD. Por tramo de confianza, cuanto acierta de verdad.

Todo se mide contra la verdad de referencia de dataset.py.
"""
from __future__ import annotations

import json, math, statistics, time, urllib.request

import dataset

BASE = "http://127.0.0.1:8096"
CAT = json.load(open("catalogs/iot.json", encoding="utf-8"))
CASES = dataset.cases()


def decision(q, timeout=300):
    p = {"instructions": CAT["instructions"], "schema": CAT["fields"], "contexts": [q]}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = json.loads(r.read().decode())
    return b, (time.perf_counter() - t0) * 1000


def unpase(reps):
    """Ejecuta el dataset `reps` veces. Las primeras 2 se descartan (calentamiento)."""
    corridas = []
    for i in range(reps + 2):
        lat, pares, nodos, rondas = [], [], [], []
        for c in CASES:
            b, wall = decision(c["q"])
            r = b["results"][0]
            t = b.get("timings", {})
            nodos.append(sum(f.get("scored_nodes", 0) for f in r["fields"].values()))
            rondas.append(t.get("rounds"))
            for f, esp in c["esperado"].items():
                got = r["decision"].get(f)
                conf = r["fields"].get(f, {}).get("probability")
                pares.append((conf, str(got) == str(esp), f, str(got), str(esp)))
            if i >= 2:
                lat.append(wall)
        if i >= 2:
            corridas.append({"lat": lat, "pares": pares,
                             "nodos": statistics.mean(nodos),
                             "rondas": max(r for r in rondas if r)})
    return corridas


# --------------------------------------------------------------------------- #
def wilson(k, n, z=1.96):
    """Intervalo de Wilson para una proporcion: mejor que el normal con n chico."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def ece(pares, bins=10):
    """Expected Calibration Error + tabla de fiabilidad.

    ECE = suma ponderada de |precision - confianza| por tramo. 0 es perfecto.
    """
    filas, total = [], 0
    e = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        sel = [(c, ok) for c, ok, *_ in pares
               if c is not None and (lo <= c < hi or (i == bins - 1 and c >= hi))]
        if not sel:
            filas.append((lo, hi, 0, None, None, None))
            continue
        conf = statistics.mean(c for c, _ in sel)
        acc = sum(1 for _, ok in sel if ok) / len(sel)
        filas.append((lo, hi, len(sel), conf, acc, acc - conf))
        e += len(sel) * abs(acc - conf)
        total += len(sel)
    return (e / total if total else 0.0), filas, total


def brier(pares):
    return statistics.mean((c - (1.0 if ok else 0.0)) ** 2
                           for c, ok, *_ in pares if c is not None)


# --------------------------------------------------------------------------- #
def main(reps=10):
    print(f"dataset: {len(CASES)} consultas | {reps} repeticiones (+2 de calentamiento)\n")
    corridas = unpase(reps)

    # ---- acierto con intervalo de confianza ---------------------------------
    print("=" * 78)
    print("ACIERTO (campos evaluables)")
    print("=" * 78)
    for f in ("magnitud", "predio", "urgencia", "respondible"):
        pares = [x for cr in corridas for x in cr["pares"] if x[2] == f]
        if not pares:
            continue
        k, n = sum(1 for x in pares if x[1]), len(pares)
        lo, hi = wilson(k, n)
        print(f"  {f:<12} {k:>4}/{n:<5} {100*k/n:>6.1f}%   IC95% [{100*lo:.1f}%, {100*hi:.1f}%]")

    # ---- variacion entre corridas ------------------------------------------
    accs = [sum(1 for x in cr["pares"] if x[1]) / len(cr["pares"]) for cr in corridas]
    print(f"\n  entre corridas: min {100*min(accs):.1f}%  max {100*max(accs):.1f}%  "
          f"desv {100*statistics.stdev(accs):.2f} pp")
    print(f"  -> {'ESTABLE' if statistics.stdev(accs) < 0.02 else 'INESTABLE'} "
          f"(umbral 2 pp)")

    # ---- latencia ----------------------------------------------------------
    print("\n" + "=" * 78)
    print("LATENCIA (ms por consulta, pared)")
    print("=" * 78)
    medias = [statistics.mean(cr["lat"]) for cr in corridas]
    todas = [x for cr in corridas for x in cr["lat"]]
    todas.sort()
    n = len(todas)
    se = statistics.stdev(medias) / math.sqrt(len(medias))
    t = 2.262  # t de Student, 9 grados de libertad, 95%
    print(f"  media    {statistics.mean(medias):>7.1f} ms   IC95% "
          f"[{statistics.mean(medias)-t*se:.1f}, {statistics.mean(medias)+t*se:.1f}]")
    print(f"  p50      {todas[n//2]:>7.1f} ms")
    print(f"  p95      {todas[int(0.95*n)]:>7.1f} ms")
    print(f"  min/max  {todas[0]:>7.1f} / {todas[-1]:.1f} ms")

    # ---- coste del esquema -------------------------------------------------
    print("\n" + "=" * 78)
    print("COSTE DEL ESQUEMA (nodos puntuados y rondas)")
    print("=" * 78)
    print(f"  nodos puntuados por consulta : {statistics.mean([c['nodos'] for c in corridas]):.1f}")
    print(f"  rondas de scoring            : {statistics.mean([c['rondas'] for c in corridas]):.1f}")

    # ---- calibracion -------------------------------------------------------
    pares = [x for cr in corridas for x in cr["pares"]]
    e, filas, total = ece(pares)
    print("\n" + "=" * 78)
    print("CALIBRACION")
    print("=" * 78)
    print(f"  ECE        {e:.4f}   (0 = perfecto)")
    print(f"  Brier      {brier(pares):.4f}   (mas bajo mejor)")
    print(f"  n          {total} decisiones de campo\n")
    print(f"  {'tramo':>14} {'n':>6} {'confianza':>10} {'acierto':>9} {'desvio':>8}")
    for lo, hi, cnt, conf, acc, gap in filas:
        if cnt == 0:
            continue
        print(f"  {lo:.1f}-{hi:.1f}".rjust(14) + f" {cnt:>6} {conf:>10.3f} {acc:>9.3f} "
              f"{gap:>+8.3f}")

    print("\n" + "=" * 78)
    veredicto = ("bien calibrado" if e < 0.05 else
                 "calibracion aceptable" if e < 0.10 else "mal calibrado")
    print(f"  ECE {e:.4f} -> {veredicto} (referencia: SemIf reporta 0.038-0.208 crudo)")
    print("=" * 78)
    return {"ece": e, "brier": brier(pares), "accs": accs, "medias": medias,
            "filas": filas, "n": total}


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
