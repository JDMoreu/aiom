#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench.py — banco de pruebas de AIOM.

Compara los dos modos sobre LAS MISMAS consultas y LA MISMA tarea (extraer los
campos), variando el paralelismo:

    decision  llama.cpp puntua las opciones del esquema; no genera tokens
    chat      el modelo escribe el JSON token a token

Mide por modo y nivel de concurrencia:

    latencia  media, p50, p95, min, max   (la media sola esconde la cola)
    pared     tiempo total del bloque
    caudal    consultas/segundo
    tokens    generados (el coste que no baja solo por hardware)
    acierto   sobre los campos inequivocos del dataset
    ruteo     los no respondibles deben acabar en chat

Uso:
    python bench.py --concurrency 1,2,4,8,16
    python bench.py --modes decision --concurrency 1,4,16
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import dataset

CHAT_TEMPLATE = """Extrae los campos de esta consulta de un operador de campo.

Devuelve SOLO un objeto JSON, sin texto adicional ni explicaciones, con estas claves:
  "magnitud": una de temperatura, humedad, bateria, senal, riego, ninguna
  "predio": numero entero del predio
  "urgencia": una de baja, media, alta

Consulta: {q}
JSON:"""


# --------------------------------------------------------------------------- #
def _post(base, path, payload, timeout):
    req = urllib.request.Request(base.rstrip("/") + path,
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode("utf-8"))
    return body, (time.perf_counter() - t0) * 1000.0


def _json_from(text):
    """Primer objeto JSON del texto, ignorando razonamiento previo."""
    if not text:
        return {}
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# una consulta en cada modo
# --------------------------------------------------------------------------- #
def query_decision(q, cat, cfg):
    payload = {"instructions": cat["instructions"], "schema": cat["fields"],
               "contexts": [q]}
    if cfg.get("model"):
        payload["model"] = cfg["model"]
    body, wall = _post(cfg["server"], "/v1/decision", payload, cfg["timeout"])
    r = body["results"][0]
    u, t = body.get("usage", {}), body.get("timings", {})
    return {"wall_ms": wall, "inner_ms": t.get("total_ms", wall),
            "tokens": 0, "prompt_tokens": u.get("prompt_tokens"),
            "cached_tokens": u.get("cached_tokens"), "values": r["decision"],
            "timings": t}


def query_chat(q, cat, cfg):
    payload = {"messages": [{"role": "user", "content": CHAT_TEMPLATE.format(q=q)}],
               "temperature": 0, "max_tokens": 256,
               "chat_template_kwargs": {"enable_thinking": False}}
    if cfg.get("model"):
        payload["model"] = cfg["model"]
    body, wall = _post(cfg["server"], "/v1/chat/completions", payload, cfg["timeout"])
    u = body.get("usage", {})
    return {"wall_ms": wall, "inner_ms": wall,
            "tokens": u.get("completion_tokens", 0),
            "prompt_tokens": u.get("prompt_tokens"), "cached_tokens": 0,
            "values": _json_from(body["choices"][0]["message"].get("content") or ""),
            "timings": {}}


MODOS = {"decision": query_decision, "chat": query_chat}


# --------------------------------------------------------------------------- #
def run_block(mode, cases, cat, cfg, concurrency):
    """Lanza TODAS las consultas con `concurrency` en vuelo y mide."""
    fn = MODOS[mode]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        raws = list(ex.map(lambda c: fn(c["q"], cat, cfg), cases))
    wall_s = time.perf_counter() - t0

    lat = sorted(r["wall_ms"] for r in raws)
    tok = sum(r["tokens"] for r in raws)
    ok = ev = 0
    for r, c in zip(raws, cases):
        a, b = dataset.score(r["values"], c)
        ok += a
        ev += b

    def pct(p):
        return lat[min(len(lat) - 1, int(round(p / 100 * (len(lat) - 1))))]

    gate = cat.get("gate_field", "respondible")
    gates = {True: [], False: []}
    for r, c in zip(raws, cases):
        gates[c["respondible"]].append(bool(r["values"].get(gate, True)))
    ruteo = (sum(1 for v in gates[False] if v is False) / len(gates[False])
             if gates[False] else None)

    return {
        "modo": mode, "concurrencia": concurrency, "consultas": len(cases),
        "pared_s": round(wall_s, 3),
        "caudal_qs": round(len(cases) / wall_s, 2),
        "latencia_ms": {"media": round(statistics.mean(lat), 1),
                        "p50": round(pct(50), 1), "p95": round(pct(95), 1),
                        "min": round(lat[0], 1), "max": round(lat[-1], 1)},
        "tokens_generados": tok,
        "tokens_por_consulta": round(tok / len(cases), 1),
        "prompt_tokens": raws[0]["prompt_tokens"],
        "cached_tokens": raws[0]["cached_tokens"],
        "acierto_campos": f"{ok}/{ev}" if ev else "n/d",
        "acierto_pct": round(100 * ok / ev, 1) if ev else None,
        "ruteo_no_respondibles_pct": (round(100 * ruteo, 1) if ruteo is not None else None),
        "detalle": [{"q": c["q"][:64], "ms": round(r["wall_ms"], 1), "tok": r["tokens"],
                     "esperado": c["esperado"], "vals": r["values"]}
                    for r, c in zip(raws, cases)],
    }


