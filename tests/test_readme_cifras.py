"""Las cifras clave del README salen de los archivos versionados: el embudo de la etapa 6, el resumen del dashboard y
el precio esperado. Si alguien cambia un número a mano, o regenera los datos sin actualizar el texto, esto falla."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _entero(n):
    return f"{int(n):,}".replace(",", ".")


def _pct(x, decimales=1):
    return f"{x:.{decimales}f}".replace(".", ",")


@pytest.fixture(scope="module")
def readme():
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", texto)   # los saltos de línea del markdown no cuentan


@pytest.fixture(scope="module")
def resumen():
    return json.load(open(RAIZ / "docs" / "dashboard" / "data" / "resumen.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def embudo():
    tabla = pd.read_csv(RAIZ / "data" / "processed" / "embudo_ranking.csv").set_index("paso")
    return {paso: (int(f["avisos"]), int(f["unidades"])) for paso, f in tabla.iterrows()}


def test_el_resumen_del_dashboard_coincide_con_el_embudo(resumen, embudo):
    ind = resumen["indicadores"]
    assert (ind["avisos_analizados"], ind["unidades_analizadas"]) == embudo["analizados"]
    assert ind["senales_unidades"] == embudo["cumple_regla"][1]
    assert ind["candidatos_unidades"] == embudo["candidato"][1]
    assert {e["paso"]: (e["avisos"], e["unidades"]) for e in resumen["embudo"]} == embudo


def test_el_embudo_del_readme_es_el_de_la_etapa_6(readme, embudo, resumen):
    a, u = embudo["analizados"]
    assert f"{_entero(a)} avisos ({_entero(u)} unidades) analizados" in readme
    a, u = embudo["marcado"]
    assert f"{_entero(a)} avisos ({_entero(u)} unidades) piden más de 25% menos" in readme
    a, u = embudo["marcado_barrio"]
    assert f"{_entero(a)} ({_entero(u)}) siguen marcados con el umbral de su barrio" in readme
    a, u = embudo["cumple_regla"]
    assert f"{_entero(a)} avisos, {_entero(u)} unidades, sin señales de error de carga: la lista oficial" in readme
    a, u = embudo["candidato"]
    assert f"{_entero(a)} avisos ({_entero(u)} unidades) son candidatos después de costos" in readme
    firmes = resumen["indicadores"]["candidatos_firmes_unidades"]
    assert resumen["sensibilidad"]["conservador"] == firmes
    assert f"y **{firmes} si se vende al límite inferior del rango del 80%**" in readme


def test_los_destacados_y_el_error_del_readme_son_los_del_resumen(readme, resumen):
    ind = resumen["indicadores"]
    assert f"quedan {ind['destacados_unidades']} destacados ({ind['destacados_firmes_unidades']} firmes)" in readme
    assert f"erra {_pct(ind['error_mediano_pct'])}% en la mediana fuera de muestra" in readme
    assert f"cubre el precio publicado el {_pct(ind['cobertura_intervalo_pct'])}% de las veces" in readme
    assert f"{_pct(ind['tasa_salida_marcados_pct'])}% contra {_pct(ind['tasa_salida_resto_pct'])}%" in readme


def test_el_rango_del_80_del_readme_sale_del_precio_esperado(readme, resumen):
    ruta = RAIZ / "data" / "processed" / "precio_esperado.tsv"
    if not ruta.exists():
        pytest.skip("faltan las salidas de la etapa 6")
    pe = pd.read_csv(ruta, sep="\t", usecols=["precio_m2_esperado", "precio_m2_esperado_inf", "precio_m2_esperado_sup",
                                               "precio_m2_usd"], low_memory=False)
    inf = 100 * (pe["precio_m2_esperado_inf"] / pe["precio_m2_esperado"] - 1).median()
    sup = 100 * (pe["precio_m2_esperado_sup"] / pe["precio_m2_esperado"] - 1).median()
    semiancho = 100 * ((pe["precio_m2_esperado_sup"] - pe["precio_m2_esperado_inf"]) / (2 * pe["precio_m2_esperado"])).median()
    frase = f"de −{abs(round(inf)):.0f}% a +{round(sup):.0f}% alrededor del esperado (semiancho mediano {round(semiancho):.0f}%)"
    assert frase in readme, frase
    dentro = (pe["precio_m2_usd"] >= pe["precio_m2_esperado_inf"]) & (pe["precio_m2_usd"] <= pe["precio_m2_esperado_sup"])
    assert round(100 * dentro.mean(), 1) == resumen["indicadores"]["cobertura_intervalo_pct"]
    assert np.isfinite([inf, sup, semiancho]).all()
