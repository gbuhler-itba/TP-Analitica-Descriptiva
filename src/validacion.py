"""
Validación y comparación de modelos de precio esperado (PreEntrega 3, notebook 04).

Todas las funciones usan las mismas vueltas de validación cruzada sin fuga de
información (`modelo.vueltas_sin_fuga`), así los modelos se comparan sobre
exactamente los mismos avisos de prueba.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import adjusted_rand_score

from src import modelo
from src.limpieza import estado_y_riesgo_del_titulo

MODELOS = ["mediana_zona", "lineal", "lineal_ampliado", "ridge", "gbm"]


def caracteristicas_ampliadas(df, reglas_titulo=None):
    """Características del modelo lineal más el estado del inmueble según el título.

    El estado ("a reciclar", "a refaccionar", "ya reformado", "a estrenar"; base:
    sin marca) y las señales "con inquilino" y "casa" / "tipo casa" recogen lo que
    la ficha no informa. Las reglas salen de config/costos.yaml (corregidas en la
    PreEntrega 3: la marca de la PreEntrega 2 tomaba "refaccionado" como "a
    refaccionar"). Las expensas relativas a la zona se agregan dentro de cada
    vuelta, porque la zona depende de la vuelta.
    """
    if reglas_titulo is None:
        reglas_titulo = cargar_reglas_titulo()
    X = modelo.matriz_caracteristicas(df)
    marcas = estado_y_riesgo_del_titulo(df["titulo"], reglas_titulo)
    estado = pd.get_dummies(marcas["estado_titulo"], prefix="titulo", dtype=float)
    estado = estado.drop(columns="titulo_sin_marca", errors="ignore")
    extra = pd.DataFrame({
        "titulo_con_inquilino": marcas["riesgo_con_inquilino"].astype(float),
        "titulo_casa": df["titulo_casa"].astype(float),
        "titulo_tipo_casa": df["titulo_tipo_casa"].astype(float),
    }, index=df.index)
    return pd.concat([X, estado, extra], axis=1)


def cargar_reglas_titulo():
    """Reglas de estado y riesgo legal del título (config/costos.yaml)."""
    import yaml
    from src.rutas import resolver
    with open(resolver("config/costos.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _expensas_relativas(df, zona, ajusta):
    """Log de expensas por m² menos la mediana de su zona, con medianas de entrenamiento.
    Sin dato = 0 (típico de la zona), con su propia marca."""
    log_exp = np.log(df["expensas_usd"] / df["m2_final"])
    mediana = log_exp[ajusta].groupby(zona[ajusta]).median()
    relativa = (log_exp - zona.map(mediana)).fillna(0)
    return relativa, log_exp.isna().astype(float)


def comparar_modelos(df, y, k=5, semilla=42, minimo_grupo=10, iqr_k=1.5, alpha_ridge=1.0):
    """Predicción fuera de muestra (log del precio por m²) de cada modelo, con las mismas vueltas.

    - mediana_zona: la referencia simple, la mediana de la zona.
    - lineal: el modelo hedónico de la PreEntrega 2 (características + zona).
    - lineal_ampliado: más las marcas del título y las expensas relativas.
    - ridge: el ampliado con regularización L2.
    - gbm: gradient boosting con las mismas características más latitud,
      longitud, barrio y la mediana de la zona; capta interacciones y
      no linealidades, pero no da primas interpretables.
    Devuelve (DataFrame de predicciones, Serie con la vuelta de cada aviso).
    """
    X = modelo.matriz_caracteristicas(df)
    Xa = caracteristicas_ampliadas(df)
    pred = pd.DataFrame(np.nan, index=df.index, columns=MODELOS)
    vuelta = pd.Series(-1, index=df.index)
    barrio_cod = df["barrio"].astype("category").cat.codes
    for p, prueba, ajusta, zona in modelo.vueltas_sin_fuga(df, y, k, semilla, minimo_grupo, iqr_k):
        vuelta[prueba] = p
        precio = np.exp(y[ajusta])
        mediana = precio.groupby(zona[ajusta]).median()
        pred.loc[prueba, "mediana_zona"] = np.log(zona[prueba].map(mediana).fillna(precio.median())).values

        exp_rel, exp_nan = _expensas_relativas(df, zona, ajusta)
        Xb = Xa.assign(expensas_rel_zona=exp_rel, expensas_sin_dato=exp_nan)
        for nombre, XX in [("lineal", X), ("lineal_ampliado", Xb)]:
            A = modelo.matriz_diseno(XX, zona)
            coef, *_ = np.linalg.lstsq(A[ajusta].values, y[ajusta].values, rcond=None)
            pred.loc[prueba, nombre] = A[prueba].values @ coef

        A = modelo.matriz_diseno(Xb, zona).drop(columns="constante")
        ridge = Ridge(alpha=alpha_ridge).fit(A[ajusta].values, y[ajusta].values)
        pred.loc[prueba, "ridge"] = ridge.predict(A[prueba].values)

        G = Xb.assign(lat=df["lat"], lon=df["lon"], barrio=barrio_cod,
                      zona_log_mediana=np.log(zona.map(mediana)))
        gbm = HistGradientBoostingRegressor(
            max_iter=600, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20,
            categorical_features=[G.columns.get_loc("barrio")], random_state=semilla,
        ).fit(G[ajusta].values, y[ajusta].values)
        pred.loc[prueba, "gbm"] = gbm.predict(G[prueba].values)
    return pred, vuelta


def metricas(y, pred, umbral=-0.25):
    """Error porcentual absoluto (mediana, p75, % dentro de ±10%) y avisos marcados por modelo."""
    filas = {}
    for m in pred.columns:
        brecha = np.exp(y - pred[m]) - 1
        error = brecha.abs()
        filas[m] = {
            "error_mediano_%": 100 * error.median(),
            "error_p75_%": 100 * error.quantile(0.75),
            "dentro_de_10%_%": 100 * (error < 0.10).mean(),
            "marcados": int((brecha < umbral).sum()),
        }
    return pd.DataFrame(filas).T


def bootstrap_diferencia_error(y, pred_a, pred_b, unidad, b=500, semilla=42):
    """IC 95% de la diferencia de error mediano (a - b, en puntos porcentuales), remuestreando unidades."""
    err_a = (np.exp(y - pred_a) - 1).abs().values
    err_b = (np.exp(y - pred_b) - 1).abs().values
    grupos = pd.Series(np.arange(len(y))).groupby(unidad.values).apply(np.array).values
    rng = np.random.default_rng(semilla)
    difs = []
    for _ in range(b):
        idx = np.concatenate(grupos[rng.integers(0, len(grupos), len(grupos))])
        difs.append(np.median(err_a[idx]) - np.median(err_b[idx]))
    puntual = np.median(err_a) - np.median(err_b)
    return 100 * puntual, 100 * np.percentile(difs, 2.5), 100 * np.percentile(difs, 97.5)


def jaccard(a, b):
    """Coincidencia entre dos conjuntos de avisos marcados (intersección / unión)."""
    return (a & b).sum() / (a | b).sum()


def intervalos_conformes(residuo, grupo, vuelta, nivel=0.90, minimo=50):
    """Intervalo de predicción por aviso con conformal cruzado.

    Para los avisos de cada vuelta, los cuantiles salen de los residuos fuera
    de muestra de las OTRAS vueltas, dentro de su grupo (barrio) si tiene al
    menos `minimo` avisos, y de toda la ciudad si no. Devuelve (límite
    inferior, límite superior) en escala log, para sumar a la predicción.
    """
    a = (1 - nivel) / 2
    inf = pd.Series(np.nan, index=residuo.index)
    sup = inf.copy()
    for p in sorted(vuelta.unique()):
        prueba = vuelta == p
        otras = ~prueba
        r = residuo[otras]
        q = r.groupby(grupo[otras]).quantile([a, 1 - a]).unstack()
        n = r.groupby(grupo[otras]).size()
        q = q[n >= minimo]
        ciudad = r.quantile([a, 1 - a]).values
        inf[prueba] = grupo[prueba].map(q[a]).fillna(ciudad[0]).values
        sup[prueba] = grupo[prueba].map(q[1 - a]).fillna(ciudad[1]).values
    return inf, sup


def estabilidad_subzonas(df, repeticiones=20, fraccion=0.8, semilla=0):
    """Estabilidad de las sub-zonas de cada barrio (k-means sobre latitud y longitud).

    Repite el k-means con la misma cantidad de sub-zonas sobre submuestras del
    80% de los avisos y otra semilla, asigna todos los avisos y compara con las
    sub-zonas originales con el índice de Rand ajustado (ARI: 1 = idénticas,
    0 = coincidencia al azar).
    """
    geo = df[df["subzona"].notna() & df["lat"].notna()]
    rng = np.random.default_rng(semilla)
    filas = []
    for barrio, g in geo.groupby("barrio"):
        k = g["subzona"].nunique()
        if k < 2:
            continue
        coords = g[["lat", "lon"]].values
        aris = []
        for r in range(repeticiones):
            idx = rng.choice(len(coords), int(fraccion * len(coords)), replace=False)
            km = KMeans(n_clusters=k, n_init=10, random_state=r).fit(coords[idx])
            aris.append(adjusted_rand_score(g["subzona"].values, km.predict(coords)))
        filas.append({"barrio": barrio, "avisos": len(g), "subzonas": k,
                      "ari_mediano": np.median(aris), "ari_p10": np.percentile(aris, 10)})
    return pd.DataFrame(filas).set_index("barrio").sort_values("ari_mediano")


def bootstrap_primas(y, A, usar, unidad, columnas, b=200, semilla=42):
    """IC 95% de las primas (%) del modelo lineal, remuestreando unidades (no avisos)."""
    Av, yv = A[usar].values, y[usar].values
    grupos = pd.Series(np.arange(usar.sum())).groupby(unidad[usar].values).apply(np.array).values
    pos = [A.columns.get_loc(c) for c in columnas]
    rng = np.random.default_rng(semilla)
    muestras = []
    for _ in range(b):
        idx = np.concatenate(grupos[rng.integers(0, len(grupos), len(grupos))])
        coef, *_ = np.linalg.lstsq(Av[idx], yv[idx], rcond=None)
        muestras.append(coef[pos])
    muestras = modelo.prima_porcentual(np.array(muestras))
    coef, *_ = np.linalg.lstsq(Av, yv, rcond=None)
    return pd.DataFrame({
        "prima_%": modelo.prima_porcentual(coef[pos]),
        "ic_inf_%": np.percentile(muestras, 2.5, axis=0),
        "ic_sup_%": np.percentile(muestras, 97.5, axis=0),
    }, index=columnas)