def config_snapshot(cfg):
    """Lo que hace falta para reproducir: estado del servidor."""
    snap = {"server": cfg["server"], "model": cfg.get("model")}
    try:
        body, _ = _post(cfg["server"], "/props", {}, 10)
        snap["props_keys"] = sorted(body.keys())[:12]
        snap["raw_props"] = {k: body[k] for k in list(body)[:8]}
    except Exception as e:
        snap["props_error"] = str(e)[:150]
    try:
        body, _ = _post(cfg["server"], "/health", {}, 10)
        snap["health"] = body.get("status")
    except Exception:
        pass
    return snap


def run_bench(cat, cfg, niveles=(1, 2, 4, 8, 16), modos=("decision", "chat"),
              out="results", warmup=2, verbose=True):
    cases = dataset.cases()
    if verbose:
        print(f"dataset: {len(cases)} consultas "
              f"({sum(c['respondible'] for c in cases)} respondibles, "
              f"{sum(not c['respondible'] for c in cases)} para chat)")
        print("calentando prefijo...", flush=True)
    for _ in range(warmup):
        query_decision(cases[0]["q"], cat, cfg)

    res = {"config": config_snapshot(cfg),
           "dataset": {"total": len(cases),
                       "respondibles": sum(c["respondible"] for c in cases),
                       "no_respondibles": sum(not c["respondible"] for c in cases)},
           "bloques": []}

    for modo in modos:
        for c in niveles:
            if verbose:
                print(f"  {modo:<9} concurrencia={c:<3} ...", end="", flush=True)
            b = run_block(modo, cases, cat, cfg, c)
            res["bloques"].append(b)
            if verbose:
                print(f" pared={b['pared_s']:>7.2f}s  p50={b['latencia_ms']['p50']:>7.1f}ms  "
                      f"caudal={b['caudal_qs']:>5.2f}q/s  tok={b['tokens_generados']:>5}  "
                      f"acierto={b['acierto_campos']}")

    if out:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "bench.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        with open(os.path.join(out, "bench.csv"), "w", encoding="utf-8") as f:
            f.write("modo,concurrencia,pared_s,caudal_qs,lat_media_ms,lat_p50_ms,lat_p95_ms,"
                    "lat_min_ms,lat_max_ms,tokens_total,tokens_por_consulta,"
                    "acierto_pct,ruteo_pct\n")
            for b in res["bloques"]:
                L = b["latencia_ms"]
                f.write(f"{b['modo']},{b['concurrencia']},{b['pared_s']},{b['caudal_qs']},"
                        f"{L['media']},{L['p50']},{L['p95']},{L['min']},{L['max']},"
                        f"{b['tokens_generados']},{b['tokens_por_consulta']},"
                        f"{b['acierto_pct']},{b['ruteo_no_respondibles_pct']}\n")
        if verbose:
            print(f"\nescrito {out}/bench.json y {out}/bench.csv")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8096")
    ap.add_argument("--model", default=None)
    ap.add_argument("--catalog", default="catalogs/iot.json")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--concurrency", default="1,2,4,8,16")
    ap.add_argument("--modes", default="decision,chat")
    ap.add_argument("--out", default="results")
    ap.add_argument("--warmup", type=int, default=2)
    a = ap.parse_args()
    cat = json.load(open(a.catalog, encoding="utf-8"))
    run_bench(cat, {"server": a.server, "model": a.model, "timeout": a.timeout},
              [int(x) for x in a.concurrency.split(",")], a.modes.split(","),
              a.out, a.warmup)


if __name__ == "__main__":
    main()
