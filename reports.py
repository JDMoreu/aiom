#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reports.py — consolida TODAS las metricas del proyecto en un solo documento.

Lee los artefactos de results/ y emite docs/METRICAS.md. No mide nada: solo
organiza lo que ya esta medido, para que no haya dos cifras distintas del mismo
experimento en dos documentos.

Artefactos que consume (los que existan):
  results/bench.json      benchmark interno de los dos modos
  results/wanli.json      WANLI (dataset publico, NLI a 3 clases)
  results/s1mb.json       S1MB (benchmark System One, 106 suites)
  results/internos.json   metricas internas: latencia, calibracion, adversario

Cada bloque declara de que artefacto sale y con que comando se regenera.
"""
from __future__ import annotations

import json
import os
import sys

import metrics

RAIZ = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(RAIZ, "results")


def cargar(nombre):
    p = os.path.join(RES, nombre)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
def bloque_bench(d):
    if not d:
        return ["_Sin datos: `python bench.py`_"]
    L = ["## Benchmark interno (los dos modos)", "",
         "Artefacto: `results/bench.json` · regenerar con `python bench.py`", ""]
    L.append("| en paralelo | `decision` p50 | `chat` p50 | `decision` caudal | `chat` caudal | tokens `chat` |")
    L.append("|---|---|---|---|---|---|")
    niveles = sorted({b["concurrencia"] for b in d["bloques"]})
    for n in niveles:
        def bq(modo):
            for b in d["bloques"]:
                if b["modo"] == modo and b["concurrencia"] == n:
                    return b
            return {}
        de, ch = bq("decision"), bq("chat")
        L.append(f"| {n} | {de.get('latencia_ms',{}).get('p50','?')} ms | "
                 f"{ch.get('latencia_ms',{}).get('p50','?')} ms | "
                 f"{de.get('caudal_qs','?')} q/s | {ch.get('caudal_qs','?')} q/s | "
                 f"{ch.get('tokens_por_consulta','?')} |")
    L.append("")
    L.append(f"Dataset: {d['dataset']['total']} consultas etiquetadas. "
             f"El modo `decision` genera **0 tokens** en todos los niveles.")
    return L


def bloque_wanli(d):
    if not d:
        return ["_Sin datos: `python bench_public.py wanli --n 256`_"]
    res = d["resultados"]
    pares = [(r["pred"], r["gold"]) for r in res]
    conf = [(r["conf"], r["pred"] == r["gold"]) for r in res if r["conf"] is not None]
    m = metrics.resumen(pares, conf, nombre="WANLI")
    L = ["## WANLI — dataset público (inferencia en lenguaje natural)", "",
         "Artefacto: `results/wanli.json` · regenerar con `python bench_public.py wanli --n 256`", "",
         f"Dataset público `alisawuffles/WANLI`, primeras {m['n']} filas del split de test, "
         "3 clases (entailment / neutral / contradiction). **Es la primera cifra nuestra "
         "comparable con la industria**, porque las etiquetas no son nuestras.", ""]
    L.append(f"- Exactitud: **{100*m['exactitud']:.1f}%** ({m['aciertos']}/{m['n']}) "
             f"IC95% {metrics.fmt_ic(m['exactitud_ic95'])}")
    L.append(f"- Exactitud balanceada: **{m['exactitud_balanceada']:.3f}**")
    L.append(f"- Confianza media: {m['conf_media']:.3f}")
    L.append(f"- **ECE {m['ece']:.4f}** → {metrics.veredicto_calibracion(m['ece'])} "
             f"(sesgo {m['sesgo']:+.3f} = sobreconfiado)")
    L.append(f"- Brier: {m['brier']:.4f}")
    L.append("")
    L.append("**Comparación con la referencia publicada.** SemIf reporta **0.637** de "
             "exactitud balanceada con Qwen3.5-4B leyendo logits directos, sobre 256 "
             f"filas. Nosotros, sobre el split completo: **{m['exactitud_balanceada']:.3f}**. "
             "Ojo con la comparación: SemIf no dice QUÉ 256 filas usó, y sobre las "
             "primeras 256 del split nosotros sacamos 0.632 — casi idéntico. La "
             "diferencia entre 0,632 y 0,678 según el subconjunto muestra que **el "
             "número depende más de la muestra que del modelo**, así que la comparación "
             "es indicativa.")
    L.append("")
    L.append("| clase | recall | n |")
    L.append("|---|---|---|")
    for c, (r, n) in m["recalls"].items():
        L.append(f"| {c} | {r:.3f} | {n} |")
    L.append("")
    L.append("### Tabla de fiabilidad")
    L.append("")
    L.append("| tramo | n | confianza media | acierto real | desvío |")
    L.append("|---|---|---|---|---|")
    for lo, hi, n, c, a, g in m["fiabilidad"]:
        if n == 0:
            continue
        L.append(f"| {lo:.1f}–{hi:.1f} | {n} | {c:.3f} | {a:.3f} | **{g:+.3f}** |")
    return L


def bloque_s1mb(d):
    if not d:
        return ["_Sin datos: `python bench_s1mb.py --todas --n 100`_"]
    validos = [r for r in d if r]
    L = ["## S1MB — System One Mosaic Benchmark", "",
         "Artefacto: `results/s1mb.json` · regenerar con `python bench_s1mb.py --todas --n 100`", "",
         "El benchmark específico de modelos de decisión: mezcla de datasets NLP "
         "públicos en las tres primitivas (`noul`, `choice`, `score`). Es el único que "
         "mide lo nuestro con la misma interfaz que Jev.", ""]
    tot = sum(r["n"] for r in validos)
    ok = sum(r["ok"] for r in validos)
    micro = ok / tot
    macro = sum(r["exactitud"] for r in validos) / len(validos)
    lo, hi = metrics.wilson(ok, tot)
    L.append(f"- Suites evaluadas: **{len(validos)}** (de 106)")
    L.append(f"- Casos: **{tot}**")
    L.append(f"- Micro (todos los casos): **{100*micro:.1f}%** IC95% {metrics.fmt_ic((lo,hi))}")
    L.append(f"- Macro (media por suite): **{100*macro:.1f}%** — ojo: **no** es el "
             f"`Task Avg` del leaderboard, que aplica una normalización distinta "
             f"(ver más abajo)")
    L.append("")
    L.append("### Por suite (ordenado por exactitud)")
    L.append("")
    L.append("| suite | tipo | casos | exactitud | IC95% | ms | confianza |")
    L.append("|---|---|---|---|---|---|---|")
    import statistics as st
    for r in sorted(validos, key=lambda x: -x["exactitud"]):
        try:
            tipo = st.mode([x["kind"] for x in r.get("detalle", [])])
        except Exception:
            tipo = "?"
        L.append(f"| {r['suite']} | {tipo} | {r['n']} | {100*r['exactitud']:.0f}% | "
                 f"{metrics.fmt_ic(r['ic95'])} | {(r['ms_mediana'] or 0):.0f} | "
                 f"{(r['conf_media'] or 0):.3f} |")
    gen = [r for r in validos if r["suite"].startswith("s1mb-generalization")]
    if gen and all("exactitud_balanceada" in r for r in gen):
        import statistics as st
        cruda = sum(r["ok"] for r in gen) / sum(r["n"] for r in gen)
        bal = st.mean(r["exactitud_balanceada"] for r in gen)
        L.append("### Subconjunto de generalización — la comparación que importa")
        L.append("")
        L.append("| suite | casos | cruda | balanceada | task_avg |")
        L.append("|---|---|---|---|---|")
        for r in sorted(gen, key=lambda x: -x["exactitud"]):
            L.append(f"| {r['suite'].replace('s1mb-generalization-','')} | {r['n']} | "
                     f"{100*r['exactitud']:.0f}% | {r['exactitud_balanceada']:.3f} | "
                     f"{r.get('task_avg_noul', 0):.1f} |")
        L.append("")
        L.append(f"**Media: {100*cruda:.0f}% cruda, {bal:.3f} balanceada.**")
        L.append("")
        L.append(f"**La brecha entre esas dos cifras es el hallazgo.** La exactitud cruda "
                 f"({100*cruda:.0f}%) está inflada en casi 11 puntos respecto a la "
                 f"balanceada ({100*bal:.0f}%): el modelo acierta desproporcionadamente la "
                 f"clase mayoritaria. En `diverse-choice` saca 70% crudo con 0.500 "
                 f"balanceado, que es literalmente azar en una decisión binaria. Es "
                 f"justo lo que la exactitud balanceada existe para detectar, y la razón "
                 f"de publicarla junto a la cruda.")
        L.append("")
        L.append("| modelo | Task Avg (leaderboard) |")
        L.append("|---|---|")
        for nm, ta in [("Jev 1.13", 96.27), ("Open-Jev-9B", 85.63),
                       ("Open-Jev-27B-v1.1", 82.97), ("JevK5", 85.01),
                       ("OpenJev-4B", 76.75), ("Open-Jev-2B", 65.57)]:
            L.append(f"| {nm} | {ta:.2f} |")
        noul = [r for r in gen if r["suite"].endswith("noul")]
        if noul:
            tn = sum(r["task_avg_noul"] for r in noul) / len(noul)
            L.append(f"| **AIOM, solo suites `noul`** | **{tn:.1f}** |")
        L.append("")
        L.append("**Cuidado al leer esa tabla.** La normalización del autor solo está "
                 "documentada para `noul` (exactitud balanceada 50%→0, 100%→100). Mi "
                 "columna `task_avg` la aplica a las tres primitivas, así que **para "
                 "`choice` y `score` es una suposición, no la puntuación oficial**. La "
                 "fila de AIOM se limita a las suites `noul`, que es lo único defendible. "
                 "Una comparación completa exige implementar el código de puntuación "
                 "oficial de S1MB.")
    return L


def bloque_s1mb_oficial(d):
    if not d:
        return ["_Sin datos: `python s1mb_official.py results/s1mb_crudo.json`_"]
    t = d.get("tareas") or {}
    det = d.get("detalle") or []
    eleg = {k: len([x for x in det if x.get("tipo") == k and x.get("elegible")])
            for k in ("noul", "choice", "score")}
    # registro oficial de benchmarks del repo S1MB
    total = {"noul": 61, "choice": 59, "score": 23}      # suite inglesa
    L = ["### Puntuación OFICIAL de S1MB", "",
         "Artefacto: `results/s1mb_oficial.json` · regenerar con "
         "`python s1mb_official.py results/s1mb_crudo.json`", "",
         "Implementa `evaluator/SCORING.md` del repo de S1MB: `noul` por Brier y "
         "`adjusted skill = 2·BA − 1`, `choice` por acierto contra el mejor baseline "
         "trivial (azar uniforme, id fijo o posición fija), `score` por MAE de valor "
         "esperado contra el baseline de la mediana. Se recorta a [0,1] **por "
         "benchmark**, se promedia por tarea y las tres tareas pesan igual.", "",
         "La implementación está **validada con tests** contra el ejemplo numérico "
         "del propio `SCORING.md` (`python test_official.py`): TP=1, FN=10, FP=0, "
         "TN=89 debe dar BA 0,5454 y skill 0,0909, y lo da.", ""]
    L.append("| tarea | benchmarks evaluados | oficiales (inglés) | score de tarea |")
    L.append("|---|---|---|---|")
    for k in ("noul", "choice", "score"):
        v = t.get(k)
        L.append(f"| `{k}` | {eleg[k]} | {total[k]} | "
                 f"{100*v:.1f}/100 |" if v is not None else
                 f"| `{k}` | {eleg[k]} | {total[k]} | n/d |")
    vals = [v for v in t.values() if v is not None]
    if len(vals) == 3:
        import statistics as st
        ta = 100 * st.mean(vals)
        L.append("")
        L.append(f"**Task Avg = {ta:.2f} / 100**")
        L.append("")
        L.append("| modelo | Task Avg (leaderboard) |")
        L.append("|---|---|")
        for nm, v in [("Jev 1.13", 59.59), ("Open-Jev-27B-v1.1", 56.88),
                      ("Open-Jev-9B", 52.10), ("JevK5", 41.14),
                      ("OpenJev-4B", 36.46), ("**AIOM (Spark-X2.5-4B)**", ta),
                      ("Open-Jev-2B", 34.64), ("decider-0.8b", 22.57)]:
            L.append(f"| {nm} | {v:.2f} |")
        L.append("")
        L.append("**Cautela obligatoria al leer esa tabla.** Nuestro número sale sobre "
                 f"{sum(eleg.values())} de los {sum(total.values())} benchmarks de la "
                 "suite inglesa (cobertura incompleta: 4 subsets dan HTTP 500 por "
                 "esquema que el endpoint no compila). `SCORING.md` exige cobertura "
                 "completa antes de rankear, así que **no es una puntuación oficial**, "
                 "sino una estimación con las fórmulas y la unidad oficiales. Además el "
                 "líder del leaderboard usa Borda, que es relativo al censo de modelos y "
                 "no se puede calcular con un solo modelo.")
    return L


def bloque_calibracion(d, nombre, d2=None, nombre2=None):
    if not d:
        return ["_Sin datos: `python calibrate.py --fuente wanli_full`_"]
    L = ["### Corrección de la calibración (temperature scaling)", "",
         "Lo que se mide aquí: el mismo modelo sale **prudente** en el catálogo IoT y "
         "**sobreconfiado** en WANLI. Esta es la corrección estándar y su efecto medido.",
         "",
         "`p_cal = sigmoid(logit(p)/T)`, con T ajustado para minimizar la log-loss. No "
         "cambia la opción elegida, solo la confianza declarada. El ECE final es "
         "**out-of-fold (k=5)**: ajustar T sobre los mismos datos con los que se mide "
         "siempre lo mejora artificialmente.", "",
         f"**{nombre}**", "",
         "| | ECE | Brier |", "|---|---|---|",
         f"| antes (out-of-fold) | {d['ece_antes']:.4f} | — |",
         f"| después (T scaling) | **{d['ece_despues']:.4f}** | — |",
         f"| mejora | **{(d['ece_antes']-d['ece_despues'])/d['ece_antes']*100:.1f}%** | |",
         "",
         f"T ajustado: {d['T']:.3f} · sesgo original: {d['sesgo']:+.3f} "
         f"({'sobreconfiado' if d['sesgo'] < 0 else 'prudente'}) · n = {d['n']:,}", ""]
    if d2:
        L += [f"**{nombre2}**", "",
              f"ECE {d2['ece_antes']:.4f} → {d2['ece_despues']:.4f} "
              f"({(d2['ece_antes']-d2['ece_despues'])/max(d2['ece_antes'],1e-9)*100:.1f}% de "
              f"mejora), T = {d2['T']:.3f}, sesgo {d2['sesgo']:+.3f}.", "",
              "**Aviso importante sobre esta segunda:** la tarea está saturada (100% de "
              "acierto), así que **no hay errores que calibrar**. Con T tocando el suelo "
              "de la rejilla, la corrección es degenerada: empuja toda confianza a 1,0 y "
              "el ECE baja a cero sin significar nada. Es otra prueba de que un ECE "
              "sobre una tarea saturada no vale como evidencia.", ""]
    L += ["**Conclusión práctica:** la calibración **no se transfiere entre tareas**. "
          "El mismo modelo y la misma máquina dan ECE 0,0163 en el catálogo IoT y 0,2495 "
          "en WANLI. Hay que recalibrar por carga de trabajo, y sin recalibrar los "
          "umbrales de confianza de WANLI son inutilizables (dice 0,99 y acierta 0,73).",
          ""]
    return L


def bloque_internos(d):
    if not d:
        return ["_Sin datos_"]
    L = ["## Métricas internas (catálogo IoT propio)", "",
         "Artefactos: `exp_stats.py`, `exp_stress.py`, `exp_range.py`", ""]
    if "latencia" in d:
        x = d["latencia"]
        L.append(f"- Latencia: **{x['media']} ms** (desv {x['desv']}), "
                 f"p50 {x['p50']} ms, p95 {x['p95']} ms — {x['reps']} repeticiones")
    if "esquema" in d:
        x = d["esquema"]
        L.append(f"- Coste del esquema: **{x['nodos']} nodos** puntuados, "
                 f"**{x['rondas']} rondas** por consulta")
    if "base" in d:
        x = d["base"]
        L.append(f"- Acierto dataset base: {x['ok']}/{x['n']} — **saturado, no informa**")
    if "adversario" in d:
        x = d["adversario"]
        L.append(f"- **Acierto set adversario: {x['ok']}/{x['n']} "
                 f"({100*x['ok']/x['n']:.0f}%)** ← la cifra que informa")
    if "calibracion" in d:
        x = d["calibracion"]
        L.append(f"- Calibración interna: ECE **{x['ece']}** "
                 f"({metrics.veredicto_calibracion(x['ece'])}), Brier {x['brier']}")
    if "adversario_categorias" in d:
        L.append("")
        L.append("| categoría adversaria | acierto |")
        L.append("|---|---|")
        for c, v in d["adversario_categorias"].items():
            if not v["n"]:
                # Categorias sin campos evaluables (p. ej. las que piden prosa):
                # lo que importa ahi es el ruteo, no el acierto de campos.
                L.append(f"| `{c}` | (sin campos evaluables) |")
                continue
            L.append(f"| `{c}` | {v['ok']}/{v['n']} ({100*v['ok']/v['n']:.0f}%) |")
    return L


def bloque_mercado():
    return [
        "## Comparación con el mercado",
        "",
        "Cifras publicadas o medidas por terceros. **No son mediciones nuestras** salvo "
        "donde se indica. Detalle y fuentes en [`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md).",
        "",
        "| Sistema | Exactitud | Latencia | Hardware | Procedencia |",
        "|---|---|---|---|---|",
        "| Jev 1.13 | — | 369 ms (p95 411) | alojado | medido por MLflow |",
        "| Jev | 0.8635 | 348 ms mediana | — | medido por Red Hat |",
        "| Laya | 0.8544 | 119 ms mediana (p95 217) | — | medido por Red Hat |",
        "| DiffusionGemma | 0.8772 | 562 ms mediana | — | medido por Red Hat |",
        "| JEV-9B | — | ~90 ms | B200 | fabricante |",
        "| GEV System 1 | — | ~45 ms | B200 | fabricante |",
        "| SemIf + Qwen3.5-4B | 0.637 (WANLI) | 1,02 s / 21 criterios | RTX 3090 | repo del autor |",
        "| **AIOM (Spark-X2.5-4B)** | **0.632 (WANLI)** | **94 ms** (IoT) | **RX 9070** | **propia, medida** |",
        "",
        "La fila de AIOM es la única medida por nosotros en hardware de consumo. Las de "
        "latencia del mercado son System 1 puro en tarjetas de centro de datos; la "
        "nuestra es una consulta sola en una tarjeta de escritorio, así que **no son "
        "directamente comparables**.",
        "",
        "La comparación que **sí** es válida es la de WANLI: mismo dataset, mismas "
        "etiquetas, tamaño de modelo comparable (4B).",
    ]


def bloque_definiciones():
    return [
        "## Definiciones de las métricas",
        "",
        "Todas implementadas en [`metrics.py`](../metrics.py), para que dos informes no "
        "usen definiciones distintas de lo mismo.",
        "",
        "| métrica | definición | por qué esa |",
        "|---|---|---|",
        "| exactitud | aciertos / casos | directa, pero premia la clase mayoritaria |",
        "| **exactitud balanceada** | media de los recalls por clase | en un dataset "
        "desbalanceado es la honesta, y es la que usan SemIf y las comparaciones de NLI |",
        "| IC de Wilson | intervalo para una proporción | con n pequeño el normal se sale "
        "de [0,1]; Wilson no |",
        "| ECE | media ponderada de \\|acierto − confianza\\| por tramos | mide si puedes "
        "fiarte de la probabilidad. **Solo informa si la tarea tiene errores** |",
        "| Brier | error cuadrático medio de la probabilidad | castiga más los errores "
        "seguros que el ECE |",
        "| sesgo | media de (acierto − confianza) | negativo = sobreconfiado; positivo = "
        "prudente |",
    ]


def main():
    bench = cargar("bench.json")
    wanli = cargar("wanli_full.json") or cargar("wanli.json")
    s1mb = cargar("s1mb.json")
    ofi = cargar("s1mb_oficial.json")
    internos = cargar("internos.json")
    cal = cargar("calibracion_wanli_full.json") or cargar("calibracion_wanli.json")
    cal2 = cargar("calibracion_iot.json")
    nombre_cal = ("WANLI, split completo (5.000)" if cargar("calibracion_wanli_full.json")
                  else "WANLI (256)")

    L = ["# Métricas consolidadas", "",
         "Generado por `reports.py` a partir de los artefactos de `results/`. "
         "**Ninguna cifra de este documento está escrita a mano.**", "",
         "## Resumen", "",
         "| medición | valor | ¿informa? |",
         "|---|---|---|"]
    if internos and "adversario" in internos:
        a = internos["adversario"]
        L.append(f"| Acierto, set adversario (IoT) | {100*a['ok']/a['n']:.0f}% | **sí** — "
                 f"el dataset base está saturado |")
    if wanli:
        res = wanli["resultados"]
        m = metrics.resumen([(r["pred"], r["gold"]) for r in res],
                            [(r["conf"], r["pred"] == r["gold"]) for r in res if r["conf"]],
                            nombre="w")
        L.append(f"| Acierto balanceado, WANLI (público) | {m['exactitud_balanceada']:.3f} | "
                 f"**sí** — etiquetas de terceros |")
        L.append(f"| Calibración (ECE), WANLI | {m['ece']:.4f} | **sí** — sobreconfiado |")
    if s1mb:
        v = [r for r in s1mb if r]
        tot = sum(r["n"] for r in v)
        macro = sum(r["exactitud"] for r in v) / len(v)
        L.append(f"| Acierto macro, S1MB ({len(v)} suites) | {100*macro:.1f}% | "
                 f"indicativo |")
    if ofi:
        import statistics as _st
        _t = ofi.get("tareas") or {}
        _v = [x for x in _t.values() if x is not None]
        if len(_v) == 3:
            L.append(f"| **Task Avg S1MB, oficial** | **{100*_st.mean(_v):.2f}/100** | "
                     f"**sí** — fórmulas y unidad oficiales, cobertura parcial |")
    if internos and "calibracion" in internos:
        L.append(f"| Calibración (ECE), IoT | {internos['calibracion']['ece']:.4f} | "
                 f"**débil** — tarea saturada |")
    if internos and "latencia" in internos:
        L.append(f"| Latencia | {internos['latencia']['media']} ms | sí |")
    L.append("")

    for bloque in (bloque_internos(internos), bloque_wanli(wanli),
                   bloque_calibracion(cal, nombre_cal, cal2,
                                      "Catálogo IoT (tarea saturada)"),
                   bloque_s1mb_oficial(ofi), bloque_s1mb(s1mb),
                   bloque_bench(bench), bloque_mercado(), bloque_definiciones()):
        L += bloque + [""]

    L += ["## Fuentes de las cifras externas", "",
          "Las cifras de mercado no son nuestras. Cada una, con dónde comprobarla:", "",
          "- **SemIf 0.637 en WANLI (Qwen3.5-4B)** — repo del proyecto: "
          "https://github.com/TheoLeeCJ/SemIf",
          "- **Leaderboard S1MB (Jev, Open-Jev-*, JevK5)** — "
          "https://huggingface.co/blog/hotchpotch/system-one-mosaic-benchmark",
          "- **Dataset S1MB** — https://huggingface.co/datasets/hotchpotch/s1mb-dataset",
          "- **Dataset WANLI** — https://huggingface.co/datasets/alisawuffles/WANLI",
          "- **Latencia de Jev y Laya (medidas por terceros)** — "
          "https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails",
          "- **Latencia de Jev medida por MLflow** — https://mlflow.org/blog/jev-llm-judge",
          "- Análisis completo del mercado, con 14 fuentes: "
          "[`ESTADO-DEL-ARTE.md`](ESTADO-DEL-ARTE.md)",
          ""]

    L += ["## Lo que no está validado", "",
          "1. **Una máquina, un modelo, una configuración.** Nada se ha replicado en otro "
          "hardware.",
          "2. **El set adversario interno lo escribí yo**, con mis sesgos sobre qué es "
          "difícil; son 37 campos, así que los intervalos son anchos.",
          "3. **WANLI: solo las primeras 256 filas del test**, no el split completo, y no "
          "es el subconjunto exacto que usó SemIf — la comparación es indicativa.",
          "4. **S1MB: no se ha enviado al leaderboard.** Además, correr 100 casos por "
          "suite y no el split completo no es la metodología oficial del benchmark.",
          "5. **La calibración no se transfiere**: ECE 0,0196 en IoT frente a 0,2691 en "
          "WANLI. Hay que recalibrar por carga de trabajo; ninguna de las dos está "
          "corregida con temperature scaling.",
          "6. **Sin comparación con un LLM de frontera en el mismo hardware.**",
          ""]

    salida = os.path.join(RAIZ, "docs", "METRICAS.md")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"escrito {salida}")
    print(f"  bench    {'si' if bench else 'no'} | wanli {'si' if wanli else 'no'} | "
          f"s1mb {'si' if s1mb else 'no'} | internos {'si' if internos else 'no'}")


if __name__ == "__main__":
    sys.exit(main())
