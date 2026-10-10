"""API HTTP de AIOM, con FastAPI: un endpoint, tres formatos de entrada.

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

    curl -s localhost:8100/docs      # la documentacion de esta API, en JSON

Dos cosas que se conservan de la version de la biblioteca estandar, porque son parte del
comportamiento y no del framework:

  - El JSON sale INDENTADO y sin escapar los acentos, igual que antes. Los ejemplos de
    la documentacion son literales y no habria que reescribirlos.
  - Las rutas y los codigos no cambian: `/docs` sigue siendo la documentacion DE ESTA
    API en JSON, no la autodocumentacion de FastAPI (que va desactivada, para no
    pisarla).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import uvicorn
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiom                    # noqa: E402
import documento as doc_mod    # noqa: E402  (saca el texto de pdf, docx, txt...)
import tipado                  # noqa: E402  (el traductor del formato tipado)
import preguntar               # noqa: E402

FORMATOS = ("texto", "natural", "tipado")

# "0 = espanol: español. 1 = ingles: ingles." -> ['espanol: español', 'ingles: ingles']
NIVEL = re.compile(r"\d+ = ([^.]+)\.")

# Tope de subida. Un PDF con imagenes se va facilmente a 10 o 20 MB, asi que el tope es
# generoso: solo esta para no llenar la memoria con un fichero que no era el que se
# queria. Lo que importa no es el peso, sino cuantos CARACTERES salen de el.
LIMITE_SUBIDA = 64 * 1024 * 1024

# La configuracion la rellena main() antes de arrancar.
CFG: dict = {}


def _niveles(descripcion):
    """Las etiquetas de los niveles de un score, sacadas de la descripcion del campo.

    El motor devuelve un `score` como un NUMERO (0, 1, 2...). Sin las etiquetas, un "0"
    a secas no dice nada: no hay forma de saber que ese 0 es "espanol". La descripcion
    del campo las lleva, y es la misma fuente que ya usa preguntar.py por consola.
    """
    return NIVEL.findall(descripcion or "")


def _documento(cuerpo):
    """El texto del documento, si lo hay. Es el caso, en vez de escribirlo.

    Se acepta el texto suelto o el objeto entero que devuelve POST /documento.
    """
    d = cuerpo.get("documento")
    if d is None:
        return None
    if isinstance(d, dict):
        d = d.get("texto")
    if not isinstance(d, str) or not d.strip():
        raise ValueError("'documento' viene vacio")
    return d.strip()


# --------------------------------------------------------------------------- #
# los tres formatos -> una lista uniforme de resultados
# --------------------------------------------------------------------------- #
def _de_campos(campos, preguntas):
    """Respuesta del servidor -> lista de resultados, uno por pregunta.

    `campos` es el bloque `fields` de /v1/decision; `preguntas` la lista [(nombre, spec)]
    con la pregunta en lenguaje natural, para poder devolverla.
    """
    salida = []
    for nombre, spec in preguntas:
        f = campos.get(nombre)
        if not f:
            continue
        r = {
            "campo": nombre,
            "tipo": aiom.AL_PROYECTO.get(spec.get("type"), spec.get("type")),
            "pregunta": spec.get("pregunta") or spec.get("description", "")[:80],
            "value": f.get("value"),
            "probability": f.get("probability"),
            "probabilities": f.get("probabilities"),
            "confidence": f.get("confidence"),
        }
        # En un score, las etiquetas de los niveles: sin ellas el numero no significa
        # nada para quien lee.
        niveles = _niveles(spec.get("description"))
        if niveles:
            r["niveles"] = niveles
        salida.append(r)
    return salida


def por_texto(cuerpo, catalogo, cfg):
    """Una pregunta suelta contra el catalogo (lo que hacia aiom.ask)."""
    q = cuerpo.get("question")
    if not isinstance(q, str) or not q.strip():
        raise ValueError("falta 'question'")
    doc = _documento(cuerpo)
    # Con documento, el caso es el documento y la pregunta va detras.
    pregunta = f"{doc}\n\n{q.strip()}" if doc else q
    r = aiom.ask(pregunta, catalogo, cfg, cuerpo.get("mode", "auto"))
    if r["mode"] == "chat":
        return {"resultados": [{"modo": "chat", "texto": r.get("text")}],
                "tiempo_ms": r["timings"]["wall_ms"],
                "tokens": r["usage"].get("tokens_generated") or 0}
    # El `tipo` y el nombre de cada campo salen del CATALOGO: la respuesta del servidor
    # trae value/probabilities/confidence, pero no de que tipo es el campo.
    esquema = catalogo.get("fields", {})
    preguntas = [(k, {"type": esquema.get(k, {}).get("type"),
                      "pregunta": esquema.get(k, {}).get("description", ""),
                      "description": esquema.get(k, {}).get("description", "")})
                 for k in (r.get("fields") or {})]
    # wall_ms, NO total_ms: el tiempo que se publica tiene que ser el mismo reloj en las
    # dos vias (ida y vuelta completa), o la comparacion favorece a una. total_ms es lo
    # que tarda el servidor por dentro y no cuenta la red.
    return {"resultados": _de_campos(r["fields"], preguntas),
            "tiempo_ms": r["timings"]["wall_ms"], "tokens": 0}


def por_natural(cuerpo, catalogo, cfg):
    """El contenido de un .txt: una o varias preguntas, en una sola peticion.

    Si viene 'documento', es el caso y el texto de arriba trae solo las preguntas.
    """
    texto = cuerpo.get("entrada")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("falta 'entrada'")
    estado, preguntas = preguntar.parsear(texto, entrada=_documento(cuerpo))
    t0 = time.perf_counter()
    res_crudo, _ = preguntar.ejecutar(estado, preguntas, timeout=cfg["timeout"])
    ms = (time.perf_counter() - t0) * 1000.0
    campos = res_crudo["results"][0]["fields"]
    return {"resultados": _de_campos(campos, preguntas), "tiempo_ms": round(ms, 1),
            "tokens": 0, "n_preguntas": len(preguntas)}


def por_tipado(cuerpo, catalogo, cfg):
    """El formato de TypeSafe: state.input + questions.<nombre> con criteria.

    `questions` admite varias: cada una es un campo del esquema y todas se resuelven en
    la misma peticion.
    """
    if "state" not in cuerpo or "questions" not in cuerpo:
        raise ValueError("faltan 'state' y 'questions'")
    doc = _documento(cuerpo)
    if doc:
        # El documento manda como estado, venga lo que venga en state.input.
        cuerpo = dict(cuerpo, state=dict(cuerpo["state"], input=doc))
    res_crudo, ms = tipado.ejecutar(cuerpo, timeout=cfg["timeout"],
                                    servidor=cfg["server"])
    campos = res_crudo["results"][0]["fields"]
    # El tipo y el enunciado salen de la PETICION; la descripcion del esquema hace falta
    # para las etiquetas de un score. traducir() es barato y no manda nada.
    _, esquema = tipado.traducir(cuerpo)
    preguntas = [(nombre, {"type": preg.get("type"),
                           "pregunta": preg.get("instructions", ""),
                           "description": esquema.get(nombre, {}).get("description", "")})
                 for nombre, preg in cuerpo["questions"].items()]
    return {"resultados": _de_campos(campos, preguntas),
            "tiempo_ms": round(ms, 1), "tokens": 0, "n_preguntas": len(preguntas)}


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
    doc = _documento(cuerpo)
    q = cuerpo["question"].strip()
    return [f"{doc}\n\n{q}" if doc else q]


def prompts_natural(cuerpo, catalogo, cfg):
    estado, preguntas = preguntar.parsear(cuerpo["entrada"], entrada=_documento(cuerpo))
    return [f"{estado}\n\nask: {c['pregunta']}" for _, c in preguntas]


def prompts_tipado(cuerpo, catalogo, cfg):
    doc = _documento(cuerpo)
    entrada = doc or cuerpo["state"].get("input", "")
    return [f"{entrada}\n\nask: {c.get('instructions', '')}"
            for c in cuerpo["questions"].values()]


PROMPTS = {"texto": prompts_texto, "natural": prompts_natural, "tipado": prompts_tipado}


def comparar(r_decision, cuerpo, catalogo, cfg, formato):
    """Envuelve el resultado de decision y le anade la via de chat, lado a lado.

    Se hace aqui y no en el cliente para que los dos tiempos sean de la MISMA corrida:
    medir en dos llamadas separadas daria tiempos de momentos distintos.
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
# el servidor
# --------------------------------------------------------------------------- #
class JsonBonito(JSONResponse):
    """JSON indentado y sin escapar acentos, como lo devolvia la version de la
    biblioteca estandar: los ejemplos de la documentacion siguen siendo literales."""

    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")


