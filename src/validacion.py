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


def comparar_modelos(df, y, k=5, semilla=42, minimo_grupo=10, iqr_k=1.5, alpha_ridge=1.0, modelos=None,
                     barrios_excluidos=(), devolver_modelos=False):
    """Predicción fuera de muestra (log del precio por m²) de cada modelo, con las mismas vueltas.

    - mediana_zona: la referencia simple, la mediana de la zona.
    - lineal: el modelo hedónico de la PreEntrega 2 (características + zona).
    - lineal_ampliado: más las marcas del título y las expensas relativas.
    - ridge: el ampliado con regularización L2.
    - gbm: gradient boosting con las mismas características más latitud,
      longitud, barrio y la mediana de la zona; capta interacciones y
      no linealidades, pero no da primas interpretables.
    `modelos`: subconjunto de MODELOS a calcular (por defecto, todos).
    `barrios_excluidos`: barrios que nunca usan sub-zona (sub-zonas inestables).
    Devuelve (DataFrame de predicciones, Serie con la vuelta de cada aviso).

    `devolver_modelos=True` agrega un tercer elemento: un diccionario por vuelta
    con las máscaras (`prueba`, `ajusta`), la `zona`, y para cada modelo
    calculado su ajuste: `coef_lineal_ampliado` con su matriz `Xb`, y `gbm` con
    su matriz `G`. Las matrices son por vuelta porque las expensas relativas y la
    mediana de la zona dependen de la vuelta. Sirve para explicar las
    predicciones (`explicar_lineal`, `explicar_gbm`).
    """
    modelos = list(modelos) if modelos is not None else MODELOS
    X = modelo.matriz_caracteristicas(df)
    Xa = caracteristicas_ampliadas(df)
    pred = pd.DataFrame(np.nan, index=df.index, columns=modelos)
    vuelta = pd.Series(-1, index=df.index)
    barrio_cod = df["barrio"].astype("category").cat.codes
    zonas = pd.Series(np.nan, index=df.index, dtype="object")
    ajustes = {}
    for p, prueba, ajusta, zona in modelo.vueltas_sin_fuga(df, y, k, semilla, minimo_grupo, iqr_k,
                                                         barrios_excluidos=barrios_excluidos):
        vuelta[prueba] = p
        zonas[prueba] = zona[prueba]
        ajustes[p] = {"prueba": prueba, "ajusta": ajusta, "zona": zona}
        precio = np.exp(y[ajusta])
        mediana = precio.groupby(zona[ajusta]).median()
        if "mediana_zona" in modelos:
            pred.loc[prueba, "mediana_zona"] = np.log(zona[prueba].map(mediana).fillna(precio.median())).values

        exp_rel, exp_nan = _expensas_relativas(df, zona, ajusta)
        Xb = Xa.assign(expensas_rel_zona=exp_rel, expensas_sin_dato=exp_nan)
        for nombre, XX in [("lineal", X), ("lineal_ampliado", Xb)]:
            if nombre not in modelos:
                continue
            A = modelo.matriz_diseno(XX, zona)
            coef, *_ = np.linalg.lstsq(A[ajusta].values, y[ajusta].values, rcond=None)
            pred.loc[prueba, nombre] = A[prueba].values @ coef
            if nombre == "lineal_ampliado":
                ajustes[p].update(coef_lineal_ampliado=pd.Series(coef, index=A.columns), Xb=Xb)

        if "ridge" in modelos:
            A = modelo.matriz_diseno(Xb, zona).drop(columns="constante")
            ridge = Ridge(alpha=alpha_ridge).fit(A[ajusta].values, y[ajusta].values)
            pred.loc[prueba, "ridge"] = ridge.predict(A[prueba].values)
        if "gbm" not in modelos:
            continue

        G = Xb.assign(lat=df["lat"], lon=df["lon"], barrio=barrio_cod,
                      zona_log_mediana=np.log(zona.map(mediana)))
        gbm = HistGradientBoostingRegressor(
            max_iter=600, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=20,
            categorical_features=[G.columns.get_loc("barrio")], random_state=semilla,
        ).fit(G[ajusta].values, y[ajusta].values)
        pred.loc[prueba, "gbm"] = gbm.predict(G[prueba].values)
        ajustes[p].update(gbm=gbm, G=G)
    pred.attrs["zona"] = zonas
    if devolver_modelos:
        return pred, vuelta, ajustes
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


# ---------------------------------------------------------------------------
# Explicación de las predicciones (PreEntrega 3)
# ---------------------------------------------------------------------------
# Columnas que se explican juntas, como una sola variable: cada dato con su marca
# de "sin dato" y la ubicación del gradient boosting. Por separado arman
# combinaciones imposibles (piso 0 sin la marca de sin dato, una latitud de un
# barrio con la longitud de otro). Los tramos de antigüedad y el estado del
# título (categorías de una misma variable) también van juntos.
VARIABLES_AGRUPADAS = {
    "banos": ["banos", "banos_sin_dato"],
    "piso": ["piso", "piso_sin_dato"],
    "expensas": ["expensas_rel_zona", "expensas_sin_dato"],
    "ubicacion": ["lat", "lon", "barrio", "zona_log_mediana"],
}
SENALES_DEL_TITULO = ["titulo_con_inquilino", "titulo_casa", "titulo_tipo_casa"]

