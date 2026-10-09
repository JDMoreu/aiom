#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp_batch.py — por que se estanca el caudal en ~13 q/s, y como romper ese techo.

El endpoint /v1/decision acepta MUCHOS contextos en UNA peticion y los puntua en
el mismo lote hacia delante. Mandar 26 peticiones HTTP no aprovecha eso.

Compara, sobre las MISMAS 26 consultas etiquetadas (53 campos evaluables):
  A) N peticiones HTTP, 1 consulta cada una, concurrencia C
  B) peticiones con N consultas cada una, en serie

Ojo con el acierto: hay que emparejar cada respuesta con SU consulta. Emparejar
por indice global es el error facil y fabrica aciertos falsos.
"""
import json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

import dataset

BASE = "http://127.0.0.1:8096"
CAT = json.load(open("catalogs/iot.json", encoding="utf-8"))
CASES = dataset.cases()
QS = [c["q"] for c in CASES]


def decision(contextos, timeout=300):
    p = {"instructions": CAT["instructions"], "schema": CAT["fields"],
         "contexts": contextos}
    req = urllib.request.Request(BASE + "/v1/decision", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode())
    return body, (time.perf_counter() - t0) * 1000


def puntuar(pares):
    """pares = [(body, [casos alineados con body['results']])]"""
    ok = ev = 0
    for body, casos in pares:
        for r, c in zip(body["results"], casos):
            a, b = dataset.score(r["decision"], c)
            ok += a
            ev += b
    return ok, ev


def main():
    decision([QS[0]])          # calentar prefijo

    print("26 consultas etiquetadas | A) 1 consulta por peticion, en paralelo")
    print(f"{'concurrencia':>13} {'pared_ms':>9} {'ms/consulta':>12} {'acierto':>10}")
    for c in (4, 8, 16):
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=c) as ex:
            outs = list(ex.map(lambda i: (decision([QS[i]])[0], [CASES[i]]),
                               range(len(QS))))
        pared = (time.perf_counter() - t0) * 1000
        ok, ev = puntuar(outs)
        print(f"{c:>13} {pared:>9.0f} {pared/26:>12.1f} {ok:>6}/{ev}")

    print("\nB) N consultas por peticion, en serie")
    print(f"{'lote':>13} {'pared_ms':>9} {'ms/consulta':>12} {'acierto':>10}")
    for tam in (1, 2, 4, 8, 13, 16, 26):
        tandas = [(QS[i:i + tam], CASES[i:i + tam]) for i in range(0, len(QS), tam)]
        t0 = time.perf_counter()
        outs = [(decision(qs)[0], cs) for qs, cs in tandas]
        pared = (time.perf_counter() - t0) * 1000
        ok, ev = puntuar(outs)
        print(f"{tam:>13} {pared:>9.0f} {pared/26:>12.1f} {ok:>6}/{ev}")


# El experimento NO se lanza al importar el modulo: antes corria aqui mismo, asi que
# un simple `import exp_batch` (por ejemplo desde una comprobacion de imports) abria
# conexiones al servidor. Ahora hace falta llamarlo a proposito.
if __name__ == "__main__":
    main()
