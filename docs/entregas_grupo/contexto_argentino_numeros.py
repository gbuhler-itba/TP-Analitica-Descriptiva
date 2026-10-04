"""
Números propios citados en contexto_argentino.md.
Correr desde la raíz del repo:  python3 docs/entregas_grupo/contexto_argentino_numeros.py
No modifica ningún archivo.

Usa el dataset limpio (salida del notebook 01), el mismo que el resto del análisis.
El conteo de avisos en USD se hace sobre el dataset del pipeline, porque el limpio
ya excluye los avisos en pesos.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]

# Tipos de cambio al 14/08/2026 (fecha del scraping). Ver fuentes en el .md
TC_A3500 = 1488.6984     # tipo de cambio de referencia Com. "A" 3500, BCRA
TC_MEP = 1518.05         # cierre MEP

crudo = pd.read_csv(RAIZ / "data" / "processed" / "propiedades_enriquecidas.tsv", sep="\t", low_memory=False)
df = pd.read_csv(RAIZ / "data" / "processed" / "propiedades_limpias.tsv", sep="\t", low_memory=False)

print("== Dolarización (dataset del pipeline) ==")
print("Avisos en USD:", (crudo["moneda"] == "USD").sum(), "de", len(crudo))

print("\n== Expensas (dataset limpio) ==")
en_ars = df["expensas_moneda"] == "ARS"
mediana = df.loc[en_ars, "expensas_monto"].median()
print("Con dato: %.1f%%" % (df["expensas_monto"].notna().mean() * 100))
print("Mediana ARS:", mediana)
print("  en USD al MEP: %.1f | al A 3500: %.1f" % (mediana / TC_MEP, mediana / TC_A3500))

print("\n== Apto crédito ==")
print((df["apto_credito"].value_counts(dropna=False, normalize=True) * 100).round(1))

g = df.dropna(subset=["subzona", "apto_credito"])
t = g.groupby(["subzona", "apto_credito"])["precio_m2_usd"].agg(["median", "size"]).unstack()
t = t[(t["size"]["Sí"] >= 10) & (t["size"]["No"] >= 10)]
dif = (t["median"]["Sí"] / t["median"]["No"] - 1) * 100
print("Sub-zonas comparables:", len(dif))
print("Diferencia mediana de precio/m2, apto vs. no apto: %.1f%%" % dif.median())
print("Sub-zonas donde el apto es más barato: %.0f%%" % ((dif < 0).mean() * 100))
print("Antigüedad mediana:", df.groupby("apto_credito")["antiguedad"].median().to_dict())

print("\n== Baja de precio (iliquidez) ==")
print("Avisos con BAJÓ DE PRECIO:", df["bajo_de_precio"].sum(), "(%.1f%%)" % (df["bajo_de_precio"].mean() * 100))
print("Baja mediana: %.1f%% | mínima: %.1f%%" % (df["baja_pct"].median(), df["baja_pct"].min()))
z = df.dropna(subset=["subzona"]).copy()
z["rel"] = np.log(z["precio_m2_usd"]) - z.groupby("subzona")["precio_m2_usd"].transform(lambda s: np.log(s).mean())
baratos = z[z["rel"] <= z["rel"].quantile(0.05)]
resto = z.drop(baratos.index)
print("5%% más barato para su sub-zona: %d avisos" % len(baratos))
print("  con baja de precio: %.1f%% (resto: %.1f%%)" % (baratos["bajo_de_precio"].mean() * 100, resto["bajo_de_precio"].mean() * 100))

print("\n== Precio publicado vs. precio de cierre ==")
a = df[df["ambientes"].between(1, 3)]
print("Avisos de 1 a 3 ambientes:", len(a), "| mediana USD/m2 publicada:", round(a["precio_m2_usd"].median()))