ETIQUETAS = {
    "log_m2": "Superficie", "ambientes": "Ambientes", "banos": "Baños", "cochera": "Cochera",
    "antiguedad": "Antigüedad", "piso": "Piso", "contrafrente": "Contrafrente", "pileta": "Pileta",
    "gimnasio": "Gimnasio", "salon_de_usos_multiples": "SUM", "seguridad": "Seguridad", "parrilla": "Parrilla",
    "balcon": "Balcón", "terraza": "Terraza", "dormitorio_en_suite": "Dormitorio en suite",
    "aire_acondicionado": "Aire acondicionado", "ascensor": "Ascensor", "apto_profesional": "Apto profesional",
    "apto_credito": "Apto crédito", "estado_titulo": "Estado según el título",
    "titulo_con_inquilino": "Con inquilino (título)", "titulo_casa": "Casa (título)",
    "titulo_tipo_casa": "Tipo casa (título)", "expensas": "Expensas frente a la zona", "ubicacion": "Ubicación",
}


def variables_del_modelo(columnas):
    """Agrupa las columnas de la matriz del modelo en variables: {variable: [columnas]}."""
    variables = {}
    for c in columnas:
        nombre = next((v for v, cols in VARIABLES_AGRUPADAS.items() if c in cols), c)
        if c.startswith("antiguedad_"):
            nombre = "antiguedad"
        elif c.startswith("titulo_") and c not in SENALES_DEL_TITULO:
            nombre = "estado_titulo"
        variables.setdefault(nombre, []).append(c)
    return variables


def explicar_lineal(ajustes, avisos):
    """Contribuciones exactas del lineal ampliado al log del precio esperado, por variable.

    Cada aviso se explica con los coeficientes de la vuelta que no lo vio:
    contribución = coeficiente × (valor del aviso − valor medio de su zona entre
    los avisos de entrenamiento). La referencia (`base`) es el log del precio
    esperado de un aviso con las características medias de su zona, así que
    base + suma de las contribuciones = log del precio esperado, exacto. Es el
    SHAP de un modelo lineal con los avisos de la zona como fondo.

    `ajustes`: el tercer elemento de `comparar_modelos(..., devolver_modelos=True)`.
    `avisos`: máscara booleana de los avisos a explicar.
    Devuelve un DataFrame (avisos × variables) más las columnas `base` y `vuelta`.
    """
    partes = []
    for p, aj in ajustes.items():
        sel = avisos & aj["prueba"]
        if not sel.any():
            continue
        Xb, coef, zona, ajusta = aj["Xb"], aj["coef_lineal_ampliado"], aj["zona"], aj["ajusta"]
        media_zona = Xb[ajusta].groupby(zona[ajusta]).mean()
        referencia = media_zona.reindex(zona[sel].values).set_axis(Xb.index[sel]).fillna(Xb[ajusta].mean())
        dif = (Xb[sel] - referencia) * coef[Xb.columns]
        A = modelo.matriz_diseno(Xb, zona)
        esperado = A[sel].values @ coef[A.columns].values
        parte = pd.DataFrame({v: dif[cols].sum(axis=1) for v, cols in variables_del_modelo(Xb.columns).items()})
        parte["base"] = esperado - parte.sum(axis=1)
        parte["vuelta"] = p
        partes.append(parte)
    return pd.concat(partes).loc[avisos[avisos].index]


def _shap_por_permutacion(predecir, fondo, x, columnas, max_evals=300, semilla=42):
    """Valores SHAP de `predecir` por variable (grupos de columnas), con el explicador por permutación de shap.

    Cada variable se representa por el número de fila de donde toma sus
    columnas: el aviso explicado o una fila del fondo. Así las columnas de una
    variable se reemplazan siempre juntas por las de un mismo aviso del fondo.
    Devuelve (valores: avisos × variables, base: predicción media del fondo).
    """
    import shap

    filas = np.vstack([fondo, x])
    n_fondo, n_var = len(fondo), len(columnas)

    def f(z):
        z = z.astype(int)
        m = np.empty((len(z), filas.shape[1]))
        for v, cols in enumerate(columnas):
            m[:, cols] = filas[z[:, v]][:, cols]
        return predecir(m)

    ids_fondo = np.repeat(np.arange(n_fondo)[:, None], n_var, axis=1)
    ids_x = np.repeat(np.arange(n_fondo, n_fondo + len(x))[:, None], n_var, axis=1)
    masker = shap.maskers.Independent(ids_fondo, max_samples=n_fondo)
    explicador = shap.explainers.Permutation(f, masker, seed=semilla)
    res = explicador(ids_x, max_evals=max(max_evals, 2 * n_var + 1), silent=True)
    return res.values, res.base_values


