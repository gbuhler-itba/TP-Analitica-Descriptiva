"""
Diagnóstico de las correcciones de la PreEntrega 1.
No modifica ningún dataset: solo lee data/processed y escribe en salida/.
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu, spearmanr

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from src.indice_confort import (MAPEO_BLOQUES, PESOS_BASE, completitud, gap_por_zona,
                                indice, preparar_componentes, puntaje_bloques, tipo_de_columna)

SAL = Path(__file__).resolve().parent / "salida"
SAL.mkdir(exist_ok=True)
df = pd.read_csv(RAIZ / "data" / "processed" / "propiedades_enriquecidas.tsv", sep="\t", low_memory=False)
res = {}
from src.limpieza import corregir_precio
pc = corregir_precio(df)
res["precio_concatenado"] = {"filas": int(pc.bajo_de_precio.sum()),
    "mediana_usd_original": float(df.loc[df.moneda == "USD", "precio"].median()),
    "media_usd_original": float(df.loc[df.moneda == "USD", "precio"].mean()),
    "baja_pct_mediana": float(pc.baja_pct.median()), "baja_pct_min": float(pc.baja_pct.min())}
df["precio"] = pc["precio_actual"]

# ---------------- Tarea 1: cifras
res["mediana_precio_usd"] = float(df.loc[df.moneda == "USD", "precio"].median())
res["mediana_m2"] = float(df["m2"].median())
res["filas_ars"] = int((df.moneda == "ARS").sum())

# ---------------- Tarea 2: sesgo geocoding
df["geo_ok"] = df.geo_status == "OK"
df["pm2"] = np.where((df.moneda == "USD") & (df.m2 >= 15), df.precio / df.m2, np.nan)
por_barrio = df.groupby("barrio").agg(avisos=("geo_ok", "size"), geocodificados=("geo_ok", "sum"),
                                      tasa_ok=("geo_ok", "mean"), mediana_pm2=("pm2", "median"))
por_barrio["perdidos"] = por_barrio.avisos - por_barrio.geocodificados
por_barrio = por_barrio.sort_values("tasa_ok")
por_barrio.round(3).to_csv(SAL / "geocoding_por_barrio.csv")
chi = chi2_contingency(pd.crosstab(df.barrio, df.geo_ok))
mw = mannwhitneyu(df.loc[df.geo_ok, "pm2"].dropna(), df.loc[~df.geo_ok, "pm2"].dropna())
comp_all = preparar_componentes(df)
res["geocoding"] = {
    "tasa_global": float(df.geo_ok.mean()),
    "chi2_barrio_p": float(chi[1]),
    "tasa_min": por_barrio.tasa_ok.min(), "barrio_min": por_barrio.index[0],
    "tasa_max": por_barrio.tasa_ok.max(), "barrio_max": por_barrio.index[-1],
    "barrios_bajo_75": por_barrio.index[por_barrio.tasa_ok < 0.75].tolist(),
    "mediana_pm2_ok": float(df.loc[df.geo_ok, "pm2"].median()),
    "mediana_pm2_no_ok": float(df.loc[~df.geo_ok, "pm2"].median()),
    "mannwhitney_p": float(mw.pvalue),
    "mediana_m2_ok": float(df.loc[df.geo_ok, "m2"].median()),
    "mediana_m2_no_ok": float(df.loc[~df.geo_ok, "m2"].median()),
    "completitud_ok": float(completitud(comp_all)[df.geo_ok].mean()),
    "completitud_no_ok": float(completitud(comp_all)[~df.geo_ok].mean()),
    "spearman_tasa_vs_pm2_barrio": float(spearmanr(por_barrio.tasa_ok, por_barrio.mediana_pm2)[0]),
}

# ---------------- Tarea 3: índice
# Muestra provisoria para el diagnóstico (la limpieza formal va en el notebook 01)
m = df.geo_ok & (df.moneda == "USD") & df.m2.between(15, 1000)
lo, hi = df.loc[m, "pm2"].quantile([0.01, 0.99])
m &= df.pm2.between(lo, hi)
d = df[m].copy()
res["muestra_diagnostico"] = {"filas": int(len(d)), "pm2_p01": float(lo), "pm2_p99": float(hi)}
comp = preparar_componentes(d)
d["log_pm2"] = np.log(d.pm2)
zona = d.subzona

# 3a. componentes
filas = []
for bloque, cols in MAPEO_BLOQUES.items():
    for c in cols:
        s = comp[c]
        tipo = "derivada" if c.startswith("es_") else tipo_de_columna(d[c])
        dif = []
        for _, g in d.assign(v=s).groupby("subzona"):
            a = g.loc[g.v == 1, "pm2"]
            b = g.loc[g.v != 1, "pm2"]
            if len(a) >= 10 and len(b) >= 10:
                dif.append(a.median() / b.median() - 1)
        filas.append({
            "bloque": bloque, "componente": c, "tipo": tipo,
            "pct_si": round(100 * (s == 1).mean(), 1),
            "pct_no": round(100 * (s == 0).mean(), 1),
            "pct_nulo": round(100 * s.isna().mean(), 1),
            "subzonas_comparables": len(dif),
            "prima_mediana_pm2_pct": round(100 * np.median(dif), 1) if dif else np.nan,
        })
tab_comp = pd.DataFrame(filas)
tab_comp.to_csv(SAL / "componentes.csv", index=False)


def diag_bloques(tratamiento):
    bl = puntaje_bloques(comp, tratamiento)
    out = {}
    y_dm = d.log_pm2 - d.groupby("subzona").log_pm2.transform("mean")
    for b in bl.columns:
        x = bl[b]
        ok = x.notna()
        var_tot = x[ok].var()
        var_intra = (x[ok] - x[ok].groupby(zona[ok]).transform("mean")).var()
        x_dm = x - x.groupby(zona).transform("mean")
        r = spearmanr(x_dm[ok], y_dm[ok])[0]
        out[b] = {
            "media": round(x.mean(), 3), "desvio": round(x.std(), 3),
            "pct_valores_distintos": int(x.nunique()),
            "pct_en_cero": round(100 * (x == 0).mean(), 1),
            "pct_varianza_intra_subzona": round(100 * var_intra / var_tot, 1),
            "spearman_intra_subzona_vs_log_pm2": round(r, 3),
        }
    bl["completitud"] = completitud(comp)
    out["corr_bloques_con_completitud"] = {b: round(spearmanr(bl[b], bl.completitud, nan_policy="omit")[0], 3)
                                           for b in MAPEO_BLOQUES}
    return out, bl


res["bloques_nulo_es_no"], bl_a = diag_bloques("nulo_es_no")
res["bloques_solo_declarados"], bl_b = diag_bloques("solo_declarados")

# 3b. sensibilidad a los pesos
TOP = 0.05


def marcados(bl, pesos):
    idx = indice(bl, pesos)
    g = gap_por_zona(d.log_pm2, idx, zona)
    corte = g.quantile(TOP)
    return set(g.index[g <= corte]), g


base_set, base_gap = marcados(bl_a, PESOS_BASE)
grilla = []
paso = 0.05
vals = np.round(np.arange(0.05, 0.91, paso), 2)
for wi, wa in itertools.product(vals, vals):
    wt = round(1 - wi - wa, 2)
    if wt < 0.05 - 1e-9:
        continue
    pesos = {"infraestructura": wi, "amenities": wa, "atributos": wt}
    s, g = marcados(bl_a, pesos)
    grilla.append({**pesos, "jaccard_vs_base": len(s & base_set) / len(s | base_set),
                   "spearman_gap_vs_base": spearmanr(g, base_gap, nan_policy="omit")[0]})
grilla = pd.DataFrame(grilla)
grilla.round(3).to_csv(SAL / "sensibilidad_pesos.csv", index=False)

# presencia de cada propiedad marcada en las distintas ponderaciones
cuenta = pd.Series(0, index=d.index)
for _, r in grilla.iterrows():
    s, _ = marcados(bl_a, {"infraestructura": r.infraestructura, "amenities": r.amenities,
                           "atributos": r.atributos})
    cuenta.loc[list(s)] += 1
frac = cuenta / len(grilla)
alt_nulos, _ = marcados(bl_b.fillna(bl_b.mean()), PESOS_BASE)
# sin índice: solo precio relativo a la zona
sin_indice = d.log_pm2 - d.groupby("subzona").log_pm2.transform("mean")
set_sin_indice = set(sin_indice.index[sin_indice <= sin_indice.quantile(TOP)])
res["sensibilidad"] = {
    "combinaciones": int(len(grilla)),
    "marcados_por_ponderacion": len(base_set),
    "jaccard_min": round(grilla.jaccard_vs_base.min(), 3),
    "jaccard_mediana": round(grilla.jaccard_vs_base.median(), 3),
    "spearman_gap_min": round(grilla.spearman_gap_vs_base.min(), 3),
    "propiedades_marcadas_alguna_vez": int((frac > 0).sum()),
    "marcadas_en_90pct_o_mas": int((frac >= 0.9).sum()),
    "marcadas_en_todas": int((frac == 1).sum()),
    "jaccard_base_vs_tratamiento_nulos_alt": round(len(alt_nulos & base_set) / len(alt_nulos | base_set), 3),
    "jaccard_base_vs_sin_indice": round(len(set_sin_indice & base_set) / len(set_sin_indice | base_set), 3),
    "peor_combinacion": grilla.sort_values("jaccard_vs_base").iloc[0][["infraestructura", "amenities", "atributos"]].to_dict(),
}
json.dump(res, open(SAL / "resumen.json", "w"), indent=2, ensure_ascii=False, default=float)
print(json.dumps(res, indent=2, ensure_ascii=False, default=float))
print(tab_comp.to_string())
