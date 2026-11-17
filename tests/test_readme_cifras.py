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


@pytest.fixture(scope="module")
def como_leer():
    html = (RAIZ / "docs" / "dashboard" / "index.html").read_text(encoding="utf-8")
    inicio = html.index('id="pagina-leer"')
    return re.sub(r"\s+", " ", html[inicio:])


@pytest.fixture(scope="module")
def avisos():
    return json.load(open(RAIZ / "docs" / "dashboard" / "data" / "avisos.json", encoding="utf-8"))


def test_las_cifras_de_como_leer_salen_del_resumen_y_de_los_avisos(como_leer, resumen, avisos):
    ind = resumen["indicadores"]
    assert f"Se equivoca {_pct(ind['error_mediano_pct'])}% en la mediana" in como_leer
    assert f"cubre el precio publicado el {_pct(ind['cobertura_intervalo_pct'])}% de las veces" in como_leer
    assert f"({_pct(ind['error_mediano_segmento_alerta_pct'])}% contra {_pct(ind['error_mediano_pct'])}%)" in como_leer
    negociacion = 100 * resumen["parametros_costos"]["base"]["negociacion"]
    assert f"descuenta {_pct(negociacion, 2)}% al vender" in como_leer
    salieron = np.mean([a["estado_r2"] == "salio" for a in avisos])
    republicados = np.mean([a["estado_r2"] == "republicado" for a in avisos])
    assert 0.45 < salieron < 0.55 and "la mitad de las señales había salido del portal" in como_leer
    assert f"(y un {round(100 * republicados):.0f}% estaba republicada" in como_leer
    assert f"se muestran 10 de" not in como_leer   # la lista destacada vive en el Resumen, no acá


def test_el_rango_de_como_leer_es_el_del_precio_esperado(como_leer):
    ruta = RAIZ / "data" / "processed" / "precio_esperado.tsv"
    if not ruta.exists():
        pytest.skip("faltan las salidas de la etapa 6")
    pe = pd.read_csv(ruta, sep="\t", usecols=["precio_m2_esperado", "precio_m2_esperado_inf", "precio_m2_esperado_sup"], low_memory=False)
    inf = 100 * (pe["precio_m2_esperado_inf"] / pe["precio_m2_esperado"] - 1).median()
    sup = 100 * (pe["precio_m2_esperado_sup"] / pe["precio_m2_esperado"] - 1).median()
    semiancho = 100 * ((pe["precio_m2_esperado_sup"] - pe["precio_m2_esperado_inf"]) / (2 * pe["precio_m2_esperado"])).median()
    frase = f"de −{abs(round(inf)):.0f}% a +{round(sup):.0f}% alrededor del esperado (semiancho mediano {round(semiancho):.0f}%)"
    assert como_leer.count(frase) == 2, frase


def test_los_geo_dudosos_de_como_leer_son_los_del_dataset(como_leer):
    acc = RAIZ / "data" / "processed" / "accesibilidad.tsv"
    limpio = RAIZ / "data" / "processed" / "propiedades_limpias.tsv"
    if not (acc.exists() and limpio.exists()):
        pytest.skip("faltan accesibilidad.tsv o el dataset limpio")
    a = pd.read_csv(acc, sep="\t", usecols=["link", "geo_dudoso", "barrio_coincide"], low_memory=False)
    links = set(pd.read_csv(limpio, sep="\t", usecols=["link"])["link"])
    en_limpio = a[a["link"].isin(links)]
    dudosos = int(en_limpio["geo_dudoso"].fillna(0).astype(int).sum())
    assert f"Los {dudosos} avisos a más de 1 km de su barrio" in como_leer
    con_barrio = a["barrio_coincide"].dropna()
    otro_poligono = round(100 * (1 - con_barrio.astype(float).mean()))
    assert f"{otro_poligono:.0f}% de los avisos con coordenadas caen en otro polígono oficial" in como_leer


def test_los_tipos_de_departamento_de_app_js_salen_del_resumen(resumen):
    js = (RAIZ / "docs" / "dashboard" / "js" / "app.js").read_text(encoding="utf-8")
    bloque = js[js.index("const SEGMENTOS = ["):js.index("];", js.index("const SEGMENTOS = ["))]
    descripciones = dict(re.findall(r'nombre: "([^"]+)", descripcion: "([^"]+)"', bloque))
    tipos = {t["nombre"]: t for t in resumen["tipos"]}
    assert set(descripciones) == set(tipos)
    for nombre, texto in descripciones.items():
        pct = round(tipos[nombre]["avisos_pct"])
        assert f"({pct}%)" in texto or f"{pct}% de la oferta" in texto, (nombre, texto, pct)
        if "mediana de" in texto:
            assert f"mediana de {tipos[nombre]['amenities_mediana']:.0f}" in texto, (nombre, texto)
    assert resumen["indicadores"]["avisos_segmento_alerta_pct"] == tipos[resumen["indicadores"]["segmento_alerta"]]["avisos_pct"]


def test_la_diferencia_simple_de_la_pileta_sale_del_dataset_limpio():
    """La comparación del hallazgo 2 (pileta a simple vista contra la prima del modelo) sale del código."""
    ruta = RAIZ / "data" / "processed" / "propiedades_limpias.tsv"
    if not ruta.exists():
        pytest.skip("falta el dataset limpio")
    from src import analisis, eda
    df = pd.read_csv(ruta, sep="\t", low_memory=False)
    dif = eda.diferencia_simple_por_unidad(df, "pileta", analisis.unidad_ranking(df))["diferencia_pct"]
    prima_modelo = 4.2   # notebook 04, sección 6 (lineal ampliado); la tabla del diccionario cita la misma
    diccionario = re.sub(r"\s+", " ", (RAIZ / "docs" / "diccionario_datos.md").read_text(encoding="utf-8"))
    presentacion = (RAIZ / "docs" / "presentacion" / "index.html").read_text(encoding="utf-8")
    assert f"+{_pct(dif)}% en la diferencia simple contra +{_pct(prima_modelo)}% en el modelo" in diccionario
    assert f"Prima del modelo: +{_pct(prima_modelo)}% (diferencia simple por unidad: +{_pct(dif)}%" in diccionario
    assert f"Prima de la pileta: {_pct(dif)}% a simple vista" in presentacion
    assert f"hasta=pilModo==='parece'?{dif:.1f}:{prima_modelo}" in presentacion
    assert f"se publica {round(dif):.0f}% más caro" in presentacion
    assert f"parece valer más de {int(dif // prima_modelo)} veces lo que vale" in presentacion
