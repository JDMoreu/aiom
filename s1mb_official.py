#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s1mb_official.py — puntuacion OFICIAL de S1MB sobre nuestras predicciones.

Implementa evaluator/SCORING.md al pie de la letra, para que las cifras sean
comparables con el leaderboard en vez de con una aproximacion propia.

Reglas, tal como las define el benchmark:

  NOUL   metrica primaria Brier = media de (p(true) - target(true))^2.
         Se predice true cuando p(true) >= 0.5 (umbral fijo, no ajustado).
         Con targets blandos: TP += t, FP += 1-t sobre los predichos true, y
         simetrico en los false. Balanced Accuracy = (TrueRecall + FalseRecall)/2.
         adjusted skill = 2*BA - 1.  Elegibilidad: ambas clases con masa positiva.

  CHOICE metrica primaria = acierto (etiquetas duras). El baseline b es la MEJOR
         exactitud esperada entre: azar uniforme (segun numero de candidatos),
         elegir siempre un id concreto, y elegir siempre una posicion concreta.
         Si el id o la posicion no existe en la pregunta, cae a azar uniforme.
         adjusted skill = (acc - b) / (1 - b).  Elegibilidad: b < 1.

  SCORE  se normaliza cada valor por (v - min)/(max - min) dentro de su pregunta,
         y se compara el valor esperado predicho con el objetivo.
         MAE = media |EV_pred - EV_obj|.  Baseline = constante que predice la
         MEDIANA de los EV objetivo; su MAE es la referencia.
         adjusted skill = 1 - MAE / baselineMAE.  Elegibilidad: baselineMAE > 0.

Agregacion: media de decisiones por benchmark -> recorte del skill a [0,1] POR
BENCHMARK -> media por tarea -> indice global con las tres tareas a peso igual,
en escala 0-100 (0 = en o por debajo del baseline trivial, 100 = techo).

