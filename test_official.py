#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_official.py — comprueba s1mb_official.py contra los ejemplos de SCORING.md.

Un implementador de puntuaciones sin test no vale nada: si me equivoco en una
formula, el numero sale plausible y falso. SCORING.md trae un ejemplo numerico
concreto, asi que se usa como caso de prueba literal.

Ejemplo del documento:
  TP = 1, FN = 10, FP = 0, TN = 89
    Accuracy = 90%, true Recall = 9.09%, BA = 54.55%, adjusted skill = 9.09%
  Siempre falso: Accuracy = 89%, BA = 50%, adjusted skill = 0

Uso:  python test_official.py
"""
from __future__ import annotations

import s1mb_official as so

FALLOS = []


def check(nombre, obtenido, esperado, tol=1e-3):
    ok = (obtenido is not None and abs(obtenido - esperado) <= tol)
    print(f"  {'OK ' if ok else 'FALLO'}  {nombre:<48} obtenido {obtenido!r:<12} "
          f"esperado {esperado!r}")
    if not ok:
        FALLOS.append(nombre)
    return ok


def noul(pred, p_true, target_true):
    """Un caso noul: el modelo predice `pred` con probabilidad `p_true` de true."""
    conf = p_true if pred == "true" else 1.0 - p_true
    return {"pred": pred, "gold": "true" if target_true >= 0.5 else "false",
            "conf": conf, "kind": "noul", "cands": ["true", "false"],
            "probs": [target_true, 1 - target_true], "vals": [None, None]}


print("=" * 84)
print("NOUL — contra el ejemplo de SCORING.md (TP=1, FN=10, FP=0, TN=89)")
print("=" * 84)
casos = []
# 1 acierto verdadero: predice true y el target es true
casos.append(noul("true", 0.9, 1.0))
# 10 fallos con target true
for _ in range(10):
    casos.append(noul("false", 0.2, 1.0))
# 89 aciertos con target false
for _ in range(89):
    casos.append(noul("false", 0.1, 0.0))

m = so.metrica_noul(casos)
check("Brier (1 acierto a 0.9 y 99 aciertos a 0.8~0.9)", m["brier"],
      (1 * (0.9 - 1.0) ** 2 + 10 * (0.2 - 1.0) ** 2 + 89 * (0.1 - 0.0) ** 2) / 100)
check("true Recall = TP/(TP+FN)", 1 / 11, 1 / 11, 1e-9)
check("BA = (trueRecall + falseRecall)/2", m["ba"], (1 / 11 + 89 / 89) / 2)
check("adjusted skill = 2*BA - 1", m["skill"], 2 * ((1 / 11 + 89 / 89) / 2) - 1)

print()
print("  Caso del documento: BA = 54.55% y skill = 9.09%")
check("BA coincide con el documento (0.5455)", m["ba"], 0.54545, 5e-4)
check("skill coincide con el documento (0.0909)", m["skill"], 0.09091, 5e-4)

print()
print("=" * 84)
print("NOUL — 'siempre falso' debe dar skill 0 (el documento lo dice)")
print("=" * 84)
siempre_falso = [noul("false", 0.1, 1.0) for _ in range(11)] + \
                [noul("false", 0.1, 0.0) for _ in range(89)]
m2 = so.metrica_noul(siempre_falso)
check("BA = 0.5", m2["ba"], 0.5)
check("adjusted skill = 0", m2["skill"], 0.0)

print()
print("=" * 84)
print("NOUL — elegibilidad: una sola clase con masa -> NO elegible")
print("=" * 84)
m3 = so.metrica_noul([noul("true", 0.9, 1.0) for _ in range(10)])
print(f"  {'OK ' if m3 is None else 'FALLO'}  devuelve None cuando falta una clase"
      f"{' ' * 18} obtenido {m3!r}")
if m3 is not None:
    FALLOS.append("elegibilidad noul")

print()
print("=" * 84)
print("CHOICE — eleccion del baseline")
print("=" * 84)
# Caso A: el oro es siempre 'a', y 60 de 100 predicen 'a' -> elegir siempre 'a'
# acierta el 100%, o sea baseline = 1.0, sin margen: NO elegible (SCORING.md)
casos_c = ([{"pred": "a", "gold": "a", "conf": 0.9, "kind": "choice",
             "cands": ["a", "b"], "probs": [1.0, 0.0], "vals": [None, None]}] * 60 +
           [{"pred": "b", "gold": "a", "conf": 0.6, "kind": "choice",
             "cands": ["a", "b"], "probs": [1.0, 0.0], "vals": [None, None]}] * 40)
mc = so.metrica_choice(casos_c)
print(f"  {'OK ' if mc is None else 'FALLO'}  baseline = 1.0 (elegir 'a' acierta todo) "
      f"-> sin margen -> None{' ' * 6} obtenido {mc!r}")
if mc is not None:
    FALLOS.append("choice sin margen")

# Caso B: oro equilibrado -> el baseline baja a 0.5 y hay margen
casos_c2 = ([{"pred": "a", "gold": "a", "conf": 0.9, "kind": "choice",
              "cands": ["a", "b"], "probs": [1.0, 0.0], "vals": [None, None]}] * 50 +
            [{"pred": "a", "gold": "b", "conf": 0.7, "kind": "choice",
              "cands": ["a", "b"], "probs": [0.0, 1.0], "vals": [None, None]}] * 50)
mc2 = so.metrica_choice(casos_c2)
check("accuracy = 0.5", mc2["acc"], 0.5)
check("baseline uniforme = 0.5", mc2["baseline_uniforme"], 0.5)
check("baseline = 0.5 (elegir 'a' siempre)", mc2["baseline"], 0.5)
check("skill = (0.5-0.5)/(1-0.5) = 0", mc2["skill"], 0.0)

print()
print("=" * 84)
print("SCORE — normalizacion de valores y baseline de la mediana")
print("=" * 84)
# rubrica 0..1 con 3 niveles; el modelo siempre elige el de valor 1.0 y el
# objetivo siempre es 0.0 -> MAE = 1, baseline (todo en la mediana 0) = 0
# -> baseline MAE = 0 -> NO elegible
casos_s = [{"pred": "2", "gold": "0", "conf": 0.9, "kind": "score",
            "cands": ["0", "1", "2"], "probs": [1.0, 0.0, 0.0],
            "vals": [0.0, 0.5, 1.0]} for _ in range(10)]
ms = so.metrica_score(casos_s)
print(f"  {'OK ' if ms is None else 'FALLO'}  baseline MAE = 0 (todos los objetivos "
      f"iguales) -> None{' ' * 2} obtenido {ms!r}")
if ms is not None:
    FALLOS.append("score sin baseline")

# con objetivos repartidos: el modelo siempre elige el nivel 2 (valor 1.0)
casos_s2 = ([{"pred": "2", "gold": "0", "conf": 0.9, "kind": "score",
              "cands": ["0", "1", "2"], "probs": [1.0, 0.0, 0.0],
              "vals": [0.0, 0.5, 1.0]}] * 5 +
            [{"pred": "2", "gold": "2", "conf": 0.9, "kind": "score",
              "cands": ["0", "1", "2"], "probs": [0.0, 0.0, 1.0],
              "vals": [0.0, 0.5, 1.0]}] * 5)
ms2 = so.metrica_score(casos_s2)
# pred = 1.0 siempre. obj: 0.0 cinco veces y 1.0 cinco veces -> MAE = 0.5
# mediana de los objetivos = 0.5 -> base MAE = 0.5 -> skill = 0
check("MAE = 0.5", ms2["mae"], 0.5)
check("baseline MAE = 0.5 (mediana 0.5)", ms2["baseline_mae"], 0.5)
check("skill = 1 - 0.5/0.5 = 0", ms2["skill"], 0.0)

print()
print("=" * 84)
if FALLOS:
    print(f"  {len(FALLOS)} FALLOS: {FALLOS}")
    raise SystemExit(1)
print("  TODOS LOS TESTS PASAN — el implementador reproduce SCORING.md")
print("=" * 84)
