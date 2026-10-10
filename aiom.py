#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIOM — all in one mode.

Un solo modelo local, dos modos:

    chat      lenguaje natural -> prosa            (/v1/chat/completions)
    decision  esquema finito   -> valores          (/v1/decision)

La decision es la pieza que no trae llama.cpp: en vez de dejar que el modelo escriba la
respuesta, se le da un esquema finito y se le pide que elija. Devuelve UNICAMENTE los
valores, y no genera ni un token.

El esquema NO vive aqui: lo trae cada peticion. El formato `natural` lo arma a partir de
las cabeceras del texto, y el `tipado` lo lee del JSON de TypeSafe. Este modulo solo tiene
lo que comparten: hablar con llama-server, el vocabulario del proyecto y el modo chat.

Sin dependencias: solo la biblioteca estandar de Python.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

DEFAULTS = {
    "server": os.environ.get("AIOM_SERVER", "http://127.0.0.1:8096"),
    "model": os.environ.get("AIOM_MODEL") or None,
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
# EL UNICO VOCABULARIO DEL PROYECTO, y su traduccion en un solo sitio.
#
# En todo el proyecto se escribe choice / score / noul. El motor de llama-server habla otro
# idioma por dentro (enum / number / boolean), y esa diferencia se resuelve AQUI y en
# ningun otro fichero. El formato natural arma su esquema con los nombres del proyecto y
# los traduce al salir; el tipado ya los trae traducidos.
# --------------------------------------------------------------------------- #
AL_MOTOR = {"choice": "enum", "score": "number", "noul": "boolean"}

# Y al reves, para lo que se DEVUELVE: lo que manda el motor puede llegar con su nombre
# (el formato natural arma el esquema por dentro) o con el del proyecto (el tipado ya lo
# trae traducido). Esta tabla los unifica de vuelta. `integer` es un score de numeros
# enteros, y se llama score como cualquier otro.
AL_PROYECTO = {v: k for k, v in AL_MOTOR.items()}
AL_PROYECTO["integer"] = "score"


# --------------------------------------------------------------------------- #
# modo chat  (el mismo modelo, respuesta en prosa)
# --------------------------------------------------------------------------- #
def chat(question: str, cfg: dict) -> dict:
    """La via de chat: un asistente GENERICO.

    A proposito no lleva persona de dominio. El modo decision es el que esta disenado
    para la tarea; el chat es el liston con el que se compara, y para que la comparacion
    diga algo tiene que ser un LLM corriente, no un agente ya especializado en el tema.
    """
    payload = {
        "messages": [
            {"role": "system", "content": "Eres un asistente util."},
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
        # El tope es alto a proposito. Con 512 el chat se cortaba a media respuesta en
        # cuanto habia tres o cuatro preguntas, y una respuesta cortada no se puede
        # comparar con nada. El contexto del servidor son 32768 tokens, asi que 2048 deja
        # sitio de sobra para que el caso y las respuestas quepan enteros.
        "max_tokens": 2048,
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
