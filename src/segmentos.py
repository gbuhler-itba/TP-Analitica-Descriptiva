"""
Segmentos exploratorios (PreEntrega 3, notebook 06): índice de equipamiento con
MCA y micro-mercados con K-means.

EXPLORATORIO: nada de este módulo alimenta la etapa 6, la lista oficial ni la
regla de decisión. src/analisis.py no lo importa.
"""

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

# Variables activas del MCA. Las "Sí/No" tienen las dos respuestas en la ficha
# (el vacío es falta de dato); en las "solo Sí" el vacío no distingue "no tiene"
# de "no lo cargó". Quedan afuera playroom, salón de fiestas y roof garden
# (menos del 2% de "Sí": en el MCA las categorías raras inflan la inercia).
COLUMNAS_SI_NO = ["aire_acondicionado", "ascensor", "balcon", "calefaccion", "con_conexion_para_lavarropas",
                  "dormitorio_en_suite", "gas_natural", "lavanderia", "pileta", "seguridad", "terraza"]
COLUMNAS_SOLO_SI = ["gimnasio", "parrilla", "salon_de_usos_multiples", "sauna", "acceso_a_internet",
                    "agua_corriente"]
COLUMNAS_MCA = COLUMNAS_SI_NO + COLUMNAS_SOLO_SI

NOMBRES = {
    "aire_acondicionado": "aire acondicionado", "ascensor": "ascensor", "balcon": "balcón",
    "calefaccion": "calefacción", "con_conexion_para_lavarropas": "conexión para lavarropas",
    "dormitorio_en_suite": "dormitorio en suite", "gas_natural": "gas natural", "lavanderia": "lavandería",
    "pileta": "pileta", "seguridad": "seguridad", "terraza": "terraza", "gimnasio": "gimnasio",
    "parrilla": "parrilla", "salon_de_usos_multiples": "SUM", "sauna": "sauna",
    "acceso_a_internet": "acceso a internet", "agua_corriente": "agua corriente",
}


def nombre_categoria(categoria):
    """'calefaccion__sin dato' -> 'calefacción: sin dato'."""
    columna, _, valor = categoria.partition("__")
    return f"{NOMBRES.get(columna, columna)}: {valor}" if valor else NOMBRES.get(columna, columna)


# ---------------------------------------------------------------------------
# MCA
# ---------------------------------------------------------------------------
def tabla_mca(df, sin_dato="no"):
    """Variables activas del MCA como categorías de texto.

    `sin_dato="no"`: el vacío cuenta como "No" (el índice mide equipamiento,
    pero confunde "no tiene" con "no lo cargó").
    `sin_dato="categoria"`: en las Sí/No el vacío es una categoría propia ("sin
    dato"); en las solo Sí, "no figura".
    """
    if sin_dato == "no":
        return df[COLUMNAS_MCA].fillna("No").astype(str)
    if sin_dato == "categoria":
        return pd.concat([df[COLUMNAS_SI_NO].fillna("sin dato"), df[COLUMNAS_SOLO_SI].fillna("no figura")],
                         axis=1).astype(str)
    raise ValueError(f"sin_dato desconocido: {sin_dato}")


def ajustar_mca(X, n_componentes=5, semilla=42):
    """MCA de prince, como en la clase."""
    import prince
    return prince.MCA(n_components=n_componentes, n_iter=10, random_state=semilla).fit(X)


def indice_mca(mca, X, eje=0):
    """Coordenada de cada aviso en un eje del MCA, con el signo fijado: más alto = más "Sí".

    El signo de un eje es arbitrario; se orienta para que correlacione en
    positivo con la cantidad de "Sí" del aviso.
    """
    coord = mca.row_coordinates(X)[eje]
    cantidad_si = (X == "Sí").sum(axis=1)
    return coord if coord.corr(cantidad_si) >= 0 else -coord


def contribuciones_eje(mca, eje=0):
    """Contribución (%) de cada categoría a un eje, de mayor a menor."""
    return (100 * mca.column_contributions_[eje]).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# K-means
# ---------------------------------------------------------------------------
def variables_kmeans(df, indice):
    """Variables activas del K-means en escala original, con la mediana en los faltantes.

    Características del departamento, no de la ubicación: ambientes, log de m²
    por ambiente (el log de m² correlaciona 0,83 con ambientes y contaría el
    tamaño dos veces), antigüedad, log de expensas por m² e índice de
    equipamiento. Devuelve (variables, máscara de valores imputados).
    """
    ambientes = df["ambientes"].fillna(df["dormitorios"] + 1).clip(lower=1, upper=6)
    V = pd.DataFrame({
        "ambientes": ambientes,
        "log_m2_por_ambiente": np.log(df["m2_final"] / ambientes),
        "antiguedad": df["antiguedad"],
        "log_expensas_m2": np.log(df["expensas_usd"] / df["m2_final"]),
        "indice_equipamiento": indice,
    }, index=df.index)
    imputado = V.isna()
    return V.fillna(V.median()), imputado


