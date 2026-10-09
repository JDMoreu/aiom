#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metrics.py — la estadistica del proyecto en un solo sitio.

Todo lo que se reporta en la documentacion sale de aqui, para que dos informes no
usen definiciones distintas de la misma metrica.

Definiciones:

  exactitud            aciertos / casos
  exactitud balanceada media de los recalls por clase. En un dataset desbalanceado
                       la exactitud premia acertar la clase mayoritaria; la
                       balanceada no. SemIf y las comparaciones de NLI usan esta.
  IC de Wilson         intervalo para una proporcion. Se prefiere al normal porque
                       con n pequeno (que es nuestro caso) el normal se sale de [0,1].
  ECE                  Expected Calibration Error: media ponderada de
                       |acierto - confianza| por tramos. 0 es perfecto.
                       Solo informa si la tarea tiene errores que repartir.
  Brier                error cuadratico medio de la probabilidad.
  tabla fiabilidad     por tramo de confianza, cuanto se acierta de verdad.
  confianza            1 - H(p)/ln(n): la entropia normalizada del reparto de
                       probabilidades. NO es "el mayor menos los otros" (eso seria el
                       margen, 2*p_max-1, que mide otra cosa). 1 = un solo pico,
                       0 = reparto plano entre todas las opciones.
"""
from __future__ import annotations

import math
import statistics


def confianza(probabilidades):
    """Entropia normalizada de un reparto de probabilidades.

    Es la formula que aplica el servidor (decision-engine.cpp), y aqui esta para poder
    comprobarla: sobre los 180 casos de results/modos.json la reproduce con una
    discrepancia maxima de 0.000000.

    1 - H(p)/ln(n)   con   H(p) = -sum p*ln(p)

    Ejemplos: todo en una opcion -> 1.0 · empate a dos -> 0.5 · empate a cuatro -> 0.0
    """
    p = [float(v) for v in probabilidades if float(v) > 0]
    if not p:
        return 0.0
    if len(p) == 1:
        return 1.0
    h = -sum(v * math.log(v) for v in p)
    return 1.0 - h / math.log(len(probabilidades))


def wilson(k: int, n: int, z: float = 1.96):
    """IC de Wilson al 95% para una proporcion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def exactitud(pares):
    """pares = [(pred, gold)] -> (exactitud, aciertos, total)"""
    n = len(pares)
    if n == 0:
        return (0.0, 0, 0)
    ok = sum(1 for p, g in pares if p == g)
    return (ok / n, ok, n)


def balanceada(pares):
    """Media de recalls por clase. Devuelve (valor, {clase: (recall, n)})."""
    clases = {}
    for p, g in pares:
        clases.setdefault(g, []).append(p == g)
    if not clases:
        return (0.0, {})
    det = {c: (sum(v) / len(v), len(v)) for c, v in clases.items()}
    return (statistics.mean(r for r, _ in det.values()), det)


def ece(pares_conf, bins: int = 10):
    """pares_conf = [(confianza, acierto_bool)] -> (ECE, filas, n)

    filas: [(lo, hi, n, confianza_media, acierto_real, desvio)]
    """
    total = 0
    e = 0.0
    filas = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        sel = [(c, ok) for c, ok in pares_conf
               if c is not None and (lo <= c < hi or (i == bins - 1 and c >= hi))]
        if not sel:
            filas.append((lo, hi, 0, None, None, None))
            continue
        conf = statistics.mean(c for c, _ in sel)
        acc = sum(1 for _, ok in sel if ok) / len(sel)
        filas.append((lo, hi, len(sel), conf, acc, acc - conf))
        e += len(sel) * abs(acc - conf)
        total += len(sel)
    return ((e / total if total else 0.0), filas, total)


def brier(pares_conf):
    v = [(c - (1.0 if ok else 0.0)) ** 2 for c, ok in pares_conf if c is not None]
    return statistics.mean(v) if v else None


def resumen(pares, pares_conf=None, etiquetas=None, nombre="", bins=10):
    """Paquete completo de metricas para un experimento."""
    ex, ok, n = exactitud(pares)
    lo, hi = wilson(ok, n)
    bal, det = balanceada(pares)
    out = {
        "nombre": nombre, "n": n, "aciertos": ok,
        "exactitud": ex, "exactitud_ic95": (lo, hi),
        "exactitud_balanceada": bal, "recalls": det,
    }
    if pares_conf:
        e, filas, m = ece(pares_conf, bins)
        out.update({"ece": e, "brier": brier(pares_conf),
                    "fiabilidad": filas, "n_calib": m,
                    "conf_media": statistics.mean(c for c, _ in pares_conf if c is not None),
                    # direccion del error: positivo = se queda corto (prudente)
                    "sesgo": statistics.mean((1.0 if ok else 0.0) - c
                                             for c, ok in pares_conf if c is not None)})
    return out


def fmt_ic(ic):
    return f"[{100*ic[0]:.1f}%, {100*ic[1]:.1f}%]"


def veredicto_calibracion(e):
    if e is None:
        return "n/d"
    if e < 0.05:
        return "bien calibrado"
    if e < 0.10:
        return "calibracion aceptable"
    return "mal calibrado"