def fallo(code: int, **campos) -> JsonBonito:
    return JsonBonito(campos, status_code=code)


# La autodocumentacion de FastAPI va ENCENDIDA: `/docs` es Swagger, con la guia de los
# tres formatos y un boton para probar cada uno desde el navegador. La version anterior
# tenia ahi su propia lista de endpoints en JSON, que no usaba nadie: subir un documento,
# sacarle el texto y pasarlo como caso es otro camino, y ese esta en POST /documento.
app = FastAPI(
    title="AIOM",
    version="1.0",
    description=(
        "La puerta de programa: otro sistema manda la pregunta por HTTP y recibe JSON.\n\n"
        "**Un modelo, dos formas de preguntar.** La via de decision puntua las opciones y "
        "devuelve un valor sin generar un token; la de chat escribe prosa. El modo no es "
        "del sistema: es **una propiedad de la peticion**, y por eso se pueden pedir las "
        "dos a la vez y compararlas."
    ),
)

# La interfaz la sirve esta misma API, asi que no hace falta CORS. Pero si alguien abre
# el HTML desde el disco (file://) el navegador manda Origin: null, y sin esto la
# peticion se cae. Es una herramienta local, no un servicio publico.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST",
                                                                      "OPTIONS"],
                   allow_headers=["*"])

