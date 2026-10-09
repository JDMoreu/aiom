"""API HTTP de AIOM: un endpoint, tres formatos de entrada.

El .txt sigue siendo la puerta HUMANA (escribir una pregunta sin saber JSON), y esto
es la puerta de PROGRAMA: otro sistema manda la pregunta por HTTP y recibe JSON.

Se elige el formato con el campo `formato`, y no se adivina:

    POST /ask   {"formato": "texto",   "question": "..."}       una pregunta suelta
    POST /ask   {"formato": "natural", "entrada": "..."}        el contenido de un .txt
    POST /ask   {"formato": "tipado",  "state": ..., "questions": ...}

`texto` pregunta contra el CATALOGO (los campos que el catalogo declara). `natural` y
`tipado` traen su propio esquema en el cuerpo, asi que no usan el catalogo.

    python api.py                    # escucha en 8100
    python api.py --port 9000

    curl -s localhost:8100/          # la documentacion, en JSON
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiom                    # noqa: E402
import ejemplos_typesafe       # noqa: E402  (reutiliza su traductor de TypeSafe)
import preguntar               # noqa: E402

FORMATOS = ("texto", "natural", "tipado")

# --------------------------------------------------------------------------- #
# los tres formatos -> una lista uniforme de resultados
# --------------------------------------------------------------------------- #
def _de_campos(campos, preguntas):
    """Respuesta del servidor -> lista de resultados, uno por pregunta.

    `campos` es el bloque `fields` de /v1/decision; `preguntas` la lista
    [(nombre, spec)] con la pregunta en lenguaje natural, para poder devolverla.
    """
    salida = []
    for nombre, spec in preguntas:
        f = campos.get(nombre)
        if not f:
            continue
        salida.append({
            "campo": nombre,
            "tipo": spec.get("type"),
            "pregunta": spec.get("pregunta") or spec.get("description", "")[:80],
            "value": f.get("value"),
            "probability": f.get("probability"),
            "probabilities": f.get("probabilities"),
            "confidence": f.get("confidence"),
        })
    return salida


def por_texto(cuerpo, catalogo, cfg):
    """Una pregunta suelta contra el catalogo (lo que hacia aiom.ask)."""
    q = cuerpo.get("question")
    if not isinstance(q, str) or not q.strip():
        raise ValueError("falta 'question'")
    r = aiom.ask(q, catalogo, cfg, cuerpo.get("mode", "auto"))
    if r["mode"] == "chat":
        return {"resultados": [{"modo": "chat", "texto": r.get("text")}],
                "tiempo_ms": r["timings"]["wall_ms"],
                "tokens": r["usage"].get("tokens_generated") or 0}
    # El `tipo` y el nombre de cada campo salen del CATALOGO: la respuesta del
    # servidor trae value/probabilities/confidence, pero no de que tipo es el campo.
    esquema = catalogo.get("fields", {})
    preguntas = [(k, {"type": esquema.get(k, {}).get("type"),
                      "pregunta": esquema.get(k, {}).get("description", "")})
                 for k in (r.get("fields") or {})]
    return {"resultados": _de_campos(r["fields"], preguntas),
            "tiempo_ms": r["timings"]["total_ms"], "tokens": 0}


def por_natural(cuerpo, catalogo, cfg):
    """El contenido de un .txt: una o varias preguntas, en una sola peticion."""
    texto = cuerpo.get("entrada")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("falta 'entrada'")
    estado, preguntas = preguntar.parsear(texto)
    t0 = time.perf_counter()
    res_crudo, _ = preguntar.ejecutar(estado, preguntas, timeout=cfg["timeout"])
    ms = (time.perf_counter() - t0) * 1000.0
    campos = res_crudo["results"][0]["fields"]
    return {"resultados": _de_campos(campos, preguntas), "tiempo_ms": round(ms, 1),
            "tokens": 0, "n_preguntas": len(preguntas)}


def por_tipado(cuerpo, catalogo, cfg):
    """El formato de TypeSafe: state.input + questions.<nombre> con criteria."""
    if "state" not in cuerpo or "questions" not in cuerpo:
        raise ValueError("faltan 'state' y 'questions'")
    res_crudo, ms, nombre = ejemplos_typesafe.ejecutar(cuerpo, timeout=cfg["timeout"])
    campos = res_crudo["results"][0]["fields"]
    # El tipo sale de la PETICION: la respuesta del servidor no lo trae.
    spec_pedida = cuerpo["questions"].get(nombre, {})
    spec = {"type": spec_pedida.get("type"),
            "pregunta": spec_pedida.get("instructions", "")}
    return {"resultados": _de_campos(campos, [(nombre, spec)]),
            "tiempo_ms": round(ms, 1), "tokens": 0, "n_preguntas": 1}


CONVERSORES = {"texto": por_texto, "natural": por_natural, "tipado": por_tipado}


# --------------------------------------------------------------------------- #
# la comparativa: la misma pregunta por las dos vias, en una sola peticion
# --------------------------------------------------------------------------- #
def _chat(texto, catalogo, cfg):
    """Una pregunta por la via de chat (prosa)."""
    r = aiom.ask(texto, catalogo, cfg, "chat")
    return {"modo": "chat", "texto": r.get("text"),
            "tiempo_ms": r["timings"]["wall_ms"],
            "tokens": r["usage"].get("tokens_generated") or 0}


def prompts_texto(cuerpo, catalogo, cfg):
    return [cuerpo["question"]]


def prompts_natural(cuerpo, catalogo, cfg):
    estado, preguntas = preguntar.parsear(cuerpo["entrada"])
    return [f"{estado}\n\nask: {c['pregunta']}" for _, c in preguntas]


def prompts_tipado(cuerpo, catalogo, cfg):
    entrada = cuerpo["state"].get("input", "")
    return [f"{entrada}\n\nask: {c.get('instructions', '')}"
            for c in cuerpo["questions"].values()]


PROMPTS = {"texto": prompts_texto, "natural": prompts_natural, "tipado": prompts_tipado}


def comparar(r_decision, cuerpo, catalogo, cfg, formato):
    """Envuelve el resultado de decision y le anade la via de chat, lado a lado.

    Se hace aqui y no en el cliente para que los dos tiempos sean de la MISMA
    corrida: medir en dos llamadas separadas daria tiempos de momentos distintos.
    """
    respuestas = [_chat(p, catalogo, cfg) for p in PROMPTS[formato](cuerpo, catalogo, cfg)]
    return {
        "formato": formato,
        "comparar": True,
        "n_preguntas": r_decision.get("n_preguntas", len(r_decision.get("resultados", []))),
        "decision": {
            "peticiones": 1,
            "resultados": r_decision["resultados"],
            "tiempo_ms": r_decision["tiempo_ms"],
            "tokens": 0,
        },
        "chat": {
            "peticiones": len(respuestas),
            "resultados": respuestas,
            "tiempo_ms": round(sum(r["tiempo_ms"] for r in respuestas), 1),
            "tokens": sum(r["tokens"] for r in respuestas),
        },
    }


# --------------------------------------------------------------------------- #
# servidor
# --------------------------------------------------------------------------- #
DOC = {
    "POST /ask": {
        "descripcion": "Pregunta al modelo local. El formato se declara, no se adivina.",
        "formatos": {
            "texto": {
                "cuerpo": {"formato": "texto", "question": "¿...?", "mode": "auto"},
                "nota": "una pregunta suelta, contra los campos del CATALOGO. "
                        "mode: auto | decision | chat",
            },
            "natural": {
                "cuerpo": {"formato": "natural",
                           "entrada": "input: ...\n\nask: ...\nchoice:\n  a: ..."},
                "nota": "el contenido de un .txt: una o varias preguntas separadas por "
                        "---. Trae su propio esquema, no usa el catalogo.",
            },
            "tipado": {
                "cuerpo": {"formato": "tipado",
                           "state": {"input": "..."},
                           "questions": {"decision": {
                               "type": "choice|score|noul",
                               "instructions": "...",
                               "criteria": {"a": "...", "b": "..."}}}},
                "nota": "el formato de TypeSafe/Jev, tal cual.",
            },
        },
        "respuesta": {
            "formato": "el que mandaste",
            "n_preguntas": "int",
            "resultados": [{"campo": "str", "tipo": "enum|number|boolean",
                            "pregunta": "str", "value": "el valor elegido",
                            "probability": "float", "probabilities": "{opcion: float}",
                            "confidence": "float"}],
            "tiempo_ms": "float", "tokens": "int (0 en decision)",
        },
    },
    "GET /health": "estado de aiom y de llama-server",
    "GET /catalog": "el catalogo cargado",
}


class Handler(BaseHTTPRequestHandler):
    catalog: dict = {}
    cfg: dict = {}

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self) -> None:
        # La UI la sirve esta misma API, asi que no hay CORS. Pero si alguien abre
        # el HTML desde el disco (file://) el navegador manda Origin: null, y sin
        # estas cabeceras la peticion se cae. Es una herramienta local, no un
        # servicio publico: por eso el comodin es aceptable aqui.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _html(self, ruta: str) -> None:
        try:
            with open(ruta, encoding="utf-8") as f:
                body = f.read().encode("utf-8")
        except OSError as e:
            return self._send(404, {"error": f"no puedo leer {ruta}: {e}"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            # /health de llama-server es GET. Con POST devolvia 404 y el estado salia
            # como 'unreachable' aunque el servidor estuviera perfectamente.
            try:
                url = self.cfg["server"].rstrip("/") + "/health"
                with urllib.request.urlopen(url, timeout=5) as r:
                    cuerpo = json.loads(r.read().decode("utf-8"))
                self._send(200, {"aiom": "ok", "llama_server": cuerpo})
            except Exception as e:                                  # noqa: BLE001
                self._send(503, {"aiom": "ok", "llama_server": f"unreachable: {e}"})
        elif self.path.startswith("/catalog"):
            self._send(200, self.catalog)
        elif self.path.startswith("/docs"):
            self._send(200, {"api": "AIOM", "endpoints": DOC})
        elif self.path in ("/", "/ui", "/index.html"):
            self._html(self.cfg["ui"])
        else:
            self._send(404, {"error": "usa POST /ask, o GET / para la interfaz"})

    def do_POST(self):
        if not self.path.startswith("/ask"):
            return self._send(404, {"error": "usa POST /ask"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception as e:                                      # noqa: BLE001
            return self._send(400, {"error": f"cuerpo invalido: {e}"})

        # El formato se declara. Si no viene, se deduce solo del campo que traiga,
        # y si tampoco, se dice que falta en vez de adivinar.
        formato = cuerpo.get("formato")
        if formato is None:
            formato = ("texto" if "question" in cuerpo else
                       "natural" if "entrada" in cuerpo else
                       "tipado" if "questions" in cuerpo else None)
        if formato not in CONVERSORES:
            return self._send(400, {
                "error": f"formato no valido: {formato!r}",
                "formatos": list(CONVERSORES),
                "pista": "manda 'formato' junto con su campo: question / entrada / "
                         "state+questions"})

        try:
            r = CONVERSORES[formato](cuerpo, self.catalog, self.cfg)
            if cuerpo.get("comparar"):
                r = comparar(r, cuerpo, self.catalog, self.cfg, formato)
                return self._send(200, r)
        except ValueError as e:
            return self._send(400, {"error": str(e), "formato": formato})
        except urllib.error.HTTPError as e:
            return self._send(502, {"error": f"llama-server {e.code}",
                                    "detail": e.read()[:300].decode("utf-8", "replace")})
        except Exception as e:                                      # noqa: BLE001
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})

        r["formato"] = formato
        r.setdefault("n_preguntas", len(r.get("resultados") or []))
        self._send(200, r)

    def log_message(self, *a):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(prog="api", description="API HTTP de AIOM")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--server", default=aiom.DEFAULTS["server"])
    ap.add_argument("--model", default=aiom.DEFAULTS["model"])
    ap.add_argument("--catalog", default=aiom.DEFAULTS["catalog"])
    ap.add_argument("--timeout", type=int, default=aiom.DEFAULTS["timeout"])
    ap.add_argument("--ui", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "web", "index.html"))
    a = ap.parse_args()

    try:
        with open(a.catalog, encoding="utf-8") as f:
            catalogo = json.load(f)
    except OSError as e:
        print(f"no puedo leer el catalogo {a.catalog}: {e}", file=sys.stderr)
        return 2

    Handler.catalog = catalogo
    Handler.cfg = {"server": a.server, "model": a.model, "timeout": a.timeout,
                   "ui": a.ui}

    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"AIOM escuchando en http://127.0.0.1:{a.port}")
    print(f"  interfaz:    http://127.0.0.1:{a.port}/")
    print(f"  POST /ask    formato: {' | '.join(CONVERSORES)}   (+ \"comparar\": true)")
    print(f"  GET  /docs   la documentacion   GET /health   GET /catalog")
    print(f"  catalogo: {a.catalog}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nparado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
