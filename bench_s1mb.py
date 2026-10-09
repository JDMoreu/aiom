#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_s1mb.py — corre el benchmark S1MB (System One Mosaic Benchmark) contra AIOM.

S1MB es el benchmark especifico de modelos System One: 106 benchmarks, ~100 casos
cada uno, en tres tipos de decision (noul, choice, score). Es el unico que mide
exactamente lo nuestro con la misma interfaz, asi que es el que permite comparar
con Jev, Laya y las reproducciones abiertas.

Estructura de cada fila:
  input.state_json        el estado (JSON)
  input.decisions[]       {id, kind, type, instructions_json, criteria[]}
  targets[]               {decision_id, ids[], probabilities[], annotation_kind}

Se construye un esquema para /v1/decision a partir de los criterios declarados y
se compara con el argmax de las probabilidades doradas.

Uso:
    python bench_s1mb.py --list
    python bench_s1mb.py --suites banking77,babi_nli,arc --n 100
    python bench_s1mb.py --todas --n 100
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from bench_public import hf_rows, decision_lote, wilson
from metrics import balanceada

DATASET = "hotchpotch/s1mb-dataset"


# --------------------------------------------------------------------------- #
def _j(s, por_defecto=""):
    """Los campos vienen como JSON serializado dentro de un string."""
    try:
        v = json.loads(s)
        return v if v is not None else por_defecto
    except Exception:
        return s if isinstance(s, str) else por_defecto


def _texto_estado(state_json):
    """Aplana el estado a texto legible; la estructura no ayuda al modelo.

    El estado puede ser dict, lista o cadena segun la suite. Asumir dict daba
    `'list' object has no attribute 'items'` y tumbaba suites enteras.
    """
    s = _j(state_json, {})
    if isinstance(s, str):
        return s
    if isinstance(s, list):
        return "\n".join(x if isinstance(x, str)
                         else json.dumps(x, ensure_ascii=False) for x in s)
    partes = []
    for k, v in s.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        partes.append(f"{k}: {v}")
    return "\n".join(partes)


def campo_de(dec):
    """Convierte una decision declarada en un campo de esquema para /v1/decision."""
    tipo = dec.get("type")
    instr = _j(dec.get("instructions_json"), dec.get("id", ""))
    crit = dec.get("criteria") or []
    if tipo == "noul":
        return {"type": "boolean", "description": str(instr)}
    ids = [c.get("id") for c in crit if c.get("id") is not None]
    if tipo == "choice" and ids:
        return {"type": "enum", "choices": [str(i) for i in ids],
                "description": str(instr)}
    if tipo == "score" and ids:
        # Rubrica: los criterios son los niveles. Se ofrecen como opciones.
        return {"type": "enum", "choices": [str(i) for i in ids],
                "description": str(instr)}
    return None


def contexto_de(row, dec):
    """El estado + los criterios + la instruccion, como contexto para el modelo.

    OJO: estas cabeceras (Estado / Opciones / Pregunta) NO son el formato de AIOM.
    Este texto va TAL CUAL como contexto de /v1/decision y reproduce la forma en que
    S1MB presenta sus casos. Cambiarlas aqui cambiaria el prompt y por tanto la
    puntuacion medida, que esta atada a esta redaccion. No son un descuido.
    """
    estado = _texto_estado(row["input"].get("state_json"))
    sysp = dec.get("system_prompt") or ""
    instr = _j(dec.get("instructions_json"), "")
    bloques = []
    if sysp:
        bloques.append(str(sysp))
    bloques.append(f"Estado:\n{estado}")
    desc = [f"- {c.get('id')}: {_j(c.get('description_json'), '')}"
            for c in (dec.get("criteria") or []) if c.get("id") is not None]
    if desc:
        bloques.append("Opciones:\n" + "\n".join(desc))
    if instr:
        bloques.append(f"Pregunta: {instr}")
    return "\n\n".join(bloques)


def objetivo(row, decision_id):
    """El target completo (ids, probabilidades, tipo de anotacion)."""
    for t in row.get("targets", []):
        if t.get("decision_id") == decision_id:
            return t
    return None


def oro(row, decision_id):
    """Etiqueta dorada: el id con mayor probabilidad."""
    t = objetivo(row, decision_id)
    if not t:
        return None
    ids = t.get("ids") or []
    probs = t.get("probabilities") or []
    if not ids:
        return None
    if probs and len(probs) == len(ids):
        return str(ids[max(range(len(probs)), key=lambda i: probs[i])])
    return str(ids[0])


