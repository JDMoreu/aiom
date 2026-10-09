#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIOM — all in one mode.

Un solo modelo local, varios modos:

    chat      lenguaje natural -> prosa            (/v1/chat/completions)
    decision  esquema finito   -> valores          (/v1/decision)
    ask       lenguaje natural -> SOLO el valor    (este proyecto)

El modo `ask` es la pieza que no trae llama.cpp: coges la pregunta en lenguaje
natural, la metes como contexto de una decision sobre un catalogo de campos
conocidos, y devuelves unicamente los valores. Cero tokens generados.

Si la pregunta no se puede responder con el catalogo, cae al modo chat sobre el
MISMO modelo cargado: no hay un segundo modelo que cargar.

Sin dependencias: solo la biblioteca estandar de Python.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

DEFAULTS = {
    "server": os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096"),
    "model": os.environ.get("AIOM_MODEL") or None,
    "catalog": os.environ.get("AIOM_CATALOG", "catalogs/iot.json"),
    "timeout": 120,
}


# --------------------------------------------------------------------------- #
# cliente de llama-server
# --------------------------------------------------------------------------- #
def _post(base: str, path: str, payload: dict, timeout: int = 120):
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body, (time.perf_counter() - t0) * 1000.0


# --------------------------------------------------------------------------- #
# modo decision  (elegir valores, no escribirlos)
# --------------------------------------------------------------------------- #
# EL UNICO VOCABULARIO DEL PROYECTO, y su traduccion en un solo sitio.
#
# En todo el proyecto se escribe choice / score / noul. El motor de llama-server habla
# otro idioma por dentro (enum / number / boolean), y esa diferencia se resuelve AQUI y
# en ningun otro fichero. Antes el catalogo escribia los nombres del motor y las otras
# puertas los del proyecto, asi que habia que saber que 'enum' era 'choice' para poder
# leer un catalogo. Ya no: el catalogo tambien habla el idioma del proyecto.
AL_MOTOR = {"choice": "enum", "score": "number", "noul": "boolean"}


def build_schema(catalog: dict) -> dict:
    """Catalogo de campos -> esquema finito que acepta /v1/decision.

    El catalogo declara sus campos en el vocabulario del proyecto (choice, score, noul);
    aqui se traducen al del motor, que es lo unico que ve el servidor.
    """
    schema = {}
    for name, spec in catalog["fields"].items():
        try:
            tipo = AL_MOTOR[spec["type"]]
        except KeyError:
            raise ValueError(
                f"campo '{name}': tipo '{spec['type']}' desconocido. "
                f"Los tipos son: {', '.join(sorted(AL_MOTOR))}") from None
        # Un score de numeros enteros es un ENTERO para el motor: asi devuelve 11 y no
        # 11.0. Se reconoce por el paso y los extremos, y se dice aqui para no obligar a
        # nadie a conocer la palabra 'integer' del motor.
        if (tipo == "number" and spec.get("step") == 1
                and float(spec.get("minimum", 0)).is_integer()
                and float(spec.get("maximum", 0)).is_integer()):
            tipo = "integer"
        f = {"type": tipo, "description": spec["description"]}
        for k in ("choices", "minimum", "maximum", "step", "aggregate"):
            if k in spec:
                f[k] = spec[k]
        schema[name] = f
    return schema


def decide(question: str, catalog: dict, cfg: dict) -> dict:
    """Pregunta en lenguaje natural -> valores. No genera ni un token."""
    payload = {
        "instructions": catalog["instructions"],
        "schema": build_schema(catalog),
        "contexts": [question],
    }
    if cfg.get("model"):
        payload["model"] = cfg["model"]
    body, wall_ms = _post(cfg["server"], "/v1/decision", payload, cfg["timeout"])
    r = body["results"][0]
    t, u = body.get("timings", {}), body.get("usage", {})
    return {
        "decision": r["decision"],
        "fields": r["fields"],
        "usage": {
            "tokens_generated": 0,
            "prompt_tokens": u.get("prompt_tokens"),
            "cached_tokens": u.get("cached_tokens"),
            "scored_rows": u.get("scored_rows"),
        },
        "timings": {"total_ms": round(t.get("total_ms", wall_ms), 1),
                    "wall_ms": round(wall_ms, 1)},
    }