def escalar(V, p_inf=0.01, p_sup=0.99):
    """Winsoriza en los percentiles p_inf y p_sup y estandariza (z-score).
    Devuelve (Z, parámetros) para volver a la escala original."""
    lim_inf, lim_sup = V.quantile(p_inf), V.quantile(p_sup)
    W = V.clip(lim_inf, lim_sup, axis=1)
    media, desvio = W.mean(), W.std(ddof=0)
    return (W - media) / desvio, {"media": media, "desvio": desvio}


def a_escala_original(centroides_z, parametros):
    """Centroides en z-score -> escala original (de las variables winsorizadas)."""
    return centroides_z * parametros["desvio"] + parametros["media"]


def ajustar_kmeans(Z, k, semilla=42, n_init=20):
    """K-means++ con varios arranques (n_init) para no quedar en un mínimo local."""
    return KMeans(n_clusters=k, init="k-means++", n_init=n_init, random_state=semilla).fit(Z)


def elegir_k(Z, ks=range(2, 11), semilla=42, n_init=20, muestra_silhouette=5000):
    """Inercia (codo) y silhouette para cada K. La silhouette se calcula sobre una muestra fija."""
    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(Z), min(muestra_silhouette, len(Z)), replace=False)
    filas = []
    for k in ks:
        km = ajustar_kmeans(Z, k, semilla, n_init)
        filas.append({"k": k, "inercia": km.inertia_,
                      "silhouette": silhouette_score(np.asarray(Z)[idx], km.labels_[idx])})
    return pd.DataFrame(filas).set_index("k")


def nombrar_segmentos(centroides, columna_equipamiento="indice_equipamiento"):
    """Nombre de negocio de cada segmento de K = 4 a partir de sus centroides (escala original).

    Regla, para que el nombre no dependa del número de etiqueta del K-means:
    el de más ambientes es "Familiares amplios y antiguos", el de más
    equipamiento "Nuevos con amenities", el de menos ambientes "Chicos y
    recientes", y el que queda "Compactos de edificio antiguo". Si la regla no
    separa los cuatro (por ejemplo, porque cambiaron los datos), falla: hay que
    volver a mirar los centroides y nombrarlos de nuevo.
    """
    if len(centroides) != 4:
        raise ValueError("La regla de nombres está pensada para K = 4.")
    nombres = {
        centroides["ambientes"].idxmax(): "Familiares amplios y antiguos",
        centroides[columna_equipamiento].idxmax(): "Nuevos con amenities",
        centroides["ambientes"].idxmin(): "Chicos y recientes",
    }
    if len(nombres) != 3:
        raise ValueError("La regla de nombres no separa los segmentos: revisar los centroides.")
    resto = [s for s in centroides.index if s not in nombres]
    nombres[resto[0]] = "Compactos de edificio antiguo"
    return nombres


def alinear_etiquetas(referencia, etiquetas, k):
    """Renombra `etiquetas` para que coincidan lo más posible con `referencia` (algoritmo húngaro)."""
    confusion = np.zeros((k, k))
    np.add.at(confusion, (referencia, etiquetas), 1)
    filas, columnas = linear_sum_assignment(-confusion)
    mapa = dict(zip(columnas, filas))
    return np.array([mapa[e] for e in etiquetas])


def estabilidad_kmeans(Z, k, repeticiones=100, fraccion=0.8, semilla=42, n_init=20):
    """Estabilidad de los segmentos con bootstrap, como en la clase.

    En cada repetición se ajusta el K-means sobre el `fraccion` de los avisos,
    con otra semilla, se asignan todos los avisos y se compara con la
    segmentación original: ARI (1 = idénticas) y tamaño de cada segmento
    (con las etiquetas alineadas). Devuelve (ARI por repetición, tamaños en %
    por repetición y segmento, etiquetas originales).
    """
    Z = np.asarray(Z)
    original = ajustar_kmeans(Z, k, semilla, n_init).labels_
    rng = np.random.default_rng(semilla)
    aris, tamanos = [], []
    for r in range(repeticiones):
        idx = rng.choice(len(Z), int(fraccion * len(Z)), replace=False)
        km = ajustar_kmeans(Z[idx], k, semilla + r + 1, n_init)
        etiquetas = alinear_etiquetas(original, km.predict(Z), k)
        aris.append(adjusted_rand_score(original, etiquetas))
        tamanos.append(100 * np.bincount(etiquetas, minlength=k) / len(Z))
    return pd.Series(aris), pd.DataFrame(tamanos), original


