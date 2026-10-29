"""Tests unitarios de src/limpieza.py, con casos chicos armados a mano."""

import numpy as np
import pandas as pd

from src.limpieza import (
    corregir_precio,
    marcas_del_titulo,
    outliers_iqr_por_grupo,
    parsear_antiguedad,
    parsear_expensas,
    parsear_superficie,
)


# ---------------------------------------------------------------------------
# corregir_precio
# ---------------------------------------------------------------------------

def _precio(texto):
    return corregir_precio(pd.DataFrame({"precio_texto": [texto]})).iloc[0]


def test_corregir_precio_separa_actual_y_anterior_cuando_bajo_de_precio():
    fila = _precio("US$120.000US$112.000 BAJÓ DE PRECIO")
    assert fila["precio_actual"] == 112000
    assert fila["precio_anterior"] == 120000
    assert bool(fila["bajo_de_precio"]) is True
    assert np.isclose(fila["baja_pct"], 100 * (1 - 112000 / 120000))


def test_corregir_precio_sin_baja_deja_anterior_vacio():
    fila = _precio("US$ 95.000")
    assert fila["precio_actual"] == 95000
    assert np.isnan(fila["precio_anterior"])
    assert bool(fila["bajo_de_precio"]) is False
    assert np.isnan(fila["baja_pct"])


def test_corregir_precio_lee_montos_en_pesos():
    assert _precio("$ 45.000.000")["precio_actual"] == 45_000_000


def test_corregir_precio_texto_vacio_da_nan():
    fila = corregir_precio(pd.DataFrame({"precio_texto": [None]})).iloc[0]
    assert np.isnan(fila["precio_actual"])
    assert bool(fila["bajo_de_precio"]) is False


def test_corregir_precio_conserva_el_indice():
    df = pd.DataFrame({"precio_texto": ["US$ 1.000", "US$ 2.000"]}, index=[10, 20])
    assert list(corregir_precio(df).index) == [10, 20]


# ---------------------------------------------------------------------------
# parsear_superficie
# ---------------------------------------------------------------------------

def test_parsear_superficie_convierte_coma_decimal():
    assert parsear_superficie(pd.Series(["103,71 m²"])).iloc[0] == 103.71


def test_parsear_superficie_entero():
    assert parsear_superficie(pd.Series(["50 m²"])).iloc[0] == 50.0


def test_parsear_superficie_punto_de_miles_es_ambiguo_y_da_nan():
    assert np.isnan(parsear_superficie(pd.Series(["45.000 m²"])).iloc[0])


def test_parsear_superficie_unidad_distinta_de_m2_da_nan():
    assert np.isnan(parsear_superficie(pd.Series(["2 ha"])).iloc[0])


def test_parsear_superficie_vacio_da_nan():
    assert np.isnan(parsear_superficie(pd.Series([None])).iloc[0])


# ---------------------------------------------------------------------------
# parsear_antiguedad
# ---------------------------------------------------------------------------

def _antiguedad(*textos):
    return parsear_antiguedad(pd.Series(list(textos)))


def test_parsear_antiguedad_lee_anios():
    edad, en_construccion = _antiguedad("71 años")
    assert edad.iloc[0] == 71
    assert not en_construccion.iloc[0]


def test_parsear_antiguedad_singular():
    assert _antiguedad("1 año")[0].iloc[0] == 1


def test_parsear_antiguedad_anio_de_construccion_se_pasa_a_edad():
    # "1.976 años" es el año de construcción: 2026 - 1976 = 50
    assert _antiguedad("1.976 años")[0].iloc[0] == 50


def test_parsear_antiguedad_negativa_es_en_construccion_con_edad_cero():
    edad, en_construccion = _antiguedad("-2 años")
    assert edad.iloc[0] == 0
    assert en_construccion.iloc[0]


def test_parsear_antiguedad_mayor_al_maximo_da_nan():
    assert np.isnan(_antiguedad("200 años")[0].iloc[0])


def test_parsear_antiguedad_vacio_da_nan():
    assert np.isnan(_antiguedad(None)[0].iloc[0])


# ---------------------------------------------------------------------------
# parsear_expensas
# ---------------------------------------------------------------------------

def _expensas(texto):
    monto, moneda = parsear_expensas(pd.Series([texto]))
    return monto.iloc[0], moneda.iloc[0]


