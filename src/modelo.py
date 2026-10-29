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
def barrios_donde_conviene_subzona(df, k=5, minimo_grupo=10, semilla=42, por_unidad=False):
    """Barrios en los que la mediana de la sub-zona predice el precio por m²
    mejor que la del barrio (error fuera de muestra, como en el notebook 02).

    `por_unidad=True` arma las partes por unidad (misma dirección y superficie),
    para que un posible duplicado no quede a la vez en entrenamiento y prueba."""
    geo = df[df["subzona"].notna()]
    unidad = grupo_de_unidad(geo) if por_unidad else None
    e_barrio = error_vara_fuera_de_muestra(geo["precio_m2_usd"], geo["barrio"], k, minimo_grupo, semilla, unidad)
    e_sub = error_vara_fuera_de_muestra(geo["precio_m2_usd"], geo["subzona"], k, minimo_grupo, semilla, unidad)
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
    los ambientes sin dato se completan con dormitorios + 1, y los baños sin
    dato con 1 (el mínimo posible), con una marca propia.
    """
    X = pd.DataFrame(index=df.index)
    X["log_m2"] = np.log(df["m2_final"])
    X["ambientes"] = df["ambientes"].fillna(df["dormitorios"] + 1).clip(upper=6)
    # Baños sin dato: todo departamento tiene al menos uno, se completa con 1 y se marca
    X["banos"] = df["banos"].fillna(1).clip(upper=4)
    X["banos_sin_dato"] = df["banos"].isna().astype(float)
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


# ---------------------------------------------------------------------------
# Validación cruzada sin fuga de información (PreEntrega 3)
# ---------------------------------------------------------------------------
def vueltas_sin_fuga(df, y, k=5, semilla=42, minimo_grupo=10, iqr_k=1.5, atipicos_en_log=True,
                     barrios_excluidos=()):
    """Genera, para cada vuelta de la validación cruzada, las decisiones tomadas SOLO con entrenamiento.

    En la PreEntrega 2 dos decisiones se tomaban con todos los avisos antes de
    la validación cruzada: qué barrios usan sub-zona y qué avisos son atípicos
    (y quedan fuera del ajuste). Eso deja que los avisos de prueba influyan en
    el modelo que los evalúa. Acá, en cada vuelta y solo con los avisos de
    entrenamiento:
      1. se eligen los barrios donde conviene la sub-zona (partes por unidad);
      2. se arma la zona de referencia;
      3. se marcan los atípicos con IQR sobre el logaritmo del precio por m²,
         dentro de la zona, y se dejan fuera del ajuste.
    Las partes se arman por unidad (misma dirección y superficie).

    `atipicos_en_log=False` reproduce el criterio de la PreEntrega 2 (IQR sobre
    el precio por m², que solo detecta la cola de arriba), para comparar.
    `barrios_excluidos`: barrios que nunca usan sub-zona (por ejemplo, los de
    sub-zonas inestables).

    Devuelve tuplas (vuelta, prueba, ajusta, zona): máscaras booleanas de prueba
    y de avisos que entran al ajuste, y la zona de referencia de cada aviso.
    """
    from src.limpieza import outliers_iqr_por_grupo

    folds = folds_agrupados(grupo_de_unidad(df), k, semilla)
    for p in sorted(folds.unique()):
        prueba = folds == p
        entrena = ~prueba
        tabla = barrios_donde_conviene_subzona(df[entrena], k, minimo_grupo, semilla, por_unidad=True)
        barrios_sub = [b for b in tabla.index[tabla["conviene_subzona"]] if b not in set(barrios_excluidos)]

        # Zona con los conteos de entrenamiento: una sub-zona chica en entrenamiento vuelve al barrio
        usa_sub = df["barrio"].isin(barrios_sub) & df["subzona"].notna()
        zona = df["subzona"].where(usa_sub, df["barrio"])
        conteo = zona[entrena].value_counts()
        zona = zona.where(zona.map(conteo).fillna(0) >= minimo_grupo, df["barrio"])

        escala = y if atipicos_en_log else np.exp(y)
        atipico = outliers_iqr_por_grupo(escala[entrena], zona[entrena], k=iqr_k, minimo_grupo=minimo_grupo)
        ajusta = entrena.copy()
        ajusta[entrena] = ~atipico.values
        yield p, prueba, ajusta, zona


def precio_esperado_sin_fuga(df, y, X, k=5, semilla=42, minimo_grupo=10, iqr_k=1.5, atipicos_en_log=True,
                             barrios_excluidos=()):
    """Precio esperado fuera de muestra con el modelo hedónico lineal, sin fuga de información
    (ver `vueltas_sin_fuga`).

    Devuelve un DataFrame con, para cada aviso: log del precio esperado, log de
    la mediana de su zona (referencia simple), la zona usada y la vuelta.
    """
    salida = pd.DataFrame(index=df.index, columns=["log_esperado", "log_mediana_zona", "zona", "vuelta"])
    for p, prueba, ajusta, zona in vueltas_sin_fuga(df, y, k, semilla, minimo_grupo, iqr_k, atipicos_en_log,
                                                    barrios_excluidos):
        A = matriz_diseno(X, zona)
        coef, *_ = np.linalg.lstsq(A[ajusta].values, y[ajusta].values, rcond=None)
        salida.loc[prueba, "log_esperado"] = A[prueba].values @ coef
        medianas = np.exp(y[ajusta]).groupby(zona[ajusta]).median()
        global_ = np.exp(y[ajusta]).median()
        salida.loc[prueba, "log_mediana_zona"] = np.log(zona[prueba].map(medianas).fillna(global_)).values
        salida.loc[prueba, "zona"] = zona[prueba].values
        salida.loc[prueba, "vuelta"] = p
    salida["log_esperado"] = salida["log_esperado"].astype(float)
    salida["log_mediana_zona"] = salida["log_mediana_zona"].astype(float)
    return salida
