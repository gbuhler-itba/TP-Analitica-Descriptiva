"""Tests de las herramientas de inferencia (src/inferencia.py)."""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from src import inferencia


def test_fila_prueba_decide_segun_alfa():
    assert inferencia.fila_prueba("t", "a", "b", "t", 2.5, 0.01)["decisión"] == "Se rechaza H0"
    assert inferencia.fila_prueba("t", "a", "b", "t", 0.5, 0.30)["decisión"] == "No se rechaza H0"


def test_holm_es_mas_conservador_que_sin_corregir():
    p = pd.Series([0.01, 0.02, 0.04], index=["a", "b", "c"])
    ajustados = inferencia.holm(p)
    assert (ajustados >= p).all() and ajustados["a"] == 0.03 and list(ajustados.index) == ["a", "b", "c"]


def test_tabla_coeficientes_transforma_la_escala():
    rng = np.random.default_rng(0)
    d = pd.DataFrame({"x": rng.integers(0, 2, 2000)})
    d["log_y"] = 0.1 * d["x"] + rng.normal(0, 0.01, 2000)
    res = smf.ols("log_y ~ x", d).fit()
    tabla = inferencia.tabla_coeficientes(res, ["x"], escala="pct_log")
    assert abs(tabla.loc["x", "efecto"] - 100 * (np.exp(0.1) - 1)) < 0.2
    assert tabla.loc["x", "ic_inf"] < tabla.loc["x", "efecto"] < tabla.loc["x", "ic_sup"]


def test_bootstrap_diferencia_medianas_detecta_el_corrimiento():
    rng = np.random.default_rng(0)
    a = rng.normal(1.0, 0.5, 1000)
    b = a - 0.3 + rng.normal(0, 0.05, 1000)
    puntual, inf, sup = inferencia.bootstrap_diferencia_medianas(a, b, np.arange(1000) // 2, n_boot=300)
    assert inf < 0.3 < sup and abs(puntual - 0.3) < 0.05