GUIA_FORMATOS = """
El campo `formato` dice cual es, y **no se adivina**: si falta o no es uno de los tres,
la API contesta con un error y la lista de los que acepta.

- **`texto`** — una pregunta suelta, contra los campos del catalogo (`--catalog`).
- **`natural`** — el contenido de un `.txt`: una o varias preguntas separadas por `---`.
- **`tipado`** — el formato de TypeSafe/Jev, tal cual.

Los tres aceptan ademas:

- **`documento`** — el texto sacado de un fichero con `POST /documento`. Ese texto pasa a
  ser el caso, y las preguntas van sobre el en vez de escribirlo.
- **`comparar: true`** — resuelve la misma pregunta por las dos vias y las devuelve
  juntas, para que los tiempos sean de la misma corrida.
"""

EJEMPLOS_ASK = {
    "texto": {
        "summary": "Una pregunta suelta, contra el catalogo",
        "value": {"formato": "texto",
                  "question": "El sensor del predio 3 lleva dos dias sin reportar",
                  "mode": "decision"},
    },
    "natural": {
        "summary": "El contenido de un .txt, entero",
        "value": {"formato": "natural",
                  "entrada": "input: Llevo desde ayer sin poder entrar: me sale un "
                             "error 500 cada vez que inicio sesion.\n\n"
                             "ask: ¿A que area hay que enviar este correo?\n"
                             "choice:\n"
                             "  soporte: Fallos y errores del producto\n"
                             "  facturacion: Cobros, facturas y reembolsos"},
    },
    "tipado": {
        "summary": "El formato de TypeSafe, tal cual",
        "value": {"formato": "tipado",
                  "state": {"input": "Me cobraron dos veces la suscripcion"},
                  "questions": {"area": {
                      "type": "choice",
                      "instructions": "¿Que area debe atenderlo?",
                      "criteria": {"billing": "Pagos y reembolsos",
                                   "technical": "Errores e integraciones"}}}},
    },
    "comparar": {
        "summary": "La misma pregunta por las dos vias, en una sola corrida",
        "value": {"formato": "natural", "comparar": True,
                  "entrada": "input: Se cayo la senal en el predio 11.\n\n"
                             "ask: ¿Es urgente?\n"
                             "noul:\n  si: Si, hay una falla activa\n  no: No corre prisa"},
    },
}


