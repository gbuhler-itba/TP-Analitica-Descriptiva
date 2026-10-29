"""Tests de la etapa 6 (análisis) y de las herramientas de validación de la PreEntrega 3."""

import numpy as np
import pandas as pd

from src import analisis, validacion


def test_tratar_geo_dudoso_saca_coordenadas_y_variables_espaciales():
    df = pd.DataFrame({
        "lat": [-34.60, -34.61, -34.62],
        "lon": [-58.40, -58.41, -58.42],
        "subzona": ["palermo_1", "palermo_2", "palermo_1"],
        "dist_subte_m": [300.0, 500.0, 800.0],
        "area_verde_500m_m2": [1000.0, 2000.0, 0.0],
        "permisos_obra_500m": [5, 9, 12],
        "geo_dudoso": pd.array([0, 1, pd.NA], dtype="Int64"),
    })
    out = analisis.tratar_geo_dudoso(df)
    assert out.loc[1, ["lat", "lon", "subzona", "dist_subte_m", "area_verde_500m_m2",
                       "permisos_obra_500m"]].isna().all()
    # los demás avisos (incluido el que no tiene dato de geo_dudoso) quedan igual
    pd.testing.assert_frame_equal(out.loc[[0, 2]], df.loc[[0, 2]], check_dtype=False)
    # no modifica el DataFrame original
    assert df.loc[1, "lat"] == -34.61


def test_jaccard():
    a = pd.Series([True, True, False, False])
    b = pd.Series([True, False, True, False])
    assert validacion.jaccard(a, b) == 1 / 3
    assert validacion.jaccard(a, a) == 1


def test_intervalos_conformes_cubren_el_nivel_pedido():
    rng = np.random.default_rng(0)
    n = 6000
    grupo = pd.Series(np.where(np.arange(n) < n / 2, "a", "b"))
    # el grupo "b" es tres veces más ruidoso: el intervalo debe ser más ancho ahí
    residuo = pd.Series(rng.normal(0, np.where(grupo == "a", 0.1, 0.3)))
    vuelta = pd.Series(rng.integers(0, 5, n))
    inf, sup = validacion.intervalos_conformes(residuo, grupo, vuelta, nivel=0.80)
    cobertura = ((residuo >= inf) & (residuo <= sup)).mean()
    assert abs(cobertura - 0.80) < 0.02
    ancho = (sup - inf).groupby(grupo).median()
    assert ancho["b"] > 2.5 * ancho["a"]


def test_intervalos_conformes_usan_la_ciudad_en_grupos_chicos():
    rng = np.random.default_rng(1)
    n = 2000
    grupo = pd.Series(["chico"] * 20 + ["grande"] * (n - 20))
    residuo = pd.Series(rng.normal(0, 0.2, n))
    vuelta = pd.Series(rng.integers(0, 5, n))
    inf, _ = validacion.intervalos_conformes(residuo, grupo, vuelta, nivel=0.80, minimo=50)
    chicos = grupo == "chico"
    for p in vuelta[chicos].unique():
        esperado = residuo[vuelta != p].quantile(0.10)
        assert np.allclose(inf[chicos & (vuelta == p)], esperado)


def test_estabilidad_subzonas_alta_con_grupos_bien_separados():
    rng = np.random.default_rng(2)
    centros = {"norte": (-34.55, -58.45), "sur": (-34.65, -58.40)}
    filas = []
    for i, (nombre, (la, lo)) in enumerate(centros.items()):
        for _ in range(100):
            filas.append({"barrio": "x", "subzona": f"x_{i}",
                          "lat": la + rng.normal(0, 0.002), "lon": lo + rng.normal(0, 0.002)})
    estab = validacion.estabilidad_subzonas(pd.DataFrame(filas), repeticiones=5)
    assert estab.loc["x", "subzonas"] == 2
    assert estab.loc["x", "ari_mediano"] > 0.95