def test_parsear_expensas_en_pesos():
    assert _expensas("290.000 ARS") == (290000, "ARS")


def test_parsear_expensas_cero_es_no_informado():
    assert np.isnan(_expensas("0 ARS")[0])


def test_parsear_expensas_monto_imposible_en_pesos_da_nan():
    assert np.isnan(_expensas("111.111.111.111 ARS")[0])


def test_parsear_expensas_usd_de_10000_o_mas_se_reinterpreta_como_pesos():
    assert _expensas("222.000 USD") == (222000, "ARS")


def test_parsear_expensas_usd_menor_a_10_da_nan():
    assert np.isnan(_expensas("1 USD")[0])


def test_parsear_expensas_usd_razonable_se_conserva():
    assert _expensas("150 USD") == (150, "USD")


# ---------------------------------------------------------------------------
# marcas_del_titulo
# ---------------------------------------------------------------------------

def _marcas(titulo):
    return marcas_del_titulo(pd.Series([titulo])).iloc[0]


def test_marcas_del_titulo_a_refaccionar():
    m = _marcas("Depto a refaccionar en Caballito")
    assert m["titulo_a_refaccionar"] and not m["titulo_reciclado"]


def test_marcas_del_titulo_para_reciclar_cuenta_como_a_refaccionar_y_no_como_reciclado():
    m = _marcas("Para reciclar, ideal reciclado")
    assert m["titulo_a_refaccionar"] and not m["titulo_reciclado"]


def test_marcas_del_titulo_reciclado():
    m = _marcas("Reciclado a nuevo")
    assert m["titulo_reciclado"] and not m["titulo_a_refaccionar"]


def test_marcas_del_titulo_a_estrenar_sin_importar_mayusculas():
    assert _marcas("A ESTRENAR")["titulo_a_estrenar"]


def test_marcas_del_titulo_con_renta_e_inquilino():
    assert _marcas("Venta con renta")["titulo_con_renta"]
    assert _marcas("Se vende con inquilino")["titulo_con_renta"]


def test_marcas_del_titulo_vacio_no_marca_nada():
    assert not _marcas(None).any()


# ---------------------------------------------------------------------------
# outliers_iqr_por_grupo
# ---------------------------------------------------------------------------

def test_outliers_iqr_marca_el_valor_extremo_del_grupo():
    valores = pd.Series(list(range(10, 20)) + [100])
    grupo = pd.Series(["a"] * 11)
    marca = outliers_iqr_por_grupo(valores, grupo)
    assert marca.tolist() == [False] * 10 + [True]


def test_outliers_iqr_no_evalua_grupos_chicos():
    valores = pd.Series([1, 2, 1000])
    grupo = pd.Series(["b"] * 3)
    assert not outliers_iqr_por_grupo(valores, grupo).any()


def test_outliers_iqr_se_calcula_dentro_de_cada_grupo():
    # 100 es normal en el grupo "caro" y atípico en el "barato"
    valores = pd.Series(list(range(10, 20)) + [100] + list(range(95, 106)))
    grupo = pd.Series(["barato"] * 11 + ["caro"] * 11)
    marca = outliers_iqr_por_grupo(valores, grupo)
    assert marca.iloc[10]
    assert not marca.iloc[11:].any()


def test_outliers_iqr_nan_no_se_marca():
    valores = pd.Series(list(range(10, 20)) + [np.nan])
    grupo = pd.Series(["a"] * 11)
    assert not outliers_iqr_por_grupo(valores, grupo).iloc[-1]


def test_marcas_casa_separa_tipo_casa_de_una_casa():
    titulos = pd.Series(["Depto tipo casa con patio", "Casa en Coghlan", "Duplex en Casa del Angel", None])
    from src.limpieza import marcas_casa
    marcas = marcas_casa(titulos)
    assert marcas["titulo_tipo_casa"].tolist() == [True, False, False, False]
    assert marcas["titulo_casa"].tolist() == [False, True, False, False]


def test_piso_desde_numero_de_unidad_se_queda_con_las_centenas():
    piso = pd.Series([903, 4, 114, None, 99])
    from src.limpieza import piso_desde_numero_de_unidad
    resultado = piso_desde_numero_de_unidad(piso)
    assert resultado.tolist()[:3] == [9, 4, 1]
    assert pd.isna(resultado.iloc[3])
    assert resultado.iloc[4] == 99