# ---------------------------------------------------------------------------
# Utilidad: liquidez, modelo de precio e incertidumbre
# ---------------------------------------------------------------------------
def bootstrap_estadistico(valores, grupos, funcion=np.mean, b=500, semilla=42):
    """Estadístico de `valores` con IC 95%, remuestreando grupos (unidades) y no avisos.
    Devuelve (puntual, límite inferior, límite superior)."""
    v = np.asarray(valores, dtype=float)
    por_grupo = pd.Series(np.arange(len(v))).groupby(np.asarray(grupos)).apply(np.array).values
    rng = np.random.default_rng(semilla)
    muestras = [funcion(v[np.concatenate(por_grupo[rng.integers(0, len(por_grupo), len(por_grupo))])])
                for _ in range(b)]
    return funcion(v), np.percentile(muestras, 2.5), np.percentile(muestras, 97.5)


def probabilidad_fuera_de_muestra(y, X, grupos, k=5, semilla=42):
    """Probabilidad de un logit sin penalización, fuera de muestra, con vueltas agrupadas por unidad.

    `y`: 0/1. `X`: variables explicativas (sin constante; vacío = solo la
    tasa promedio). `grupos`: unidad de cada aviso (enteros desde 0).
    """
    from sklearn.linear_model import LogisticRegression
    from src import modelo

    folds = modelo.folds_agrupados(pd.Series(grupos, index=y.index), k, semilla)
    prob = pd.Series(np.nan, index=y.index)
    for p in sorted(folds.unique()):
        prueba = folds == p
        if X.shape[1] == 0:
            prob[prueba] = y[~prueba].mean()
            continue
        logit = LogisticRegression(penalty=None, max_iter=2000).fit(X[~prueba].values, y[~prueba].values)
        prob[prueba] = logit.predict_proba(X[prueba].values)[:, 1]
    return prob


def log_loss_por_aviso(y, prob):
    """Pérdida logarítmica de cada aviso (más baja = mejor predicción)."""
    p = np.clip(prob, 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def precio_esperado_con_equipamiento(df, y, k=5, semilla=42, minimo_grupo=10, iqr_k=1.5, barrios_excluidos=()):
    """Lineal ampliado fuera de muestra con cuatro formas de incluir el equipamiento, con las mismas vueltas sin fuga.

    - amenities_oficiales: el modelo oficial (las amenities sueltas que usa hoy);
    - sueltas_17: las 17 características activas del MCA, sueltas;
    - conteo: cuántas de esas 17 declara el aviso (alternativa simple);
    - indice_mca: el índice de equipamiento, con el MCA ajustado SOLO con los
      avisos de entrenamiento de cada vuelta (si se ajustara con todos, los de
      prueba influirían en el índice que los evalúa).
    El resto de las variables es el del lineal ampliado. Devuelve el log del
    precio esperado por m² de cada variante.
    """
    from src import modelo, validacion

    Xa = validacion.caracteristicas_ampliadas(df)
    equipo_oficial = [c for c in modelo.AMENITIES_Y_EXTRAS if c != "apto_profesional"]
    base = Xa.drop(columns=equipo_oficial)
    X_mca = tabla_mca(df, "no")
    sueltas = (X_mca == "Sí").astype(float).add_prefix("eq_")
    conteo = sueltas.sum(axis=1)
    pred = pd.DataFrame(np.nan, index=df.index,
                        columns=["amenities_oficiales", "sueltas_17", "conteo", "indice_mca"])
    for _, prueba, ajusta, zona in modelo.vueltas_sin_fuga(df, y, k, semilla, minimo_grupo, iqr_k,
                                                         barrios_excluidos=barrios_excluidos):
        exp_rel, exp_nan = validacion._expensas_relativas(df, zona, ajusta)
        b = base.assign(expensas_rel_zona=exp_rel, expensas_sin_dato=exp_nan)
        mca = ajustar_mca(X_mca[ajusta], semilla=semilla)
        coord = mca.row_coordinates(X_mca)[0]
        indice = coord if coord[ajusta].corr(conteo[ajusta]) >= 0 else -coord
        variantes = {
            "amenities_oficiales": pd.concat([b, Xa[equipo_oficial]], axis=1),
            "sueltas_17": pd.concat([b, sueltas], axis=1),
            "conteo": b.assign(conteo_amenities=conteo),
            "indice_mca": b.assign(indice_equipamiento=indice),
        }
        for nombre, XX in variantes.items():
            A = modelo.matriz_diseno(XX, zona)
            coef, *_ = np.linalg.lstsq(A[ajusta].values, y[ajusta].values, rcond=None)
            pred.loc[prueba, nombre] = A[prueba].values @ coef
    return pred
