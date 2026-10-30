"""Tests de los segmentos exploratorios (src/segmentos.py)."""

import numpy as np
import pandas as pd
import pytest

from src import segmentos


def _avisos_con_amenities(n=300, semilla=0):
    rng = np.random.default_rng(semilla)
    lujo = rng.random(n) < 0.3
    df = pd.DataFrame(index=range(n))
    for c in segmentos.COLUMNAS_MCA:
        prob = np.where(lujo, 0.8, 0.15)
        valores = np.where(rng.random(n) < prob, "Sí", "No").astype(object)
        if c in segmentos.COLUMNAS_SOLO_SI:
            valores[valores == "No"] = None
        else:
            valores[rng.random(n) < 0.1] = None
        df[c] = valores
    return df, lujo


def test_tabla_mca_trata_el_sin_dato_segun_la_opcion():
    df, _ = _avisos_con_amenities()
    como_no = segmentos.tabla_mca(df, "no")
    assert set(np.unique(como_no.values)) == {"Sí", "No"}
    categoria = segmentos.tabla_mca(df, "categoria")
    assert "sin dato" in set(categoria[segmentos.COLUMNAS_SI_NO].values.ravel())
    assert "no figura" in set(categoria[segmentos.COLUMNAS_SOLO_SI].values.ravel())


def test_indice_mca_crece_con_el_equipamiento():
    df, lujo = _avisos_con_amenities()
    X = segmentos.tabla_mca(df, "no")
    indice = segmentos.indice_mca(segmentos.ajustar_mca(X, n_componentes=2), X)
    assert indice[lujo].mean() > indice[~lujo].mean()
    assert indice.corr((X == "Sí").sum(axis=1)) > 0.8


def test_escalar_winsoriza_y_estandariza():
    V = pd.DataFrame({"a": np.r_[np.arange(99.0), 10_000.0], "b": np.linspace(0, 1, 100)})
    Z, param = segmentos.escalar(V)
    assert np.allclose(Z.mean(), 0) and np.allclose(Z.std(ddof=0), 1)
    assert segmentos.a_escala_original(Z, param)["a"].max() < 10_000   # el extremo quedó recortado


def test_alinear_etiquetas_recupera_la_permutacion():
    referencia = np.array([0, 0, 1, 1, 2, 2])
    assert (segmentos.alinear_etiquetas(referencia, np.array([2, 2, 0, 0, 1, 1]), 3) == referencia).all()


def test_estabilidad_alta_con_grupos_separados():
    rng = np.random.default_rng(1)
    Z = np.vstack([rng.normal(c, 0.3, size=(100, 2)) for c in [(0, 0), (5, 0), (0, 5)]])
    aris, tamanos, original = segmentos.estabilidad_kmeans(Z, 3, repeticiones=10, n_init=5)
    assert aris.min() > 0.95
    assert np.allclose(tamanos.mean(), 100 / 3, atol=2)
    assert len(original) == len(Z)


def test_nombrar_segmentos_sigue_la_regla_y_falla_si_no_separa():
    centroides = pd.DataFrame({"ambientes": [4.3, 2.7, 2.8, 1.7], "indice_equipamiento": [0.0, 0.9, -0.2, -0.1]},
                              index=[7, 3, 1, 0])
    nombres = segmentos.nombrar_segmentos(centroides)
    assert nombres[7] == "Familiares amplios y antiguos" and nombres[3] == "Nuevos con amenities"
    assert nombres[0] == "Chicos y recientes" and nombres[1] == "Compactos de edificio antiguo"
    centroides.loc[7, "indice_equipamiento"] = 2.0   # el más grande también es el más equipado
    with pytest.raises(ValueError):
        segmentos.nombrar_segmentos(centroides)


def test_bootstrap_estadistico_cubre_la_media_y_respeta_los_grupos():
    rng = np.random.default_rng(0)
    valores = rng.normal(10, 1, 400)
    puntual, inf, sup = segmentos.bootstrap_estadistico(valores, np.repeat(np.arange(200), 2), b=300)
    assert inf < puntual < sup and inf < 10 < sup
    # Con un solo grupo, todas las muestras son iguales: el intervalo no tiene ancho
    _, inf, sup = segmentos.bootstrap_estadistico(valores, np.zeros(400, dtype=int), b=50)
    assert inf == sup


def test_probabilidad_fuera_de_muestra_aprende_y_sin_variables_da_la_tasa():
    rng = np.random.default_rng(0)
    n = 2000
    x = pd.DataFrame({"x": rng.normal(size=n)})
    y = pd.Series((rng.random(n) < 1 / (1 + np.exp(-2 * x["x"]))).astype(int))
    grupos = np.arange(n) // 2
    prob = segmentos.probabilidad_fuera_de_muestra(y, x, grupos)
    base = segmentos.probabilidad_fuera_de_muestra(y, x.iloc[:, :0], grupos)
    assert prob.notna().all() and np.corrcoef(prob, x["x"])[0, 1] > 0.9
    assert abs(base.mean() - y.mean()) < 0.01
    assert segmentos.log_loss_por_aviso(y, prob).mean() < segmentos.log_loss_por_aviso(y, base).mean()
