import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr

# Raíz del repo: funciona como script desde cualquier carpeta y en notebooks
try:
    RAIZ = Path(__file__).resolve().parents[2]
except NameError:  # en un notebook no existe __file__
    RAIZ = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(RAIZ))
from src.indice_confort import MAPEO_BLOQUES, preparar_componentes, tipo_de_columna
from src.limpieza import corregir_precio

df = pd.read_csv(RAIZ / "data" / "processed" / "propiedades_enriquecidas.tsv", sep="\t", low_memory=False)

# ---------------------------------------------------------------------------
# 1. Precio corregido, antigüedad numérica y muestra de trabajo
# ---------------------------------------------------------------------------
df["precio"] = corregir_precio(df)["precio_actual"]

antig = pd.to_numeric(df["antig_edad"].str.replace(" años", "").str.replace(" año", "")
                      .str.replace(".", "", regex=False), errors="coerce")
antig = np.where(antig >= 1800, 2026 - antig, antig)   # "1.976 años" es el año, no la edad
df["antiguedad"] = np.where(antig < 0, np.nan, antig)  # negativos: a revisar en el notebook 01

muestra = (df["geo_status"] == "OK") & (df["moneda"] == "USD") & df["m2"].between(15, 1000)
d = df[muestra].copy()
d["pm2"] = d["precio"] / d["m2"]
lo, hi = d["pm2"].quantile([0.01, 0.99])
d = d[d["pm2"].between(lo, hi)].copy()
d["log_pm2"] = np.log(d["pm2"])
d["log_m2"] = np.log(d["m2"])
print(f"Muestra: {len(d)} avisos")

comp = preparar_componentes(d)


# ---------------------------------------------------------------------------
# 2. Todo "dentro de la sub-zona": se le resta a cada variable la media de su
#    sub-zona, así la correlación compara departamentos de la misma zona
# ---------------------------------------------------------------------------
def intra(serie):
    return serie - serie.groupby(d["subzona"]).transform("mean")


def residualizar(y, controles):
    """Saca de y la parte explicada linealmente por los controles."""
    datos = pd.concat([y, controles], axis=1).dropna()
    X = np.column_stack([np.ones(len(datos)), datos.iloc[:, 1:].values])
    beta, *_ = np.linalg.lstsq(X, datos.iloc[:, 0].values, rcond=None)
    return pd.Series(datos.iloc[:, 0].values - X @ beta, index=datos.index)


y_intra = intra(d["log_pm2"])
controles = pd.concat([intra(d["log_m2"]), intra(d["antiguedad"])], axis=1)

filas = []
for bloque, columnas in MAPEO_BLOQUES.items():
    for c in columnas:
        x = comp[c]  # 1 / 0 / NaN (no declarado)
        tipo = "derivada" if c.startswith("es_") else tipo_de_columna(d[c])
        x_nulo_no = x.fillna(0)

        # (a) correlación simple dentro de la sub-zona, nulo = "no tiene"
        rho_simple = spearmanr(intra(x_nulo_no), y_intra)[0]

        # (b) igual, pero controlando por superficie y antigüedad
        #     (compara departamentos de tamaño y edad parecidos)
        x_res = residualizar(intra(x_nulo_no), controles)
        y_res = residualizar(y_intra, controles)
        comunes = x_res.index.intersection(y_res.index)
        rho_ctrl = spearmanr(x_res[comunes], y_res[comunes])[0]

        # (c) solo sobre avisos que declararon el dato (sirve en columnas Sí/No)
        dec = x.notna()
        rho_declarados = (spearmanr(intra(x[dec]), y_intra[dec])[0]
                          if tipo != "solo_si" and x[dec].nunique() > 1 else np.nan)

        filas.append({
            "bloque": bloque, "componente": c, "tipo": tipo,
            "pct_si": 100 * (x == 1).mean(), "pct_nulo": 100 * x.isna().mean(),
            "rho_simple": rho_simple, "rho_ctrl_m2_antig": rho_ctrl,
            "rho_solo_declarados": rho_declarados,
        })

tabla = pd.DataFrame(filas).round(3)
tabla = tabla.sort_values(["bloque", "rho_ctrl_m2_antig"], ascending=[True, False])
print(tabla.to_string(index=False))

# ---------------------------------------------------------------------------
# 3. Una propuesta de pesos derivados de los datos (una de varias opciones)
#    Peso de cada componente proporcional a su rho controlado, descartando
#    los que dan <= 0.02 (no aportan o van en contra).
# ---------------------------------------------------------------------------
UMBRAL = 0.02
tabla["peso_componente"] = np.where(tabla["rho_ctrl_m2_antig"] > UMBRAL, tabla["rho_ctrl_m2_antig"], 0)
tabla["peso_componente"] = tabla["peso_componente"] / tabla["peso_componente"].sum()
pesos_bloque = tabla.groupby("bloque")["peso_componente"].sum().round(3)
print("\nPesos por bloque que implican los datos (vs. 45/30/25 original):")
print(pesos_bloque)
print("\nComponentes descartados:", tabla.loc[tabla["peso_componente"] == 0, "componente"].tolist())

# ---------------------------------------------------------------------------
# 4. Correlación entre componentes: detecta redundancias
#    (si dos van siempre juntos, están contando lo mismo dos veces)
# ---------------------------------------------------------------------------
orden = [c for cols in MAPEO_BLOQUES.values() for c in cols]
matriz = comp[orden].fillna(0).corr(method="spearman")
plt.figure(figsize=(11, 9))
sns.heatmap(matriz, cmap="RdBu_r", center=0, vmin=-1, vmax=1, annot=True, fmt=".1f",
            annot_kws={"size": 7}, cbar_kws={"label": "Spearman"})
plt.title("Correlación entre componentes del índice (nulo = no tiene)")
plt.tight_layout()
plt.show()

pares = (matriz.where(np.triu(np.ones(matriz.shape, dtype=bool), k=1)).stack()
         .rename("rho").reset_index().sort_values("rho", ascending=False))
print("\nPares más redundantes:")
print(pares.head(8).round(2).to_string(index=False))

# ---------------------------------------------------------------------------
# 5. Prueba: agrupar amenities redundantes en una sola variable
# ---------------------------------------------------------------------------
GRUPO = ["pileta", "gimnasio", "salon_de_usos_multiples", "parrilla"]


def rho_controlado(x):
    x_res = residualizar(intra(x), controles)
    y_res = residualizar(y_intra, controles)
    comunes = x_res.index.intersection(y_res.index)
    return spearmanr(x_res[comunes], y_res[comunes])[0]


edificio_amenities = comp[GRUPO].fillna(0).max(axis=1)  # 1 si tiene al menos uno
print(f"\nedificio_amenities: {100 * edificio_amenities.mean():.1f}% de los avisos, "
      f"rho controlado = {rho_controlado(edificio_amenities):.3f}")

tabla2 = tabla[~tabla["componente"].isin(GRUPO)][["bloque", "componente", "rho_ctrl_m2_antig"]].copy()
tabla2.loc[len(tabla2)] = ["amenities", "edificio_amenities", rho_controlado(edificio_amenities)]
tabla2["peso"] = np.where(tabla2["rho_ctrl_m2_antig"] > UMBRAL, tabla2["rho_ctrl_m2_antig"], 0)
tabla2["peso"] = tabla2["peso"] / tabla2["peso"].sum()
comparacion = pd.DataFrame({
    "componentes_separados": pesos_bloque,
    "amenities_agrupados": tabla2.groupby("bloque")["peso"].sum().round(3),
})
print("\nPesos por bloque:")
print(comparacion)