def _ejemplos_ask():
    return {"application/json": {"examples": EJEMPLOS_ASK}}


def _responder(cuerpo: dict) -> JsonBonito:
    """El trabajo de /ask: formato, conversion y, si toca, comparacion.

    Es sincrono a proposito: habla con llama-server con urllib, que es bloqueante, y
    FastAPI lo ejecuta en su pool de hilos para no parar el bucle de eventos.
    """
    # El formato se declara. Si no viene, se deduce solo del campo que traiga, y si
    # tampoco, se dice que falta en vez de adivinar.
    formato = cuerpo.get("formato")
    if formato is None:
        formato = ("texto" if "question" in cuerpo else
                   "natural" if "entrada" in cuerpo else
                   "tipado" if "questions" in cuerpo else None)
    if formato not in CONVERSORES:
        return fallo(400, error=f"formato no valido: {formato!r}",
                     formatos=list(CONVERSORES),
                     pista="manda 'formato' junto con su campo: question / entrada / "
                           "state+questions")
    try:
        r = CONVERSORES[formato](cuerpo, CFG["catalog"], CFG)
        if cuerpo.get("comparar"):
            return JsonBonito(comparar(r, cuerpo, CFG["catalog"], CFG, formato))
    except ValueError as e:
        return fallo(400, error=str(e), formato=formato)
    except urllib.error.HTTPError as e:
        return fallo(502, error=f"llama-server {e.code}",
                     detail=e.read()[:300].decode("utf-8", "replace"))
    except Exception as e:                                          # noqa: BLE001
        return fallo(500, error=f"{type(e).__name__}: {e}")

    r["formato"] = formato
    r.setdefault("n_preguntas", len(r.get("resultados") or []))
    return JsonBonito(r)


@app.post("/ask", summary="Pregunta al modelo local", description=GUIA_FORMATOS,
          openapi_extra={"requestBody": {"required": True, "content": _ejemplos_ask()}})
async def ask(request: Request):
    try:
        cuerpo = json.loads((await request.body()).decode("utf-8"))
    except Exception as e:                                          # noqa: BLE001
        return fallo(400, error=f"cuerpo invalido: {e}")
    if not isinstance(cuerpo, dict):
        return fallo(400, error="el cuerpo tiene que ser un objeto JSON")
    return await run_in_threadpool(_responder, cuerpo)


@app.post("/documento", summary="Sube un fichero y devuelve su texto",
          description="""El cuerpo va **en crudo** (los bytes del fichero) y el nombre en la
cabecera `X-Nombre` o en `?nombre=`. De la extension sale como se lee: no se adivina por
el contenido, porque un `.docx` y un `.zip` empiezan igual.

El texto que devuelve es el que se pasa luego como `documento` en `POST /ask`: eso es el
caso, y las preguntas van sobre el. **No se guarda nada**: se lee, se convierte a texto y
se devuelve.""",
          openapi_extra={"requestBody": {"required": True, "content": {
              "application/octet-stream": {
                  "schema": {"type": "string", "format": "binary"}}}}})
