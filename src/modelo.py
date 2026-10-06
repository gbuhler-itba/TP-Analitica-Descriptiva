"""
Modelo de precio esperado (regresión hedónica) y brecha de precio.

El precio esperado de un aviso se estima con una regresión lineal del
logaritmo del precio por m² sobre las características del departamento y su
zona de referencia. Se estima fuera de muestra (validación cruzada en k
partes): el precio esperado de cada aviso sale de un modelo que no lo vio.
Solo usa numpy y pandas.
"""

import numpy as np
import pandas as pd

from src.eda import error_vara_fuera_de_muestra

# Variables de la ficha que entran como "tiene / no tiene" (columna con "Sí")
AMENITIES_Y_EXTRAS = [
    "pileta", "gimnasio", "salon_de_usos_multiples", "seguridad", "parrilla",
    "balcon", "terraza", "dormitorio_en_suite", "aire_acondicionado",
    "ascensor", "apto_profesional",
]

# Tramos de antigüedad (el último tramo, más de 70 años, queda como base)
TRAMOS_ANTIGUEDAD = [(0, 5), (6, 15), (16, 30), (31, 50), (51, 70)]


# ---------------------------------------------------------------------------
# Zona de referencia
# ---------------------------------------------------------------------------
def barrios_donde_conviene_subzona(df, k=5, minimo_grupo=10, semilla=42):
    """Barrios en los que la mediana de la sub-zona predice el precio por m²
    mejor que la del barrio (error fuera de muestra, como en el notebook 02)."""
    geo = df[df["subzona"].notna()]
    e_barrio = error_vara_fuera_de_muestra(geo["precio_m2_usd"], geo["barrio"], k, minimo_grupo, semilla)
    e_sub = error_vara_fuera_de_muestra(geo["precio_m2_usd"], geo["subzona"], k, minimo_grupo, semilla)
    ok = e_barrio.notna() & e_sub.notna()
    tabla = pd.DataFrame({
        "barrio": geo.loc[ok, "barrio"],
        "error_barrio": e_barrio[ok],
        "error_subzona": e_sub[ok],
    }).groupby("barrio").median()
    tabla["conviene_subzona"] = tabla["error_subzona"] < tabla["error_barrio"]
    return tabla


def zona_de_referencia(df, barrios_subzona, minimo_grupo=10):
    """Sub-zona en los barrios donde conviene y el aviso tiene sub-zona;
    barrio en el resto. Zonas con menos de `minimo_grupo` avisos vuelven al barrio."""
    usa_sub = df["barrio"].isin(barrios_subzona) & df["subzona"].notna()
    zona = df["subzona"].where(usa_sub, df["barrio"])
    chica = zona.map(zona.value_counts()) < minimo_grupo
    return zona.where(~chica, df["barrio"])


# ---------------------------------------------------------------------------
# Características
# ---------------------------------------------------------------------------
def _si(serie):
    return (serie == "Sí").astype(float)


def matriz_caracteristicas(df):
    """Características del departamento, sin ninguna variable derivada del precio.

    Faltantes: la antigüedad y el piso sin dato tienen su propia categoría;
    los ambientes sin dato se completan con dormitorios + 1.
    """
    X = pd.DataFrame(index=df.index)
    X["log_m2"] = np.log(df["m2_final"])
    X["ambientes"] = df["ambientes"].fillna(df["dormitorios"] + 1).clip(upper=6)
    X["banos"] = df["banos"].clip(upper=4)
    X["cochera"] = (df["cocheras"].fillna(0) > 0).astype(float)

    ant = df["antiguedad"]
    for lo, hi in TRAMOS_ANTIGUEDAD:
        X[f"antiguedad_{lo}_{hi}"] = ant.between(lo, hi).astype(float)
    X["antiguedad_sin_dato"] = ant.isna().astype(float)

    piso = df["numero_de_piso_de_la_unidad"]
    X["piso"] = piso.clip(upper=20).fillna(0)
    X["piso_sin_dato"] = piso.isna().astype(float)
    X["contrafrente"] = (df["disposicion"] == "Contrafrente").astype(float)

    for c in AMENITIES_Y_EXTRAS:
        X[c] = _si(df[c])
    X["apto_credito"] = _si(df["apto_credito"])
    return X


def matriz_diseno(X, zona):
    """Constante + características + una columna por zona (la primera queda como base)."""
    dummies = pd.get_dummies(zona, prefix="zona", drop_first=True, dtype=float)
    A = pd.concat([X, dummies], axis=1)
    A.insert(0, "constante", 1.0)
    return A


# ---------------------------------------------------------------------------
# Validación cruzada agrupada
# ---------------------------------------------------------------------------
def grupo_de_unidad(df):
    """Misma dirección y misma superficie = misma unidad (o unidad gemela).
    Sin dirección, cada aviso es su propio grupo."""
    clave = df["dir_limpia"].fillna(df["id_aviso"]) + "|" + df["m2_final"].astype(str)
    return pd.Series(pd.factorize(clave)[0], index=df.index)


def folds_agrupados(grupos, k=5, semilla=42):
    """Asigna cada grupo entero a una de k partes, para que un posible
    duplicado nunca esté a la vez en entrenamiento y en prueba."""
    rng = np.random.default_rng(semilla)
    parte_del_grupo = rng.permutation(grupos.max() + 1) % k
    return pd.Series(parte_del_grupo[grupos.values], index=grupos.index)


def precio_esperado_fuera_de_muestra(y, A, zona, folds, entrena_con=None):
    """Para cada parte, ajusta en las otras y predice en ella.

    `entrena_con`: máscara opcional de avisos que pueden usarse para ajustar
    (por ejemplo, sin outliers). La predicción se hace para todos.
    Devuelve (log del precio esperado por el modelo, log de la mediana de la zona).
    """
    if entrena_con is None:
        entrena_con = pd.Series(True, index=y.index)
    modelo = pd.Series(np.nan, index=y.index)
    base = pd.Series(np.nan, index=y.index)
    for p in sorted(folds.unique()):
        prueba = folds == p
        entrena = ~prueba & entrena_con
        coef, *_ = np.linalg.lstsq(A[entrena].values, y[entrena].values, rcond=None)
        modelo[prueba] = A[prueba].values @ coef
        medianas = np.exp(y[entrena]).groupby(zona[entrena]).median()
        global_ = np.exp(y[entrena]).median()
        base[prueba] = np.log(zona[prueba].map(medianas).fillna(global_))
    return modelo, base


def ajustar(y, A, usar=None):
    """Coeficientes del modelo ajustado con todos los avisos de `usar`."""
    if usar is None:
        usar = pd.Series(True, index=y.index)
    coef, *_ = np.linalg.lstsq(A[usar].values, y[usar].values, rcond=None)
    return pd.Series(coef, index=A.columns)


def prima_porcentual(coef):
    """Coeficiente en log -> diferencia porcentual de precio por m²."""
    return 100 * (np.exp(coef) - 1)
