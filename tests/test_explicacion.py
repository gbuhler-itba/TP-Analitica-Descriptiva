"""Tests de la explicación de las predicciones (src/validacion.py y src/analisis.py)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingRegressor

from src import analisis, modelo, validacion


def _dataset_sintetico(n=400, semilla=0):
    """Avisos con todas las columnas que usan los modelos, en dos barrios con dos sub-zonas cada uno."""
    rng = np.random.default_rng(semilla)
    barrio = rng.choice(["Almagro", "Boedo"], n)
    sub = rng.integers(0, 2, n)
    lat = np.where(barrio == "Almagro", -34.60, -34.63) + 0.01 * sub + rng.normal(0, 0.002, n)
    lon = -58.42 + 0.01 * sub + rng.normal(0, 0.002, n)
    m2 = rng.uniform(30, 120, n)
    precio_m2 = 2000 * np.where(barrio == "Almagro", 1.1, 0.9) * (1 + 0.1 * sub) * rng.lognormal(0, 0.1, n)
    df = pd.DataFrame({
        "id_aviso": [f"MLA{i}" for i in range(n)],
        "dir_limpia": [f"calle {i}" for i in range(n)],
        "barrio": barrio,
        "subzona": [f"{b}_{s}" for b, s in zip(barrio, sub)],
        "lat": lat, "lon": lon,
        "m2_final": m2,
        "precio_m2_usd": precio_m2,
        "ambientes": rng.integers(1, 5, n).astype(float),
        "dormitorios": rng.integers(0, 4, n).astype(float),
        "banos": np.where(rng.random(n) < 0.2, np.nan, rng.integers(1, 3, n)),
        "cocheras": rng.integers(0, 2, n).astype(float),
        "antiguedad": np.where(rng.random(n) < 0.2, np.nan, rng.integers(0, 90, n)),
        "numero_de_piso_de_la_unidad": np.where(rng.random(n) < 0.2, np.nan, rng.integers(0, 12, n)),
        "disposicion": rng.choice(["Frente", "Contrafrente"], n),
        "apto_credito": rng.choice(["Sí", "No"], n),
        "titulo": rng.choice(["Depto a reciclar", "Depto luminoso", "Depto a estrenar"], n),
        "titulo_casa": rng.random(n) < 0.05,
        "titulo_tipo_casa": rng.random(n) < 0.05,
        "expensas_usd": np.where(rng.random(n) < 0.2, np.nan, rng.uniform(50, 300, n)),
    })
    for c in modelo.AMENITIES_Y_EXTRAS:
        df[c] = rng.choice(["Sí", "No"], n)
    return df, np.log(df["precio_m2_usd"])


@pytest.fixture(scope="module")
def ajustado():
    df, y = _dataset_sintetico()
    pred, vuelta, ajustes = validacion.comparar_modelos(df, y, k=2, modelos=["lineal_ampliado", "gbm"],
                                                        devolver_modelos=True)
    return df, y, pred, vuelta, ajustes


def test_variables_del_modelo_agrupa_columnas_que_van_juntas():
    columnas = ["log_m2", "banos", "banos_sin_dato", "antiguedad_0_5", "antiguedad_sin_dato", "piso",
                "piso_sin_dato", "titulo_a_reciclar", "titulo_a_estrenar", "titulo_casa", "lat", "lon", "barrio",
                "zona_log_mediana"]
    v = validacion.variables_del_modelo(columnas)
    assert v["banos"] == ["banos", "banos_sin_dato"]
    assert v["antiguedad"] == ["antiguedad_0_5", "antiguedad_sin_dato"]
    assert v["piso"] == ["piso", "piso_sin_dato"]
    assert v["estado_titulo"] == ["titulo_a_reciclar", "titulo_a_estrenar"]
    assert v["titulo_casa"] == ["titulo_casa"]
    assert v["ubicacion"] == ["lat", "lon", "barrio", "zona_log_mediana"]
    assert sum(len(c) for c in v.values()) == len(columnas)


def test_comparar_modelos_sin_devolver_modelos_no_cambia_la_salida(ajustado):
    df, y, pred, vuelta, ajustes = ajustado
    salida = validacion.comparar_modelos(df, y, k=2, modelos=["lineal_ampliado", "gbm"])
    assert len(salida) == 2
    pd.testing.assert_frame_equal(salida[0], pred)
    assert set(ajustes) == set(vuelta.unique())
    # Los modelos devueltos reproducen la predicción de los avisos que no vieron
    for p, aj in ajustes.items():
        prueba = aj["prueba"]
        assert np.allclose(aj["gbm"].predict(aj["G"][prueba].values), pred.loc[prueba, "gbm"])


def test_explicar_lineal_es_exacto_y_la_base_es_la_de_la_zona(ajustado):
    df, y, pred, vuelta, ajustes = ajustado
    avisos = pd.Series(True, index=df.index)
    contrib = validacion.explicar_lineal(ajustes, avisos)
    assert list(contrib.index) == list(df.index)
    suma = contrib.drop(columns="vuelta").sum(axis=1)
    assert np.allclose(suma, pred["lineal_ampliado"])
    # Un aviso con las características medias de su zona tendría contribución 0: la base es común a la zona
    zona = pd.concat([aj["zona"][aj["prueba"]] for aj in ajustes.values()]).loc[df.index]
    rango = contrib.groupby([contrib["vuelta"], zona])["base"].agg(lambda b: b.max() - b.min())
    assert (rango < 1e-9).all()


@pytest.mark.parametrize("fondo", ["ciudad", "zona"])
def test_explicar_gbm_suma_la_prediccion_con_barrio_categorico(ajustado, fondo):
    df, y, pred, vuelta, ajustes = ajustado
    avisos = pd.Series(False, index=df.index)
    avisos.iloc[:12] = True
    contrib = validacion.explicar_gbm(ajustes, avisos, fondo=fondo, n_fondo=20, max_evals=100)
    assert list(contrib.index) == list(df.index[avisos])
    assert "ubicacion" in contrib.columns and "lat" not in contrib.columns
    suma = contrib.drop(columns="vuelta").sum(axis=1)
    assert np.allclose(suma, pred.loc[avisos, "gbm"])


def test_shap_por_permutacion_reemplaza_las_columnas_de_una_variable_juntas():
    # Columnas 0 y 1 son una sola variable y valen siempre lo mismo; si el explicador
    # las separara, armaría filas imposibles y la función fallaría.
    rng = np.random.default_rng(0)
    a = rng.normal(size=30)
    fondo = np.column_stack([a, a, rng.normal(size=30)])
    x = np.array([[2.0, 2.0, 1.0]])

    def predecir(m):
        assert np.array_equal(m[:, 0], m[:, 1]), "se separaron columnas de una misma variable"
        return m[:, 0] + 0.5 * m[:, 2]

    valores, base = validacion._shap_por_permutacion(predecir, fondo, x, [[0, 1], [2]], max_evals=50)
    assert np.allclose(base + valores.sum(axis=1), predecir(x))
    # Modelo aditivo: el SHAP exacto es el apartamiento de cada variable respecto de la media del fondo
    assert np.allclose(valores[0], [2.0 - a.mean(), 0.5 * (1.0 - fondo[:, 2].mean())])


def test_tabla_explicacion_ordena_y_reproduce_el_precio_esperado():
    contrib = pd.DataFrame({
        "log_m2": [0.10, -0.05], "cochera": [0.03, 0.00], "antiguedad": [-0.20, 0.02],
        "pileta": [0.01, -0.01], "piso": [-0.02, 0.04], "base": [np.log(2000), np.log(3000)], "vuelta": [0, 1],
    }, index=[10, 11])
    df = pd.DataFrame({"id_aviso": ["MLA1", "MLA2"]}, index=[10, 11])
    tabla = analisis.tabla_explicacion(contrib, df, n=2)
    fila = tabla.iloc[0]
    assert fila["precio_m2_referencia_zona"] == 2000
    assert (fila["sube_1"], fila["sube_2"]) == ("Superficie", "Cochera")
    assert (fila["baja_1"], fila["baja_2"]) == ("Antigüedad", "Piso")
    assert fila["sube_1_%"] == pytest.approx(100 * (np.exp(0.10) - 1), abs=0.05)
    # Los efectos se multiplican: referencia × (1 + efectos) × (1 + resto) = esperado
    efectos = [fila[c] for c in ["sube_1_%", "sube_2_%", "baja_1_%", "baja_2_%", "resto_%"]]
    producto = 2000 * np.prod([1 + e / 100 for e in efectos])
    assert producto == pytest.approx(fila["precio_m2_esperado"], rel=2e-3)
    assert fila["precio_m2_esperado"] == pytest.approx(2000 * np.exp(-0.08), abs=1)


def test_explicar_gbm_guardado_lee_solo_si_coincide_con_el_calculo(ajustado, tmp_path):
    df, y, pred, vuelta, ajustes = ajustado
    avisos = pd.Series(False, index=df.index)
    avisos.iloc[:6] = True
    ruta = tmp_path / "shap_gbm.tsv"
    kw = {"n_fondo": 10, "max_evals": 60}
    primero, origen = validacion.explicar_gbm_guardado(ajustes, avisos, ruta, df["id_aviso"], pred["gbm"], **kw)
    assert origen == "calculado" and ruta.exists()
    segundo, origen = validacion.explicar_gbm_guardado(ajustes, avisos, ruta, df["id_aviso"], pred["gbm"], **kw)
    assert origen == "leído"
    pd.testing.assert_frame_equal(segundo, primero, check_dtype=False)
    # Otra predicción (otros datos, otro modelo u otra plataforma) u otros parámetros: se recalcula
    _, origen = validacion.explicar_gbm_guardado(ajustes, avisos, ruta, df["id_aviso"], pred["gbm"] + 0.01, **kw)
    assert origen == "calculado"
    _, origen = validacion.explicar_gbm_guardado(ajustes, avisos, ruta, df["id_aviso"], pred["gbm"], n_fondo=12,
                                                 max_evals=60)
    assert origen == "calculado"
