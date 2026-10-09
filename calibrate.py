#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calibrate.py — arregla la calibracion con temperature scaling, y lo mide.

Contexto medido: el mismo modelo esta PRUDENTE en el catalogo IoT (ECE 0.0163) y
GRAVEMENTE SOBRECONFIADO en WANLI (ECE 0.2691). Esa segunda no es usable para
decidir con umbrales: dice 0.99 y acierta 0.70.

Temperature scaling es la correccion mas simple y la mas citada:

    p_cal = sigmoid( logit(p) / T ),   T ajustado para minimizar la log-loss

T > 1 aplana la confianza (arregla la sobreconfianza); T < 1 la afila. No cambia
la opcion elegida, solo la confianza que declaras, asi que no puede empeorar el
acierto. Es exactamente lo que SemIf reporta en sus tablas de ECE.

**Se ajusta con validacion cruzada, no in-sample**: ajustar T sobre los mismos
datos con los que mides el ECE siempre lo mejora artificialmente. Aqui se parte
en k pliegues y el ECE final es OUT-OF-FOLD, como el de SemIf.

Uso:  python calibrate.py                 (WANLI)
      python calibrate.py --fuente iot
"""
from __future__ import annotations

import argparse
import json
import math
import statistics

import metrics

EPS = 1e-6


def logit(p):
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def sigmoid(x):
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def p_cal(p, T):
    return sigmoid(logit(p) / T)


def nll(pares, T):
    """Log-loss de las confianzas reescaladas frente al acierto real."""
    s = 0.0
    for p, ok in pares:
        q = min(max(p_cal(p, T), EPS), 1 - EPS)
        s -= math.log(q) if ok else math.log(1 - q)
    return s / len(pares)


def ajustar_T(pares, lo=0.05, hi=40.0, pasos=1600):
    """Busqueda en rejilla: sin dependencias y con un unico minimo claro.

    Ojo con el tope: si T sale igual a `hi`, el optimo esta FUERA de la rejilla y
    el ajuste esta truncado. Se avisa en el informe.
    """
    mejor, mejorT = None, 1.0
    for i in range(pasos + 1):
        T = lo + (hi - lo) * i / pasos
        v = nll(pares, T)
        if mejor is None or v < mejor:
            mejor, mejorT = v, T
    return mejorT, (mejorT >= hi - 1e-9)


def out_of_fold(pares, pliegues=5):
    """EDA out-of-fold: T se ajusta en k-1 pliegues y se evalua en el que falta."""
    idx = list(range(len(pares)))
    tam = len(idx) // pliegues
    reales, calibradas, Ts, avisos = [], [], [], []
    for k in range(pliegues):
        val = idx[k * tam:(k + 1) * tam] if k < pliegues - 1 else idx[k * tam:]
        ent = [idx[i] for i in idx if i not in set(val)]
        if not ent or not val:
            continue
        T, truncado = ajustar_T([pares[i] for i in ent])
        if truncado:
            avisos.append(T)
        Ts.append(T)
        for i in val:
            p, ok = pares[i]
            reales.append((p, ok))
            calibradas.append((p_cal(p, T), ok))
    return reales, calibradas, (statistics.mean(Ts) if Ts else 1.0), len(avisos)


def informe(nombre, pares):
    e0, f0, n = metrics.ece(pares)
    e1, f1, _ = metrics.ece(pares)
    reales, calibradas, T, truncados = out_of_fold(pares)
    e_real, fr, _ = metrics.ece(reales)
    e_cal, fc, _ = metrics.ece(calibradas)
    conf0 = statistics.mean(c for c, _ in pares)
    acc0 = statistics.mean(1.0 if ok else 0.0 for _, ok in pares)

    print("=" * 80)
    print(f"{nombre}  ({len(pares)} decisiones, T medio ajustado {T:.3f})")
    print("=" * 80)
    print(f"  confianza media declarada : {conf0:.3f}")
    print(f"  acierto real              : {acc0:.3f}")
    print(f"  sesgo                     : {acc0-conf0:+.3f}  "
          f"({'SOBREconfiado' if acc0 < conf0 else 'prudente'})")
    print()
    print(f"  {'':<22} {'ECE':>8} {'Brier':>8}")
    print(f"  {'antes (out-of-fold)':<22} {e_real:>8.4f} {metrics.brier(reales):>8.4f}")
    print(f"  {'despues (T scaling)':<22} {e_cal:>8.4f} {metrics.brier(calibradas):>8.4f}")
    if e_real > 0:
        print(f"  {'mejora':<22} {(e_real-e_cal)/e_real*100:>7.1f}%")
    if truncados:
        print(f"  AVISO: T tocó el tope de la rejilla en {truncados} de 5 pliegues;")
        print(f"         el óptimo está fuera y el ajuste queda truncado (sube el rango).")
    print()
    print(f"  fiabilidad ANTES / DESPUES")
    print(f"  (los tramos se definen por la confianza ORIGINAL, para que las filas "
          f"cuadren;")
    print(f"   la 2a columna es lo que dice el modelo DESPUES de reescalar)")
    print(f"  {'tramo':>10} {'n':>6} {'conf':>7} {'acierto':>8} | {'conf*':>7} {'acierto*':>8}")
    por_tramo = {}
    for (p, ok), (pc, _) in zip(reales, calibradas):
        por_tramo.setdefault(int(p * 10), []).append((p, pc, ok))
    for b in sorted(por_tramo):
        v = por_tramo[b]
        conf = statistics.mean(p for p, _, _ in v)
        acc = statistics.mean(1.0 if ok else 0.0 for _, _, ok in v)
        c2 = statistics.mean(pc for _, pc, _ in v)
        print(f"  {b/10:.1f}-{(b+1)/10:.1f}".rjust(10) +
              f" {len(v):>6} {conf:>7.3f} {acc:>8.3f} | {c2:>7.3f} {acc:>8.3f}")
    return {"ece_antes": e_real, "ece_despues": e_cal, "T": T,
            "sesgo": acc0 - conf0, "n": len(pares)}


def cargar(fuente):
    if fuente == "wanli":
        d = json.load(open("results/wanli.json", encoding="utf-8"))
        return [(r["conf"], r["pred"] == r["gold"]) for r in d["resultados"]
                if r.get("conf") is not None], "WANLI (NLI, 3 clases)"
    if fuente == "wanli_full":
        d = json.load(open("results/wanli_full.json", encoding="utf-8"))
        return [(r["conf"], r["pred"] == r["gold"]) for r in d["resultados"]
                if r.get("conf") is not None], "WANLI split completo (5.000)"
    d = json.load(open("results/internos.json", encoding="utf-8"))
    filas = d["calibracion"]["fiabilidad"]
    pares = []
    for lo, hi, n, conf, acc, _ in filas:
        if not n:
            continue
        # reconstruye el tramo: n casos, `acc` de ellos correctos, confianza `conf`
        k = int(round(acc * n))
        pares += [(conf, i < k) for i in range(n)]
    return pares, "Catálogo IoT (tarea saturada)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", default="wanli_full",
                    choices=["wanli", "wanli_full", "iot"])
    a = ap.parse_args()
    pares, nombre = cargar(a.fuente)
    r = informe(nombre, pares)
    print()
    print("  Nota: el ECE final es OUT-OF-FOLD (k=5). Ajustar T sobre los mismos")
    print("  datos con los que se mide siempre mejora el numero; esto no lo hace.")
    with open(f"results/calibracion_{a.fuente}.json", "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"  escrito results/calibracion_{a.fuente}.json")


if __name__ == "__main__":
    main()