async def subir_documento(request: Request):
    """Sube un fichero y devuelve su texto, para poder usarlo como caso.

    El cuerpo va EN CRUDO (los bytes del fichero), y el nombre en la cabecera X-Nombre o
    en ?nombre=. De la extension sale como se lee: no se adivina por el contenido,
    porque un .docx y un .zip empiezan igual.

    Esto NO se guarda en ningun sitio: se lee, se convierte a texto y se devuelve.
    """
    nombre = (request.headers.get("x-nombre") or "").strip() \
        or (request.query_params.get("nombre") or "").strip()
    if not nombre:
        return fallo(400, error="falta el nombre del fichero: mandalo en la cabecera "
                                "X-Nombre, o en ?nombre=carta.pdf. De ahi sale como se lee")
    n = int(request.headers.get("content-length") or 0)
    if n <= 0:
        return fallo(400, error="el cuerpo va vacio: manda los bytes del fichero en crudo")
    # Se mira el tamano ANTES de leer: asi un fichero enorme no llega a la memoria.
    if n > LIMITE_SUBIDA:
        return fallo(413, error=f"el fichero pasa de {LIMITE_SUBIDA // (1024*1024)} MB",
                     bytes=n)
    datos = await request.body()

    def extraer():
        try:
            return doc_mod.extraer_bytes(datos, nombre)
        except ValueError as e:
            return fallo(400, error=str(e), soportados=sorted(doc_mod.SOPORTADOS))
        except Exception as e:                                      # noqa: BLE001
            # Un .docx corrupto o un PDF que no lo es lanzan cosas que no son
            # ValueError. Sin esto la excepcion sube y el navegador solo ve un fallo
            # de red en vez del motivo.
            return fallo(400, error=f"no pude leer '{nombre}': "
                                    f"{type(e).__name__}: {e}")

    r = await run_in_threadpool(extraer)
    if isinstance(r, JsonBonito):
        return r
    # El contexto del modelo son 32768 tokens. A ~4 caracteres por token, un documento de
    # mas de 100.000 caracteres puede no caber: se avisa, no se corta en silencio,
    # porque recortar cambiaria lo que el modelo ve.
    if r["caracteres"] > 100_000:
        r["aviso"] = (f"{r['caracteres']} caracteres puede no caber en el contexto "
                      f"del modelo (32768 tokens). Recorta el documento o sube "
                      f"el contexto al arrancar llama-server")
    # Y las paginas que no se pudieron leer se dicen, porque el texto que va arriba
    # parece el documento entero y no lo es: quien pregunte sobre el tiene que saber
    # que le falta trozo.
    mudas = r.get("paginas_ilegibles", 0) + r.get("paginas_sin_texto", 0)
    if mudas:
        causas = []
        if r.get("paginas_ilegibles"):
            causas.append(f"{r['paginas_ilegibles']} con texto ilegible (glifos de una "
                          f"fuente sin traducir)")
        if r.get("paginas_sin_texto"):
            causas.append(f"{r['paginas_sin_texto']} solo con imagenes (un escaneo, "
                          f"sin capa de texto)")
        n = r["paginas_con_texto"]
        r["aviso"] = (f"de {r['paginas']} paginas, {mudas} no se pudieron leer: "
                      + " y ".join(causas) + ". El texto de arriba es solo el de "
                      + ("la pagina legible." if n == 1
                         else f"las {n} paginas legibles."))
    return JsonBonito(r)


@app.get("/health", summary="Estado de la API y del llama-server")
def health():
    # /health de llama-server es GET. Con POST devolvia 404 y el estado salia como
    # 'unreachable' aunque el servidor estuviera perfectamente.
    try:
        url = CFG["server"].rstrip("/") + "/health"
        with urllib.request.urlopen(url, timeout=5) as r:
            cuerpo = json.loads(r.read().decode("utf-8"))
        return JsonBonito({"aiom": "ok", "llama_server": cuerpo})
    except Exception as e:                                          # noqa: BLE001
        return fallo(503, aiom="ok", llama_server=f"unreachable: {e}")


@app.get("/catalog", summary="El catalogo cargado")
def catalog():
    return JsonBonito(CFG["catalog"])


@app.get("/", summary="La interfaz web")
@app.get("/ui", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def interfaz():
    ruta = CFG["ui"]
    try:
        with open(ruta, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except OSError as e:
        return fallo(404, error=f"no puedo leer {ruta}: {e}")


@app.exception_handler(404)
async def no_encontrado(request: Request, exc):
    return fallo(404, error="usa POST /ask, o GET / para la interfaz")


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

    CFG.update({"server": a.server, "model": a.model, "timeout": a.timeout,
                "ui": a.ui, "catalog": catalogo})

    print(f"AIOM escuchando en http://127.0.0.1:{a.port}")
    print(f"  interfaz:    http://127.0.0.1:{a.port}/")
    print(f"  POST /ask    formato: {' | '.join(CONVERSORES)}   (+ \"comparar\": true)")
    print(f"  GET  /docs   Swagger: la documentacion y las pruebas de la API")
    print(f"  GET  /health   GET /catalog")
    print(f"  catalogo: {a.catalog}")
    # access_log=False: sin una linea por peticion, como en la version anterior.
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning",
                access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
