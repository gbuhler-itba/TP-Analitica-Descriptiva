"""
Herramientas de inferencia para la evaluación de hipótesis (PreEntrega 3, notebook 05).

Intervalos con bootstrap por unidad, la fila de un test formal (H0, H1,
estadístico, p-valor y decisión), corrección por comparaciones múltiples y
coeficientes de regresión con su intervalo, en la escala en que se leen.
"""

import numpy as np
import pandas as pd


def bootstrap_estadistico(valores, grupos, funcion=np.mean, b=500, semilla=42):
    """Estadístico de `valores` con IC 95%, remuestreando grupos (unidades) y no avisos.
    Devuelve (puntual, límite inferior, límite superior)."""
    v = np.asarray(valores, dtype=float)
    por_grupo = pd.Series(np.arange(len(v))).groupby(np.asarray(grupos)).apply(np.array).values
    rng = np.random.default_rng(semilla)
    muestras = [funcion(v[np.concatenate(por_grupo[rng.integers(0, len(por_grupo), len(por_grupo))])])
                for _ in range(b)]
    return funcion(v), np.percentile(muestras, 2.5), np.percentile(muestras, 97.5)


def fila_prueba(prueba, h0, h1, estadistico, valor, p_valor, alfa=0.05):
    """Una fila de la tabla resumen de tests formales, con la decisión al nivel `alfa`."""
    return {"prueba": prueba, "H0": h0, "H1": h1, "estadístico": estadistico, "valor": valor,
            "p_valor": p_valor, "decisión": "Se rechaza H0" if p_valor < alfa else "No se rechaza H0"}


def holm(p_valores):
    """p-valores ajustados por comparaciones múltiples con el método de Holm."""
    from statsmodels.stats.multitest import multipletests
    p = pd.Series(p_valores)
    return pd.Series(multipletests(p.values, method="holm")[1], index=p.index)


def tabla_coeficientes(resultado, variables, escala="pp"):
    """Coeficientes de un modelo de statsmodels con IC 95% y p-valor, en la escala en que se leen.

    `escala`: "pp" (probabilidad lineal: puntos porcentuales), "pct_log"
    (variable dependiente en log: % de diferencia, 100 × (e^b − 1)) u "or"
    (logit: odds ratio, e^b).
    """
    ic = resultado.conf_int().loc[variables]
    coef = resultado.params[variables]
    transformar = {"pp": lambda b: 100 * b, "pct_log": lambda b: 100 * (np.exp(b) - 1), "or": np.exp}[escala]
    return pd.DataFrame({"efecto": transformar(coef), "ic_inf": transformar(ic[0]), "ic_sup": transformar(ic[1]),
                         "p_valor": resultado.pvalues[variables]})


def bootstrap_diferencia_medianas(a, b, grupos, n_boot=500, semilla=42):
    """Diferencia de medianas (a − b) de dos mediciones pareadas por aviso, con IC 95% remuestreando grupos.
    Devuelve (puntual, límite inferior, límite superior)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    por_grupo = pd.Series(np.arange(len(a))).groupby(np.asarray(grupos)).apply(np.array).values
    rng = np.random.default_rng(semilla)
    difs = []
    for _ in range(n_boot):
        idx = np.concatenate(por_grupo[rng.integers(0, len(por_grupo), len(por_grupo))])
        difs.append(np.median(a[idx]) - np.median(b[idx]))
    return np.median(a) - np.median(b), np.percentile(difs, 2.5), np.percentile(difs, 97.5)