Uso:  python s1mb_official.py results/s1mb_crudo.json
"""
from __future__ import annotations

import json
import statistics
import sys

TOL = 1e-12


# --------------------------------------------------------------------------- #
def p_true_de(caso):
    """Probabilidad de `true` que declaro el modelo en una decision noul."""
    v, c = caso.get("pred"), caso.get("conf")
    if v is None or c is None:
        return None
    if v == "true":
        return c
    if v == "false":
        return 1.0 - c
    return None


def target_true(caso, cands):
    """Probabilidad objetivo de `true` (targets blandos permitidos)."""
    probs = caso.get("probs")
    if not probs or not cands or len(probs) != len(cands):
        return None
    try:
        i = [str(x) for x in cands].index("true")
    except ValueError:
        return None
    return probs[i]


def metrica_noul(casos):
    """(Brier, BA, adjusted skill, n) segun SCORING.md."""
    TP = FP = FN = TN = 0.0
    briers, usados = [], 0
    masa_t = masa_f = 0.0
    for c in casos:
        cands = c.get("cands") or []
        t = target_true(c, cands)
        pt = p_true_de(c)
        if t is None or pt is None:
            continue
        usados += 1
        briers.append((pt - t) ** 2)
        masa_t += t
        masa_f += 1 - t
        if pt >= 0.5:                       # umbral fijo del benchmark
            TP += t
            FP += 1 - t
        else:
            FN += t
            TN += 1 - t
    if not usados or masa_t <= TOL or masa_f <= TOL:
        return None                      # no elegible: falta una clase
    tr = TP / (TP + FN) if (TP + FN) > TOL else None
    fr = TN / (TN + FP) if (TN + FP) > TOL else None
    if tr is None or fr is None:
        return None
    ba = (tr + fr) / 2
    return {"brier": statistics.mean(briers), "ba": ba, "skill": 2 * ba - 1,
            "n": usados, "tipo": "noul"}


def metrica_choice(casos):
    """(accuracy, baseline b, adjusted skill, n) segun SCORING.md."""
    pares = [(c["pred"], c["gold"], c.get("cands") or []) for c in casos
             if c.get("pred") is not None and c.get("gold") is not None]
    if not pares:
        return None
    n = len(pares)
    acc = sum(1 for p, g, _ in pares if p == g) / n

    # baseline 1: azar uniforme segun el numero de candidatos de cada pregunta
    uni = statistics.mean(1.0 / len(c) if c else 0.0 for _, _, c in pares)
    # baseline 2: elegir siempre un id concreto (si falta, cae a azar uniforme)
    b_id = 0.0
    for cand in {x for _, _, cs in pares for x in cs}:
        a = statistics.mean(1.0 if (cand in cs and g == cand) else
                            (0.0 if cand in cs else (1.0 / len(cs) if cs else 0.0))
                            for _, g, cs in pares)
        b_id = max(b_id, a)
    # baseline 3: elegir siempre una posicion concreta del orden original
    maxlen = max((len(cs) for _, _, cs in pares), default=0)
    b_pos = 0.0
    for i in range(maxlen):
        a = statistics.mean(1.0 if (len(cs) > i and g == cs[i]) else
                            (0.0 if len(cs) > i else (1.0 / len(cs) if cs else 0.0))
                            for _, g, cs in pares)
        b_pos = max(b_pos, a)
    b = max(uni, b_id, b_pos)
    if b >= 1 - TOL:
        return None                      # sin margen: excluido
    return {"acc": acc, "baseline": b, "skill": (acc - b) / (1 - b),
            "n": n, "tipo": "choice",
            "baseline_uniforme": uni, "baseline_id": b_id, "baseline_pos": b_pos}


def _norm_valores(cands, vals):
    """(v - min)/(max - min) dentro de la propia pregunta."""
    if not vals or len(vals) != len(cands):
        return None
    nums = []
    for v in vals:
        if v is None or not isinstance(v, (int, float)):
            return None
        nums.append(float(v))
    lo, hi = min(nums), max(nums)
    if hi - lo <= TOL:
        return None
    return {str(c): (float(v) - lo) / (hi - lo) for c, v in zip(cands, vals)}


def metrica_score(casos):
    """(MAE, baseline MAE, adjusted skill, n) segun SCORING.md."""
    ev_pred, ev_obj = [], []
    for c in casos:
        cands, vals = c.get("cands") or [], c.get("vals") or []
        probs = c.get("probs")
        mapa = _norm_valores(cands, vals)
        if mapa is None or not probs or len(probs) != len(cands):
            continue
        # objetivo: valor esperado con las probabilidades anotadas
        t_ev = sum(p * mapa[str(cd)] for cd, p in zip(cands, probs))
        # prediccion: etiqueta dura del modelo (una opcion, probabilidad 1)
        if c.get("pred") is None or str(c["pred"]) not in mapa:
            continue
        p_ev = mapa[str(c["pred"])]
        ev_pred.append(p_ev)
        ev_obj.append(t_ev)
    if not ev_pred:
        return None
    mae = statistics.mean(abs(a - b) for a, b in zip(ev_pred, ev_obj))
    mediana = statistics.median(ev_obj)
    base_mae = statistics.mean(abs(b - mediana) for b in ev_obj)
    if base_mae <= TOL:
        return None                      # sin margen: excluido
    return {"mae": mae, "baseline_mae": base_mae, "baseline_mediana": mediana,
            "skill": 1 - mae / base_mae, "n": len(ev_pred), "tipo": "score"}


CALC = {"noul": metrica_noul, "choice": metrica_choice, "score": metrica_score}


# --------------------------------------------------------------------------- #
def main(ruta="results/s1mb_crudo.json"):
    suites = json.load(open(ruta, encoding="utf-8"))
    por_tarea = {"noul": [], "choice": [], "score": []}
    detalle = []

    # La unidad "benchmark" oficial es (subset, TIPO), como revela el registro
    # evaluator/data/benchmarks/<subset>-<tipo>-test-v1.json. Prueba: el benchmark
    # `civil-comments-noul` declara case_count 100 y decision_count 700, o sea que
    # sus 7 decisiones se agregan en UNO. Y `argument-quality` tiene dos archivos
    # (choice y noul) porque aporta ambos tipos.
    for s in suites:
        casos = s.get("detalle") or []
        if not casos:
            continue
        grupos = {}
        for c in casos:
            k = c.get("kind")
            if k:
                grupos.setdefault(k, []).append(c)
        for tipo, cs in grupos.items():
            if tipo not in CALC:
                continue
            nombre = f"{s['suite']}::{tipo}" if len(grupos) > 1 else s["suite"]
            m = CALC[tipo](cs)
            if m is None:
                detalle.append({"suite": nombre, "tipo": tipo, "elegible": False})
                continue
            m["suite"] = nombre
            m["subset"] = s["suite"]
            m["elegible"] = True
            por_tarea[tipo].append(m)
            detalle.append(m)

    print("=" * 96)
    print(f"{'suite':<44} {'tipo':>6} {'n':>6} {'metrica':>10} {'baseline':>9} {'skill':>8} {'rec.':>6}")
    print("=" * 96)
    orden = {"noul": 0, "choice": 1, "score": 2}
    for m in sorted(detalle, key=lambda x: (orden.get(x["tipo"], 9), x["suite"])):
        if not m["elegible"]:
            print(f"{m['suite']:<44} {m['tipo']:>6} {'':>6} {'':>10} {'':>9} {'':>8}  NO ELEGIBLE")
            continue
        if m["tipo"] == "noul":
            prim, base = f"Brier {m['brier']:.4f}", f"BA {m['ba']:.3f}"
        elif m["tipo"] == "choice":
            prim, base = f"acc {m['acc']:.3f}", f"b {m['baseline']:.3f}"
        else:
            prim, base = f"MAE {m['mae']:.4f}", f"bMAE {m['baseline_mae']:.4f}"
        rec = max(0.0, min(1.0, m["skill"]))
        print(f"{m['suite']:<44} {m['tipo']:>6} {m['n']:>6} {prim:>10} {base:>9} "
              f"{m['skill']:>8.3f} {rec:>6.3f}")

    print("\n" + "=" * 96)
    print("AGREGACION (SCORING.md: recorte a [0,1] por benchmark, media por tarea)")
    print("=" * 96)
    tareas = {}
    for t, ms in por_tarea.items():
        if not ms:
            tareas[t] = None
            continue
        recortados = [max(0.0, min(1.0, m["skill"])) for m in ms]
        tareas[t] = statistics.mean(recortados)
        print(f"  {t:<8} benchmarks elegibles: {len(ms):>3}   "
              f"score de tarea: {tareas[t]:.4f}  ({100*tareas[t]:.1f}/100)")
    validas = [v for v in tareas.values() if v is not None]
    if len(validas) == 3:
        idx = statistics.mean(validas)
        print(f"\n  INDICE GLOBAL (Task Avg)  =  {100*idx:.2f} / 100")
        print(f"  cobertura: {len(por_tarea['noul'])}/{sum(1 for d in detalle if d['tipo']=='noul')} "
              f"noul, {len(por_tarea['choice'])} choice, {len(por_tarea['score'])} score")
    else:
        print(f"\n  INDICE GLOBAL no calculable: faltan tareas "
              f"({[t for t,v in tareas.items() if v is None]})")
        print("  SCORING.md exige las 106 suites completas con resultado medido;")
        print("  las no elegibles no se pueden omitir para mejorar el indice.")
    print("=" * 96)

    with open("results/s1mb_oficial.json", "w", encoding="utf-8") as f:
        json.dump({"detalle": detalle, "tareas": tareas}, f,
                  ensure_ascii=False, indent=2)
    print("\nescrito results/s1mb_oficial.json")
    return tareas


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/s1mb_crudo.json")
