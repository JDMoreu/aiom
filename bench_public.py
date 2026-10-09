#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_public.py — mide AIOM contra datasets PUBLICOS, para tener cifras
comparables con la industria en vez de solo con nuestro propio fixture.

Dos objetivos:

  WANLI   (alisawuffles/WANLI, CC-BY) — inferencia en lenguaje natural a 3 clases.
          Cifra publicada con la que comparar: SemIf obtuvo 0.637 de exactitud
          balanceada con Qwen3.5-4B leyendo logits directos.
  S1MB    (hotchpotch/s1mb-dataset) — el benchmark especifico de modelos System
          One: 137 pruebas de tipo Noul/Choice/Score.

Se descarga por la API pública de Hugging Face (sin dependencias) y se manda al
endpoint /v1/decision AGRUPANDO consultas, que es lo que medimos que rinde mas.

Uso:
    python bench_public.py wanli --n 256
    python bench_public.py s1mb --list
    python bench_public.py s1mb --suite <nombre> --n 100
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:8096"
HF = "https://datasets-server.huggingface.co"


# --------------------------------------------------------------------------- #
def get_json(url, timeout=60, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aiom-bench"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == intentos - 1:
                raise
            time.sleep(1.5 * (i + 1))


def hf_rows(dataset, config, split, n, page=100):
    """Trae las primeras `n` filas paginando la API publica de HF."""
    filas, offset = [], 0
    while len(filas) < n:
        largo = min(page, n - len(filas))
        url = (f"{HF}/rows?dataset={urllib.parse.quote(dataset)}"
               f"&config={urllib.parse.quote(config)}&split={urllib.parse.quote(split)}"
               f"&offset={offset}&length={largo}")
        d = get_json(url)
        filas += [r["row"] for r in d.get("rows", [])]
        if len(d.get("rows", [])) < largo:
            break
        offset += largo
    return filas[:n]


# --------------------------------------------------------------------------- #
def decision_lote(contextos, instrucciones, esquema, timeout=90):
    """UNA peticion con muchos contextos (lo que medimos que es mas rapido).

    Timeout corto a proposito: con el entorno lanzando el comando dos veces, dos
    procesos compiten por la cache KV del servidor, las peticiones se encolan y
    algunas tardaban hasta agotar un timeout largo. Eso dejaba la suite "colgada"
    sin error visible. A 90 s un caso atascado falla rapido y el reintento
    individual lo aisla.
    """
    p = {"instructions": instrucciones, "schema": esquema, "contexts": contextos}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = json.loads(r.read().decode())
    return b, (time.perf_counter() - t0) * 1000


def ejecutar(casos, campo, instrucciones, esquema, lote=16, verbose=True):
    """casos = [{"ctx":..., "gold":...}] -> [{pred, conf, ms}]"""
    salida = []
    for i in range(0, len(casos), lote):
        trozo = casos[i:i + lote]
        b, wall = decision_lote([c["ctx"] for c in trozo], instrucciones, esquema)
        t = b.get("timings", {})
        for j, r in enumerate(b["results"]):
            d = r["decision"]
            salida.append({
                "pred": d.get(campo),
                "conf": r["fields"].get(campo, {}).get("probability"),
                "gold": trozo[j]["gold"],
                "total_ms": t.get("total_ms"),
                "rondas": t.get("rounds"),
                "nodos": sum(f.get("scored_nodes", 0) for f in r["fields"].values()),
            })
        if verbose:
            print(f"  ... {min(i+lote, len(casos))}/{len(casos)}", flush=True)
    return salida


# --------------------------------------------------------------------------- #
def wilson(k, n, z=1.96):
    import math
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def metricas(res, etiquetas):
    """Exactitud, exactitud balanceada, recall por clase e IC."""
    n = len(res)
    ok = sum(1 for r in res if r["pred"] == r["gold"])
    recalls = {}
    for L in etiquetas:
        idx = [i for i, r in enumerate(res) if r["gold"] == L]
        if idx:
            recalls[L] = (sum(1 for i in idx if res[i]["pred"] == L) / len(idx), len(idx))
    bal = statistics.mean(v for v, _ in recalls.values()) if recalls else 0.0
    lo, hi = wilson(ok, n)
    lat = sorted(r["total_ms"] for r in res if r["total_ms"])
    return {
        "n": n, "ok": ok, "exactitud": ok / n,
        "ic95": (lo, hi), "balanceada": bal, "recalls": recalls,
        "ms_mediana": lat[len(lat) // 2] if lat else None,
        "rondas": statistics.mean(r["rondas"] for r in res if r["rondas"]) if res else None,
        "nodos": statistics.mean(r["nodos"] for r in res),
        "conf_media": statistics.mean(r["conf"] for r in res if r["conf"]) if res else None,
    }


def imprimir(nombre, m, referencia=None):
    print("\n" + "=" * 82)
    print(f"{nombre}")
    print("=" * 82)
    print(f"  casos                 : {m['n']}")
    print(f"  exactitud             : {100*m['exactitud']:.1f}%  ({m['ok']}/{m['n']})"
          f"   IC95% [{100*m['ic95'][0]:.1f}%, {100*m['ic95'][1]:.1f}%]")
    print(f"  exactitud BALANCEADA  : {m['balanceada']:.3f}")
    print(f"  ms por decision       : {m['ms_mediana']:.0f} (mediana, sin colas de red)")
    print(f"  rondas / nodos        : {m['rondas']:.1f} / {m['nodos']:.1f}")
    print(f"  confianza media       : {m['conf_media']:.3f}")
    print(f"\n  {'clase':<16} {'recall':>8} {'n':>6}")
    for L, (r, cnt) in m["recalls"].items():
        print(f"  {L:<16} {r:>8.3f} {cnt:>6}")
    if referencia:
        print(f"\n  referencia publicada  : {referencia}")


# --------------------------------------------------------------------------- #
# WANLI
# --------------------------------------------------------------------------- #
WANLI_INSTR = ("Decides relaciones de inferencia en lenguaje natural (NLI). Dado un "
               "premise (una afirmacion) y una hypothesis (otra afirmacion), elige si "
               "el premise ENTAILS (implica) la hypothesis, si son NEUTRAL (no hay "
               "relacion), o si se CONTRADICT.")
WANLI_SCHEMA = {
    "relacion": {
        "type": "enum",
        "choices": ["entailment", "neutral", "contradiction"],
        "description": ("entailment si el premise implica claramente la hypothesis; "
                        "contradiction si el premise afirma lo contrario; neutral si no "
                        "permite decidir."),
    }
}


def wanli(n=256):
    filas = hf_rows("alisawuffles/WANLI", "default", "test", n)
    print(f"WANLI test: {len(filas)} casos descargados")
    casos = [{"ctx": f"Premise: {f['premise']}\nHypothesis: {f['hypothesis']}",
              "gold": f["gold"]} for f in filas]
    res = ejecutar(casos, "relacion", WANLI_INSTR, WANLI_SCHEMA)
    m = metricas(res, ["entailment", "neutral", "contradiction"])
    imprimir("WANLI (inferencia en lenguaje natural, 3 clases)", m,
             "SemIf con Qwen3.5-4B, logits directos, 256 filas: exactitud balanceada 0.637")
    return m, res


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("wanli")
    p.add_argument("--n", type=int, default=256)
    p.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.cmd == "wanli":
        m, res = wanli(a.n)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump({"metricas": m, "resultados": res}, f, ensure_ascii=False, indent=2)
            print(f"\nescrito {a.out}")


if __name__ == "__main__":
    main()