# --------------------------------------------------------------------------- #
# modo chat  (el mismo modelo, respuesta en prosa)
# --------------------------------------------------------------------------- #
def chat(question: str, catalog: dict, cfg: dict) -> dict:
    """La via de chat: un asistente GENERICO.

    A proposito no lleva persona de dominio. El modo decision es el que esta disenado
    para la tarea; el chat es el liston con el que se compara, y para que la comparacion
    diga algo tiene que ser un LLM corriente, no un agente ya especializado en el tema.
    Un catalogo PUEDE traer `chat_system` si alguien quiere darle una voz concreta, pero
    los ejemplos no lo traen: sin nada, el chat contesta como asistente normal.
    """
    payload = {
        "messages": [
            {"role": "system", "content": catalog.get(
                "chat_system") or "Eres un asistente util."},
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
        # El modelo trae el razonamiento activado por defecto: sin esto se gasta
        # el presupuesto entero pensando y devuelve contenido vacio.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if cfg.get("model"):
        payload["model"] = cfg["model"]
    body, wall_ms = _post(cfg["server"], "/v1/chat/completions", payload, cfg["timeout"])
    choice = body["choices"][0]["message"]
    u = body.get("usage", {})
    return {
        "text": (choice.get("content") or "").strip(),
        "usage": {
            "tokens_generated": u.get("completion_tokens", 0),
            "prompt_tokens": u.get("prompt_tokens"),
        },
        "timings": {"wall_ms": round(wall_ms, 1)},
    }


# --------------------------------------------------------------------------- #
# modo ask  (lenguaje natural -> solo el valor, con relevo a chat)
# --------------------------------------------------------------------------- #
def ask(question: str, catalog: dict, cfg: dict, force_mode: str = "auto") -> dict:
    """La puerta de entrada.

    Una sola pasada de decision decide dos cosas a la vez: si la pregunta es
    respondible con el catalogo, y los valores. Si no lo es y estamos en modo
    auto, se releva al chat sobre el mismo modelo.
    """
    if force_mode == "chat":
        out = chat(question, catalog, cfg)
        return {"mode": "chat", **out}

    d = decide(question, catalog, cfg)
    gate = catalog.get("gate_field", "respondible")
    respondible = d["decision"].get(gate, True)

    if force_mode == "auto" and not respondible:
        out = chat(question, catalog, cfg)
        return {"mode": "chat", "reason": f"{gate}=false en la decision",
                "decision_probe": d, **out}

    values = {k: v for k, v in d["decision"].items() if k != gate}
    return {"mode": "decision", "value": values, "fields": d["fields"],
            "usage": d["usage"], "timings": d["timings"]}


def ask_many(questions, catalog, cfg, lote=16, meta=None):
    """Igual que `ask`, pero agrupando consultas en una sola peticion.

    El servidor puntua todo el lote en la misma pasada hacia delante, asi que el
    cliente no necesita un pool de hilos: N preguntas caben en UNA peticion.

    Las consultas que no caben en el catalogo se recogen y se relevan a chat al
    final, para no romper el lote. Esas SI escriben texto y dominan el tiempo
    total: por eso el desglose va en `meta`, no en una sola cifra enganosa.

    Devuelve una lista alineada con `questions`.
    """
    gate = catalog.get("gate_field", "respondible")
    salida = [None] * len(questions)
    a_chat = []
    t_dec = 0.0

    for i in range(0, len(questions), lote):
        trozo = questions[i:i + lote]
        payload = {"instructions": catalog["instructions"],
                   "schema": build_schema(catalog), "contexts": trozo}
        if cfg.get("model"):
            payload["model"] = cfg["model"]
        _t0 = time.perf_counter()
        body, _ = _post(cfg["server"], "/v1/decision", payload, cfg["timeout"])
        t_dec += time.perf_counter() - _t0
        t = body.get("timings", {})
        for j, r in enumerate(body["results"]):
            idx = i + j
            d = r["decision"]
            if not d.get(gate, True):
                a_chat.append(idx)
            else:
                salida[idx] = {"mode": "decision",
                               "value": {k: v for k, v in d.items() if k != gate},
                               "fields": r.get("fields", {}),
                               "timings": {"total_ms": t.get("total_ms")}}

    _t1 = time.perf_counter()
    for idx in a_chat:
        salida[idx] = {"mode": "chat", **chat(questions[idx], catalog, cfg)}
    t_chat = time.perf_counter() - _t1

    if meta is not None:
        meta.update({"decision_ms": t_dec * 1000, "chat_ms": t_chat * 1000,
                     "por_decision": len(questions) - len(a_chat), "por_chat": len(a_chat),
                     "ms_por_decision": (t_dec * 1000 / max(1, len(questions) - len(a_chat))),
                     "ms_por_chat": (t_chat * 1000 / max(1, len(a_chat)))})
    return salida


# --------------------------------------------------------------------------- #
# linea de comandos
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(prog="aiom", description="all in one mode")
    ap.add_argument("--server", default=DEFAULTS["server"])
    ap.add_argument("--model", default=DEFAULTS["model"])
    ap.add_argument("--catalog", default=DEFAULTS["catalog"])
    ap.add_argument("--timeout", type=int, default=DEFAULTS["timeout"])
    sub = ap.add_subparsers(dest="cmd")

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question")
    p_ask.add_argument("--mode", default="auto", choices=["auto", "decision", "chat"])
    p_ask.add_argument("--json", action="store_true", help="detalle completo (probabilidades)")
    p_batch = sub.add_parser("ask-batch", help="agrupa consultas en una peticion")
    p_batch.add_argument("--file", required=True, help="un texto por linea")
    p_batch.add_argument("--lote", type=int, default=16)

    args = ap.parse_args()
    cfg = {"server": args.server, "model": args.model, "timeout": args.timeout}

    try:
        with open(args.catalog, encoding="utf-8") as f:
            catalog = json.load(f)
    except OSError as e:
        print(f"no puedo leer el catalogo {args.catalog}: {e}", file=sys.stderr)
        return 2

    if args.cmd == "ask":
        r = ask(args.question, catalog, cfg, args.mode)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        elif r["mode"] == "decision":
            v = r["value"]
            print("  ".join(f"{k}={val}" for k, val in v.items()) if v else "(sin valores)")
        else:
            print(r.get("text") or "(sin texto)")
    elif args.cmd == "ask-batch":
        with open(args.file, encoding="utf-8") as f:
            qs = [ln.strip() for ln in f if ln.strip()]
        meta = {}
        rs = ask_many(qs, catalog, cfg, args.lote, meta=meta)
        for r in rs:
            if r["mode"] == "decision":
                print("  ".join(f"{k}={v}" for k, v in r["value"].items()))
            else:
                print("[chat] " + (r.get("text") or "(vacio)")[:70])
        print(f"\n{len(qs)} consultas en {(meta['decision_ms']+meta['chat_ms']):.0f} ms",
              file=sys.stderr)
        print(f"  por decision : {meta['por_decision']:>3} consultas  "
              f"{meta['decision_ms']:>8.0f} ms  ({meta['ms_por_decision']:>6.1f} ms/consulta)   0 tokens",
              file=sys.stderr)
        print(f"  por relevo   : {meta['por_chat']:>3} consultas  "
              f"{meta['chat_ms']:>8.0f} ms  ({meta['ms_por_chat']:>6.1f} ms/consulta)   escribe texto",
              file=sys.stderr)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
