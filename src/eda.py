"""
Funciones de análisis exploratorio reutilizables desde los notebooks.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Colores comunes a todos los gráficos del proyecto
AZUL = "#2a78d6"       # serie principal
AZUL_OSCURO = "#184f95"
GRIS = "#B0B0B0"       # contexto, de-énfasis
ROJO = "#C8553D"       # énfasis / alerta


# Nombres de barrio para mostrar en gráficos (el dataset usa el formato de la URL)
_TILDES_BARRIO = {
    "nunez": "Núñez", "agronomia": "Agronomía", "constitucion": "Constitución",
    "villa-ortuzar": "Villa Ortúzar", "san-nicolas": "San Nicolás",
    "velez-sarsfield": "Vélez Sarsfield", "villa-pueyrredon": "Villa Pueyrredón",
}


def nombre_barrio(slug):
    """'villa-lugano' -> 'Villa Lugano'; agrega las tildes de los nombres oficiales."""
    return _TILDES_BARRIO.get(slug, slug.replace("-", " ").title().replace(" Del ", " del "))


def formato_ar(valor, decimales=0):
    """Número con separador de miles "." y decimal "," (12345.6 -> '12.345,6')."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def resumen_numerico(df, columnas):
    """Estadísticos de resumen robustos para variables numéricas."""
    filas = {}
    for c in columnas:
        s = df[c].dropna()
        filas[c] = {
            "n": len(s),
            "media": s.mean(),
            "mediana": s.median(),
            "desvio": s.std(),
            "asimetria": s.skew(),
            "p05": s.quantile(0.05),
            "p25": s.quantile(0.25),
            "p75": s.quantile(0.75),
            "p95": s.quantile(0.95),
        }
    return pd.DataFrame(filas).T


def precio_relativo(valores, grupo):
    """Logaritmo del valor menos la media del logaritmo de su grupo.

    0 = típico de su grupo; +0,10 ~ 10% más caro; -0,10 ~ 10% más barato.
    """
    log_v = np.log(valores)
    return log_v - log_v.groupby(grupo).transform("mean")


def error_vara_fuera_de_muestra(valores, grupo, k=5, minimo_grupo=10, semilla=42):
    """Error de usar la mediana de un grupo como precio de referencia.

    Para cada aviso, la mediana de su grupo se calcula SIN ese aviso (validación
    cruzada en k partes), y se mide el error porcentual absoluto. Permite comparar
    barrio contra sub-zona sin favorecer a la división con más grupos.
    Devuelve una Serie con el error de cada aviso (NaN si su grupo es muy chico).
    """
    datos = pd.DataFrame({"v": valores, "g": grupo}).dropna()
    rng = np.random.default_rng(semilla)
    datos["parte"] = rng.integers(0, k, len(datos))
    error = pd.Series(np.nan, index=datos.index)
    for p in range(k):
        entrena = datos[datos["parte"] != p]
        prueba = datos[datos["parte"] == p]
        conteo = entrena.groupby("g")["v"].size()
        medianas = entrena.groupby("g")["v"].median()[conteo >= minimo_grupo]
        referencia = prueba["g"].map(medianas)
        error.loc[prueba.index] = (prueba["v"] / referencia - 1).abs()
    return error


def correlacion_intra_grupo(x, y, grupo):
    """Spearman entre x e y después de restar la media de cada grupo a ambas.

    Mide la relación DENTRO de los grupos (por ejemplo, dentro de cada barrio),
    sin que la mezcle la diferencia de nivel entre grupos.
    """
    datos = pd.DataFrame({"x": x, "y": y, "g": grupo}).dropna()
    x_dm = datos["x"] - datos.groupby("g")["x"].transform("mean")
    y_dm = datos["y"] - datos.groupby("g")["y"].transform("mean")
    rho, p = spearmanr(x_dm, y_dm)
    return rho, p, len(datos)


def medianas_por_tramo(x, y, cortes, etiquetas=None):
    """Mediana, cuartiles y cantidad de y por tramos de x."""
    tramo = pd.cut(x, cortes, labels=etiquetas, include_lowest=True)
    return y.groupby(tramo, observed=True).agg(
        n="size",
        p25=lambda s: s.quantile(0.25),
        mediana="median",
        p75=lambda s: s.quantile(0.75),
    )


def diferencia_intra_grupo(valores, marca, grupo, minimo=10):
    """Diferencia porcentual de medianas entre avisos con y sin `marca`,
    calculada dentro de cada grupo y resumida con la mediana entre grupos."""
    datos = pd.DataFrame({"v": valores, "m": marca, "g": grupo}).dropna()
    difs = []
    for _, g in datos.groupby("g"):
        a = g.loc[g["m"] == 1, "v"]
        b = g.loc[g["m"] == 0, "v"]
        if len(a) >= minimo and len(b) >= minimo:
            difs.append(a.median() / b.median() - 1)
    return (100 * np.median(difs) if difs else np.nan), len(difs)