# --------------------------------------------------------------------------- #
def _norm(v):
    """Normaliza el valor para comparar con la etiqueta dorada.

    Los `noul` devuelven un booleano de Python y la etiqueta dorada de S1MB es la
    cadena "true"/"false" en minuscula: str(True) es "True" y no casa. Este fallo
    daba 0% en toda una suite y parecia un fallo del modelo.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v) if v is not None else None


def correr_suite(suite, n=100, verbose=True):
    filas = hf_rows(DATASET, suite, "test", n)
    if verbose:
        print(f"  {suite}: {len(filas)} casos", flush=True)
    if not filas:
        return None

    # El esquema y el contexto son POR CASO (las decisiones y el estado cambian),
    # asi que se agrupa por forma de decision para reutilizar el esquema.
    resultados, fallos = [], 0
    lote, metas = [], []
    # Presupuesto en CARACTERES, no en numero de casos: contract_nli trae contextos
    # de ~17.000 chars y agrupar 8 de ellos da HTTP 500 (peticion demasiado grande).
    presupuesto = [0]

    def vaciar():
        nonlocal lote, metas, fallos
        if not lote:
            return
        esquema = metas[0]["esquema"]
        try:
            b, wall = decision_lote(lote, metas[0]["instrucciones"], esquema)
            res = b["results"]
            t = b.get("timings", {})
        except Exception as e:
            if len(lote) == 1:
                raise
            # Reintento individual: aisla el caso problematico en vez de perder el lote
            res, t = [], {}
            for k, ctx in enumerate(lote):
                try:
                    bb, _ = decision_lote([ctx], metas[k]["instrucciones"],
                                          metas[k]["esquema"])
                    res.append(bb["results"][0])
                    t = bb.get("timings", t)
                except Exception:
                    res.append({"decision": {}, "fields": {}})
        for j, r in enumerate(res):
            m = metas[j]
            got = r["decision"].get(m["campo"])
            resultados.append({
                "decision": m["campo"],
                "gold": _norm(m["gold"]), "pred": _norm(got),
                "conf": r["fields"].get(m["campo"], {}).get("probability"),
                "total_ms": t.get("total_ms"), "rondas": t.get("rounds"),
                "nodos": sum(f.get("scored_nodes", 0) for f in r["fields"].values()),
                "kind": m["kind"],
                # para la puntuacion oficial: opciones, valores y targets
                "cands": m["cands"], "vals": m["vals"],
                "probs": m["probs"], "anno": m["anno"],
            })
        lote, metas = [], []
        presupuesto[0] = 0

    for row in filas:
        for dec in row["input"].get("decisions", []):
            esquema_campo = campo_de(dec)
            if esquema_campo is None:
                fallos += 1
                continue
            g = oro(row, dec.get("id"))
            if g is None:
                fallos += 1
                continue
            campo = str(dec.get("id"))
            esquema = {campo: {k: v for k, v in esquema_campo.items()
                               if k != "description"}}
            esquema[campo]["description"] = esquema_campo["description"][:400] or campo
            # Enum: las opciones deben ser exactamente los ids de criterio.
            if esquema_campo.get("type") == "enum":
                esquema[campo]["choices"] = esquema_campo["choices"]
            tgt = objetivo(row, dec.get("id")) or {}
            ctx = contexto_de(row, dec)
            lote.append(ctx)
            presupuesto[0] += len(ctx)
            metas.append({"campo": campo, "gold": g, "esquema": esquema,
                          "instrucciones": str(dec.get("instructions_json") or
                                               "Responde la pregunta sobre el estado."),
                          "kind": dec.get("type"),
                          # metadatos para la puntuacion OFICIAL de S1MB
                          "cands": [str(c.get("id")) for c in (dec.get("criteria") or [])
                                    if c.get("id") is not None],
                          "vals": [c.get("value") for c in (dec.get("criteria") or [])],
                          "probs": tgt.get("probabilities"),
                          "anno": tgt.get("annotation_kind")})
            if len(lote) >= 8 or presupuesto[0] > 4000:
                vaciar()
    vaciar()

    n_eval = len(resultados)
    if not n_eval:
        return None
    ok = sum(1 for r in resultados if r["pred"] == r["gold"])
    lo, hi = wilson(ok, n_eval)
    bal, recalls = balanceada([(r["pred"], r["gold"]) for r in resultados])
    # Score normalizado de S1MB: para noul, exactitud balanceada 50% -> 0 y 100% -> 100.
    # Es lo que reporta el leaderboard como Task Avg, y NO es la exactitud cruda.
    def norm_noul(x):
        return max(0.0, min(100.0, (x - 0.5) / 0.5 * 100.0))
    lat = sorted(r["total_ms"] for r in resultados if r["total_ms"])
    return {
        "suite": suite, "n": n_eval, "ok": ok, "exactitud": ok / n_eval,
        "exactitud_balanceada": bal,
        "recalls": {k: list(v) for k, v in recalls.items()},
        "task_avg_noul": norm_noul(bal),
        "ic95": (lo, hi), "saltados": fallos,
        "ms_mediana": lat[len(lat) // 2] if lat else None,
        "nodos": statistics.mean(r["nodos"] for r in resultados),
        "conf_media": (statistics.mean(r["conf"] for r in resultados if r["conf"])
                       if any(r["conf"] for r in resultados) else None),
        "detalle": resultados,
    }


def imprimir_tabla(res):
    print("\n" + "=" * 100)
    print(f"{'suite':<36} {'tipo':>7} {'casos':>6} {'exactitud':>10} {'IC95%':>16} {'ms':>7} {'conf':>6}")
    print("=" * 100)
    for r in res:
        if not r:
            continue
        tipo = statistics.mode([d["kind"] for d in r["detalle"]])
        ic = f"[{100*r['ic95'][0]:.0f}%, {100*r['ic95'][1]:.0f}%]"
        print(f"{r['suite']:<36} {tipo:>7} {r['n']:>6} {100*r['exactitud']:>9.1f}% "
              f"{ic:>16} {(r['ms_mediana'] or 0):>6.0f} {(r['conf_media'] or 0):>6.3f}")
    validos = [r for r in res if r]
    if validos:
        tot = sum(r["n"] for r in validos)
        aciertos = sum(r["ok"] for r in validos)
        micro = aciertos / tot
        macro = statistics.mean(r["exactitud"] for r in validos)
        lo, hi = wilson(aciertos, tot)
        print("-" * 100)
        print(f"{'MICRO (todos los casos)':<36} {'':>7} {tot:>6} {100*micro:>9.1f}% "
              f"{'[' + f'{100*lo:.1f}%, {100*hi:.1f}%' + ']':>16}")
        print(f"{'MACRO (media por suite)':<36} {'':>7} {len(validos):>6} {100*macro:>9.1f}%")
    print("=" * 100)
    return validos


SUITES_DEFECTO = ["banking77", "arc", "babi_nli", "clinc", "go_emotions", "hans",
                  "hatecheck", "hwu64", "contract_nli", "defeasible_nli",
                  "logical_entailment", "temporal_nli", "hans", "winobias",
                  "crows_pairs", "ag_news"]


def _es_relanzamiento():
    """Detecta que este proceso es el relanzamiento duplicado del mismo comando.

    El entorno lanza el comando y aparece un proceso hijo con la MISMA linea de
    comandos, arrancado en el mismo segundo. Ocurre DESPUES de cualquier
    comprobacion de fichero, asi que un lock no lo evita: los dos pasan.

    Lo que si funciona: el hijo hereda el entorno del padre. Marcamos una variable
    al arrancar; si ya esta puesta, somos el relanzamiento y salimos. Dos
    instancias compitiendo por la cache KV es lo que devolvia los HTTP 500
    ("no free KV cache space") y dejaba las suites colgadas.
    """
    import os
    if os.environ.get("S1MB_EN_CURSO"):
        print("ABORTADO: soy el relanzamiento duplicado del mismo comando.")
        return True
    os.environ["S1MB_EN_CURSO"] = "1"
    return False


def _lock(ruta=".s1mb.lock", max_edad=3600):
    """Impide dos corridas simultaneas.

    Dos instancias compitiendo por la cache KV del mismo servidor es lo que dejaba
    suites colgadas y devolvia HTTP 500 intermitentes ("no free KV cache space"),
    que se confunden con un problema de tamano de peticion. No lo es.

    La creacion tiene que ser ATOMICA: `os.path.exists` + `open` es una condicion
    de carrera, y con dos procesos arrancando en el mismo segundo ambos pasaban la
    comprobacion y los dos seguian. `O_CREAT | O_EXCL` lo resuelve el sistema.
    """
    import os, time
    def tomar():
        fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return ruta
    try:
        return tomar()
    except FileExistsError:
        try:
            edad = time.time() - os.path.getmtime(ruta)
        except OSError:
            return tomar()
        if edad < max_edad:
            print(f"ABORTADO: ya hay una corrida en curso (lock de hace {edad:.0f}s).")
            print(f"Si quedó huérfana, borra {ruta} y reintenta.")
            return None
        os.remove(ruta)          # lock viejo: lo reclamamos
        return tomar()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--suites", default=None)
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.list:
        from bench_public import get_json
        s = get_json(f"https://datasets-server.huggingface.co/splits?dataset={DATASET.replace('/', '%2F')}")
        cfgs = sorted(x["config"] for x in s["splits"])
        print(f"{len(cfgs)} benchmarks S1MB:")
        for c in cfgs:
            print(" ", c)
        return

    if a.todas:
        from bench_public import get_json
        s = get_json(f"https://datasets-server.huggingface.co/splits?dataset={DATASET.replace('/', '%2F')}")
        suites = sorted(x["config"] for x in s["splits"])
    else:
        suites = a.suites.split(",") if a.suites else SUITES_DEFECTO

    if _es_relanzamiento():
        return
    cerrojo = _lock()
    if cerrojo is None:
        return

    res = []
    t0 = time.time()
    for s in suites:
        try:
            res.append(correr_suite(s, a.n, verbose=True))
        except Exception as e:
            print(f"  {s}: ERROR {type(e).__name__}: {e}")
            res.append(None)
    validos = imprimir_tabla(res)
    print(f"\ntiempo total: {time.time()-t0:.0f}s")
    if a.out and validos:
        with open(a.out, "w", encoding="utf-8") as f:
            # Se guarda `detalle` a proposito: la puntuacion OFICIAL de S1MB
            # necesita las predicciones caso por caso, no solo los agregados.
            json.dump(validos, f, ensure_ascii=False)
        print(f"escrito {a.out}")
    import os as _os
    if _os.path.exists(cerrojo):
        _os.remove(cerrojo)


if __name__ == "__main__":
    main()
