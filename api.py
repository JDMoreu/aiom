"""API HTTP de AIOM, con FastAPI: un endpoint, tres formatos de entrada.

El .txt sigue siendo la puerta HUMANA (escribir una pregunta sin saber JSON), y esto
es la puerta de PROGRAMA: otro sistema manda la pregunta por HTTP y recibe JSON.

Se elige el formato con el campo `formato`, y no se adivina:

    POST /ask   {"formato": "natural", "entrada": "..."}          el contenido de un .txt
    POST /ask   {"formato": "tipado",  "state": ..., "questions": ...}
    POST /ask   {"formato": "chat",    "question": "..."}         una pregunta suelta

`natural` y `tipado` son las vias de DECISION: traen su propio esquema y devuelven
valores, sin generar un token. `chat` es la via de prosa: una pregunta libre y el modelo
escribe la respuesta.

    python api.py                    # escucha en 8100
    python api.py --port 9000

    curl -s localhost:8100/docs      # Swagger: la documentacion y las pruebas de la API

Dos cosas que se conservan de la version de la biblioteca estandar, porque son parte del
comportamiento y no del framework:

  - El JSON sale INDENTADO y sin escapar los acentos, igual que antes. Los ejemplos de
    la documentacion son literales y no habria que reescribirlos.
  - Las rutas y los codigos no cambian: `/docs` es Swagger, con la guia de los tres
    formatos y un boton para probar cada uno desde el navegador.
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
    del campo las lleva, y es la misma fuente que usa el analizador del formato natural.
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
def _red(x):
    """Redondea un numero para publicarlo.

    El motor devuelve las probabilidades con toda la precision del float, y asi salen
    cosas como 0.9999997615814209. Cuatro decimales es mas de lo que nadie necesita, y
    un documento con diecisiete digitos no dice nada a quien lo lee.
    """
    return round(x, 4) if isinstance(x, (int, float)) else x


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
        probs = f.get("probabilities")
        r = {
            "campo": nombre,
            "tipo": aiom.AL_PROYECTO.get(spec.get("type"), spec.get("type")),
            "pregunta": spec.get("pregunta") or spec.get("description", "")[:80],
            "value": f.get("value"),
            "probability": _red(f.get("probability")),
            "probabilities": ({k: _red(v) for k, v in probs.items()} if probs else probs),
            "confidence": _red(f.get("confidence")),
        }
        # En un score, las etiquetas de los niveles: sin ellas el numero no significa
        # nada para quien lee.
        niveles = _niveles(spec.get("description"))
        if niveles:
            r["niveles"] = niveles
        salida.append(r)
    return salida


def _con_las_reglas(estado, preguntas):
    """El caso y las preguntas CON sus reglas, en lenguaje llano.

    Al chat se le dan las MISMAS reglas que a la via de decision -las opciones de cada
    pregunta y los niveles de cada escala-, pero escritas en prosa y SIN las cabeceras
    `ask:`/`choice:`. La diferencia importa, y esta medida:

      - con las cabeceras delante, el modelo contesta en el formato de la decision
        (un `true` a secas, 2 tokens), y eso no es prosa;
      - sin las reglas, contesta en prosa pero se inventa los nombres (506 tokens, y
        llamaba al area "Seccion de Soporte Tecnico / Atencion al Cliente");
      - con las reglas en prosa, contesta en prosa Y con los nombres de las opciones
        (63 tokens).

    Asi las dos vias reciben la misma informacion, que es lo que hace que la comparacion
    diga algo: la diferencia es la FORMA de la respuesta, no lo que se le conto.
    """
    lineas = [f"{i}. {c['description']}" for i, (_, c) in enumerate(preguntas, 1)]
    return f"{estado}\n\nResponde a estas preguntas:\n" + "\n".join(lineas)


def por_chat(cuerpo, cfg):
    """Una pregunta suelta, en prosa. Sin esquema y sin valores: el modelo escribe.

    Es el camino para lo que NO es una decision: redactar, explicar, resumir. Aqui no hay
    campos ni probabilidades, hay texto.

    Acepta las DOS formas de darle el caso, las mismas que la via de decision:

      - `question`: una frase suelta. Lo mas corto.
      - `entrada`: el mismo texto que el formato natural, con sus cabeceras (`input:`,
        `ask:`, `choice:`...). Asi se le puede pasar EL MISMO caso que a la decision, con
        las mismas reglas, y comparar las dos respuestas sin reescribir nada.
    """
    doc = _documento(cuerpo)
    texto = cuerpo.get("entrada")
    if isinstance(texto, str) and texto.strip():
        estado, preguntas = preguntar.parsear(texto, entrada=doc)
        pregunta = _con_las_reglas(estado, preguntas)
    else:
        q = cuerpo.get("question")
        if not isinstance(q, str) or not q.strip():
            raise ValueError("falta 'question' o 'entrada'")
        # Con documento, el caso es el documento y la pregunta va detras.
        pregunta = f"{doc}\n\n{q.strip()}" if doc else q
    r = aiom.chat(pregunta, cfg)
    return {"resultados": [{"via": "chat", "texto": r["text"]}],
            "tiempo_ms": r["timings"]["wall_ms"],
            "tokens": r["usage"].get("tokens_generated") or 0}


def por_natural(cuerpo, cfg):
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


def por_tipado(cuerpo, cfg):
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


CONVERSORES = {"natural": por_natural, "tipado": por_tipado, "chat": por_chat}


# --------------------------------------------------------------------------- #
# la comparativa: la misma pregunta por las dos vias, en una sola peticion
# --------------------------------------------------------------------------- #
def _chat(texto, cfg):
    """Una pregunta por la via de chat (prosa)."""
    r = aiom.chat(texto, cfg)
    return {"via": "chat", "texto": r["text"],
            "tiempo_ms": r["timings"]["wall_ms"],
            "tokens": r["usage"].get("tokens_generated") or 0}


def prompts_chat(cuerpo, cfg):
    """El chat recibe la pregunta tal cual, con el documento delante si lo hay."""
    doc = _documento(cuerpo)
    q = cuerpo["question"].strip()
    return [f"{doc}\n\n{q}" if doc else q]


def prompts_natural(cuerpo, cfg):
    """El chat recibe el caso y TODAS las preguntas, de una vez y en lenguaje llano.

    Una sola peticion, que es como se le pregunta a un asistente, y con la misma entrada
    que resuelve la decision, para que la comparacion sea en igualdad.

    Se le dan las MISMAS REGLAS que a la decision -las opciones y los niveles-, pero
    escritas en prosa y sin las cabeceras `ask:`/`choice:`. Se probo de las tres maneras y
    esta es la que funciona: con las cabeceras contesta en el formato de la decision (un
    `true` a secas), y sin las reglas se inventa los nombres de las opciones.
    """
    estado, preguntas = preguntar.parsear(cuerpo["entrada"], entrada=_documento(cuerpo))
    return [_con_las_reglas(estado, preguntas)]


def prompts_tipado(cuerpo, cfg):
    """Lo mismo en el formato tipado: aqui no hay .txt, asi que el texto se arma.

    El caso y las preguntas con sus reglas, en UNA peticion. Las reglas salen del esquema
    que ya trae el JSON, y se escriben en prosa: al chat no se le manda JSON.
    """
    doc = _documento(cuerpo)
    entrada = doc or cuerpo["state"].get("input", "")
    _, esquema = tipado.traducir(cuerpo)
    lineas = []
    for i, (nombre, preg) in enumerate(cuerpo["questions"].items(), 1):
        reglas = esquema.get(nombre, {}).get("description", "")
        lineas.append(f"{i}. {reglas or preg.get('instructions', '')}")
    return [f"{entrada}\n\nResponde a estas preguntas:\n" + "\n".join(lineas)]


# Solo los dos formatos de DECISION tienen con que compararse: en `chat` las dos vias
# serian la misma cosa, asi que ahi `comparar` no se ofrece.
PROMPTS = {"natural": prompts_natural, "tipado": prompts_tipado}


def comparar(r_decision, cuerpo, cfg, formato):
    """Envuelve el resultado de decision y le anade la via de chat, lado a lado.

    Se hace aqui y no en el cliente para que los dos tiempos sean de la MISMA corrida:
    medir en dos llamadas separadas daria tiempos de momentos distintos.

    Las dos vias reciben la misma entrada, y cada una UNA peticion: la decision resuelve
    todos los campos de golpe y el chat contesta todo en una sola respuesta. Es lo que
    hace que la comparacion sea en igualdad de condiciones.
    """
    respuestas = [_chat(p, cfg) for p in PROMPTS[formato](cuerpo, cfg)]
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

- **`natural`** — el contenido de un `.txt`: una o varias preguntas separadas por `---`.
  Es la via de **decision**: trae su esquema en el texto y devuelve valores, sin generar
  un token.
- **`tipado`** — el formato de TypeSafe/Jev, tal cual. La otra via de decision: el mismo
  caso, pero con el esquema en JSON.
- **`chat`** — una pregunta suelta, en prosa. Aqui no hay campos ni probabilidades: el
  modelo escribe. Es el camino para lo que no es una decision (redactar, explicar). Acepta
  `question` (una frase) o `entrada`, el **mismo texto** que el formato natural, para poder
  pasarle el mismo caso y comparar.

`natural` y `tipado` aceptan ademas:

- **`documento`** — el texto sacado de un fichero con `POST /documento`. Ese texto pasa a
  ser el caso, y las preguntas van sobre el en vez de escribirlo.
- **`comparar: true`** — resuelve la misma pregunta por las dos vias y las devuelve
  juntas, para que los tiempos sean de la misma corrida. En `chat` no aplica: las dos
  vias serian la misma cosa.
"""

