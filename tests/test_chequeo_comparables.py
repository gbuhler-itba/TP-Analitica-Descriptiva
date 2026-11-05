"""El chequeo con comparables corre sobre los datos versionados y respeta su propio criterio."""

import numpy as np
import pandas as pd
import pytest

from src import chequeo_comparables as cc
from src.configuracion import cargar_config
from src.rutas import resolver


def test_comparables_respetan_las_tolerancias():
    base = pd.DataFrame({
        "id_aviso": list("abcdefg"), "unidad": [1, 2, 3, 4, 5, 6, 7], "barrio": ["x"] * 6 + ["y"],
        "zona": ["x"] * 7, "m2_final": [50, 60, 70, 50, 50, 50, 50], "precio_m2_usd": [2000] * 7,
        "precio_m2_esperado": [2000] * 7, "ambientes": [2, 3, 2, 4, 2, 2, 2],
        "antiguedad": [30, 40, 20, 30, 60, 30, 30], "atipico": [False] * 5 + [True, False],
    })
    aviso = base.iloc[0]
    comp = cc.comparables_de(aviso, base)
    # b entra (+1 ambiente, +20% de m², +10 años). Afuera: c (+40% de m²), d (+2 ambientes), e (+30 años),
    # f (atípico), g (otro barrio) y a (la propia unidad).
    assert list(comp["id_aviso"]) == ["b"]
    sin_antiguedad = aviso.copy()
    sin_antiguedad["antiguedad"] = np.nan
    assert cc.comparables_de(sin_antiguedad, base).empty   # sin antigüedad no hay comparables


@pytest.fixture(scope="module")
def datos():
    cfg = cargar_config()
    if not resolver(cfg["rutas"]["precio_esperado"]).exists():
        pytest.skip("faltan las salidas de la etapa 6")
    base = cc.cargar_base(cfg)
    return base, cc.destacados_del_dashboard(base)


def test_el_chequeo_corre_y_devuelve_las_columnas_esperadas(datos):
    base, destacados = datos
    assert len(destacados) > 0 and destacados["id_aviso"].is_unique
    tabla = cc.chequear(base, destacados.head(40))
    assert list(tabla.columns) == ["id_aviso", "barrio", "firme", "segmento", "comparables", "precio_m2_comparables",
                                   "esperado_vs_comparables", "publicado_vs_comparables"]
    assert len(tabla) == 40 and (tabla["comparables"] >= 0).all()
    con = tabla[tabla["comparables"] > 0]
    assert np.isfinite(con[["precio_m2_comparables", "esperado_vs_comparables", "publicado_vs_comparables"]]).all().all()
    assert tabla.loc[tabla["comparables"] == 0, "precio_m2_comparables"].isna().all()
    resumen = cc.resumir(tabla)
    assert set(resumen) == {"destacados", "con_comparables", "esperado_vs_comparables_mediana_pct",
                            "debajo_del_umbral_pct", "firmes_con_comparables", "firmes_debajo_del_umbral",
                            "esperado_vs_comparables_por_segmento_pct"}
    assert resumen["con_comparables"] <= resumen["destacados"] == 40
    assert resumen["firmes_debajo_del_umbral"] <= resumen["firmes_con_comparables"]


def test_guarda_la_tabla_y_el_resumen(datos, tmp_path):
    base, destacados = datos
    tabla = cc.chequear(base, destacados.head(12))
    cc.guardar(tabla, cc.resumir(tabla), tmp_path)
    leida = pd.read_csv(tmp_path / "chequeo_comparables.csv")
    assert len(leida) == 12 and list(leida.columns) == list(tabla.columns)
    import json
    resumen = json.load(open(tmp_path / "chequeo_comparables.json", encoding="utf-8"))
    assert resumen["destacados"] == 12 and resumen["criterio"]["minimo_comparables"] == cc.MINIMO
    # El archivo versionado tiene que corresponder a la lista destacada actual
    versionado = json.load(open(resolver("data/processed/chequeo_comparables.json"), encoding="utf-8"))
    assert versionado["destacados"] == len(destacados)
