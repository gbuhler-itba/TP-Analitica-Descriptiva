"""Tests unitarios de precio_relativo y error_vara_fuera_de_muestra (src/eda.py)."""

import numpy as np
import pandas as pd

from src.eda import error_vara_fuera_de_muestra, precio_relativo


def test_precio_relativo_es_log_menos_media_del_log_del_grupo():
    valores = pd.Series([100.0, 100.0 * np.exp(0.1), 50.0])
    grupo = pd.Series(["a", "a", "b"])
    assert np.allclose(precio_relativo(valores, grupo), [-0.05, 0.05, 0.0])


def test_precio_relativo_suma_cero_dentro_de_cada_grupo():
    valores = pd.Series([1000.0, 1500.0, 2000.0, 3000.0, 3500.0])
    grupo = pd.Series(["a", "a", "a", "b", "b"])
    suma = precio_relativo(valores, grupo).groupby(grupo).sum()
    assert np.allclose(suma, 0)


def test_precio_relativo_no_depende_de_la_escala():
    valores = pd.Series([100.0, 200.0, 400.0])
    grupo = pd.Series(["a"] * 3)
    assert np.allclose(precio_relativo(valores, grupo), precio_relativo(valores * 1000, grupo))


def test_error_vara_es_cero_si_todo_el_grupo_tiene_el_mismo_valor():
    valores = pd.Series([2000.0] * 50)
    grupo = pd.Series(["a"] * 50)
    error = error_vara_fuera_de_muestra(valores, grupo)
    assert np.allclose(error, 0)


def test_error_vara_es_el_error_porcentual_absoluto_contra_la_mediana():
    # 40 avisos a 1000 y 1 a 1500: la mediana sin ese aviso es 1000 -> error 50%
    valores = pd.Series([1000.0] * 40 + [1500.0])
    grupo = pd.Series(["a"] * 41)
    error = error_vara_fuera_de_muestra(valores, grupo)
    assert np.isclose(error.iloc[-1], 0.5)
    assert np.allclose(error.iloc[:-1], 0)


def test_error_vara_grupo_chico_queda_en_nan():
    valores = pd.Series([1000.0] * 50 + [1000.0] * 5)
    grupo = pd.Series(["grande"] * 50 + ["chico"] * 5)
    error = error_vara_fuera_de_muestra(valores, grupo)
    assert error.iloc[50:].isna().all()
    assert error.iloc[:50].notna().all()


def test_error_vara_con_unidad_pone_cada_unidad_entera_en_una_sola_parte():
    # Dos avisos de la misma unidad con precios muy distintos: si quedaran en partes
    # distintas, cada uno serviría de referencia al otro. Con `unidad`, la mediana de
    # entrenamiento de cada uno nunca incluye al otro, así que su error es el mismo
    # que si el gemelo no existiera.
    rng = np.random.default_rng(0)
    n = 200
    valores = pd.Series(rng.lognormal(7.5, 0.3, n))
    grupo = pd.Series(["a"] * n)
    unidad = pd.Series(np.arange(n) // 2)          # unidades de dos avisos
    valores.iloc[1::2] = valores.iloc[0::2].values  # los gemelos piden lo mismo
    error = error_vara_fuera_de_muestra(valores, grupo, k=5, minimo_grupo=2, semilla=1, unidad=unidad)
    # Con partes por unidad, los dos avisos de cada unidad tienen el mismo error
    pares = error.groupby(unidad).nunique()
    assert (pares == 1).all()