EJEMPLOS_ASK = {
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
    "chat": {
        "summary": "Una pregunta suelta, en prosa",
        "value": {"formato": "chat",
                  "question": "Explicame en dos frases que es una red de sensores IoT"},
    },
    "comparar": {
        "summary": "La misma pregunta por las dos vias, en una sola corrida",
        "value": {"formato": "natural", "comparar": True,
                  "entrada": "input: Se cayo la senal en el predio 11.\n\n"
                             "ask: ¿Es urgente?\n"
                             "noul:\n  false: No corre prisa\n  true: Si, hay una falla activa"},
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
        formato = ("natural" if "entrada" in cuerpo else
                   "tipado" if "questions" in cuerpo else
                   "chat" if "question" in cuerpo else None)
    if formato not in CONVERSORES:
        return fallo(400, error=f"formato no valido: {formato!r}",
                     formatos=list(CONVERSORES),
                     pista="manda 'formato' junto con su campo: entrada / state+questions "
                           "/ question")
    try:
        r = CONVERSORES[formato](cuerpo, CFG)
        # `comparar` solo tiene sentido en las vias de decision: en chat las dos vias
        # serian la misma cosa.
        if cuerpo.get("comparar") and formato in PROMPTS:
            return JsonBonito(comparar(r, cuerpo, CFG, formato))
    except ValueError as e:
        return fallo(400, error=str(e), formato=formato)
    except urllib.error.HTTPError as e:
        return fallo(502, error=f"llama-server {e.code}",
                     detail=e.read()[:300].decode("utf-8", "replace"))
    except urllib.error.URLError as e:
        # No hay nadie al otro lado. Es el fallo mas comun al empezar, asi que se dice
        # cual es y donde se le busca, en vez de un 500 sin explicacion.
        return fallo(502, error="no puedo hablar con llama-server",
                     detail=str(e.reason), servidor=CFG.get("server"),
                     pista="esta levantado el servidor del modelo?")
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
    # Y lo que se pudo leer y COMO se dice, porque no es lo mismo un texto que estaba en
    # el PDF que uno leido de una imagen: quien pregunte sobre el tiene que saber de
    # donde sale y que puede traer errores.
    partes = []
    if r.get("paginas_con_texto"):
        partes.append(f"{r['paginas_con_texto']} con texto propio")
    if r.get("paginas_con_ocr"):
        partes.append(f"{r['paginas_con_ocr']} leidas con OCR (eran escaneos, el texto "
                      f"puede traer errores)")
    if r.get("paginas_ilegibles"):
        partes.append(f"{r['paginas_ilegibles']} con texto ilegible (glifos de una "
                      f"fuente sin traducir)")
    if r.get("paginas_sin_texto"):
        partes.append(f"{r['paginas_sin_texto']} sin nada que leer")
    if partes:
        r["aviso"] = f"de {r['paginas']} paginas: " + "; ".join(partes) + "."
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
    ap.add_argument("--timeout", type=int, default=aiom.DEFAULTS["timeout"])
    ap.add_argument("--ui", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "web", "index.html"))
    a = ap.parse_args()

    CFG.update({"server": a.server, "model": a.model, "timeout": a.timeout,
                "ui": a.ui})

    print(f"AIOM escuchando en http://127.0.0.1:{a.port}")
    print(f"  interfaz:    http://127.0.0.1:{a.port}/")
    print(f"  POST /ask    formato: {' | '.join(CONVERSORES)}   (+ \"comparar\": true)")
    print(f"  POST /documento   sube un fichero y devuelve su texto")
    print(f"  GET  /docs   Swagger: la documentacion y las pruebas de la API")
    print(f"  GET  /health")
    # access_log=False: sin una linea por peticion, como en la version anterior.
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning",
                access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