def explicar_gbm(ajustes, avisos, fondo="ciudad", n_fondo=50, max_evals=300, semilla=42):
    """Valores SHAP del gradient boosting en log del precio esperado, por variable.

    El TreeExplainer de shap no reproduce bien los cortes por categoría nativos
    del HistGradientBoosting (la suma de los valores no da la predicción), así
    que se usa el explicador por permutación, que solo necesita la función de
    predicción. Cada aviso se explica con el modelo de la vuelta que no lo vio.

    `fondo`: contra qué se compara el aviso.
      - "ciudad": `n_fondo` avisos al azar del entrenamiento de la vuelta
        (la ubicación aparece como una variable más);
      - "zona": hasta `n_fondo` avisos de entrenamiento de su misma zona (la
        base es el precio esperado típico de la zona, como en `explicar_lineal`).
    base + suma de los valores = log del precio esperado (exacto, por
    construcción del explicador por permutación). Con 50 avisos de fondo y 300
    evaluaciones tarda unos 0,17 s por aviso; el notebook 04 (sección 9) mide
    cuánto cambian los valores con un fondo y una cantidad de evaluaciones mayores.
    Devuelve un DataFrame (avisos × variables) más las columnas `base` y `vuelta`.
    """
    rng = np.random.default_rng(semilla)
    partes = []
    for p, aj in ajustes.items():
        sel = avisos & aj["prueba"]
        if not sel.any():
            continue
        G, gbm, zona, ajusta = aj["G"], aj["gbm"], aj["zona"], aj["ajusta"]
        variables = variables_del_modelo(G.columns)
        columnas = [[G.columns.get_loc(c) for c in cols] for cols in variables.values()]
        grupos = zona[sel].groupby(zona[sel]).groups if fondo == "zona" else {None: sel[sel].index}
        for z, idx in grupos.items():
            pozo = ajusta & (zona == z) if z is not None else ajusta
            if not pozo.any():
                pozo = ajusta
            elegidos = rng.choice(pozo[pozo].index, size=min(n_fondo, int(pozo.sum())), replace=False)
            valores, base = _shap_por_permutacion(gbm.predict, G.loc[elegidos].values, G.loc[idx].values,
                                                  columnas, max_evals, semilla)
            parte = pd.DataFrame(valores, index=idx, columns=list(variables))
            parte["base"] = base
            parte["vuelta"] = p
            partes.append(parte)
    return pd.concat(partes).loc[avisos[avisos].index]


def explicar_gbm_guardado(ajustes, avisos, ruta, id_aviso, prediccion, fondo="ciudad", n_fondo=50, max_evals=300,
                          semilla=42):
    """`explicar_gbm` con los resultados guardados en `ruta` (TSV), porque calcularlos tarda varios minutos.

    Usa el archivo solo si corresponde exactamente a este cálculo: los mismos
    avisos (`id_aviso`), los mismos parámetros y referencia + suma de los
    valores = `prediccion` (log del precio esperado del gradient boosting). Si
    cambian los datos, el modelo o la plataforma (el gradient boosting puede
    variar entre plataformas), la suma deja de coincidir y se recalcula.
    Devuelve (DataFrame como el de `explicar_gbm`, "leído" o "calculado").
    """
    from src.rutas import asegurar_directorio, resolver

    ruta = resolver(ruta)
    parametros = {"fondo": fondo, "n_fondo": n_fondo, "max_evals": max_evals, "semilla": semilla}
    ids = id_aviso[avisos]
    if ruta.exists():
        guardado = pd.read_csv(ruta, sep="\t")
        param_ok = all(f"param_{k}" in guardado.columns and str(guardado[f"param_{k}"].iloc[0]) == str(v)
                       for k, v in parametros.items())
        if param_ok and len(guardado) == len(ids) and (guardado["id_aviso"].values == ids.values).all():
            contrib = guardado.drop(columns=["id_aviso"] + [f"param_{k}" for k in parametros]).set_index(ids.index)
            if np.allclose(contrib.drop(columns="vuelta").sum(axis=1), prediccion[avisos], atol=1e-8):
                return contrib, "leído"
    contrib = explicar_gbm(ajustes, avisos, **parametros)
    salida = contrib.assign(**{f"param_{k}": v for k, v in parametros.items()})
    salida.insert(0, "id_aviso", ids.values)
    salida.to_csv(asegurar_directorio(ruta), sep="\t", index=False, float_format="%.17g")
    return contrib, "calculado"


def explicar_modelo(ajustes, avisos, nombre, **kwargs):
    """Explicación por aviso del modelo `nombre` contra su zona: contribuciones exactas
    si es el lineal ampliado, SHAP con fondo de la zona si es el gradient boosting
    (`kwargs` va a `explicar_gbm`; el lineal no lo necesita)."""
    if nombre == "lineal_ampliado":
        return explicar_lineal(ajustes, avisos)
    if nombre == "gbm":
        return explicar_gbm(ajustes, avisos, fondo="zona", **kwargs)
    raise ValueError(f"Modelo sin explicación: {nombre}")
