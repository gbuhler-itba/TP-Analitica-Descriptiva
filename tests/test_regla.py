"""Tests de la regla de decisión (src/regla.py), con los costos reales de config/costos.yaml."""

import numpy as np
import pandas as pd
import pytest

from src import regla, validacion

COSTOS = validacion.cargar_reglas_titulo()


def test_costo_de_entrada_coincide_con_el_total_de_costos_yaml_y_aplica_el_umbral_de_sellos():
    p = regla.parametros(COSTOS)
    precio = pd.Series([100_000.0, 200_000.0, 30_000.0])
    entrada = regla.costo_entrada(precio, p)
    total = COSTOS["costos_entrada"]["total_costos_entrada"]["valor"] / 100
    assert entrada[0] == pytest.approx(total * 100_000)
    # Sobre el umbral de Sellos (USD 148.941) la alícuota total pasa de 2,7% a 3,5%: la mitad, 0,40 pp más
    assert entrada[1] == pytest.approx((total + 0.004) * 200_000)
    # En avisos chicos pesa el honorario mínimo del escribano
    minimo = COSTOS["costos_entrada"]["honorarios_escribano"]["minimo_absoluto_usd"]
    assert entrada[2] == pytest.approx(minimo + (total - 0.0242) * 30_000)


def test_refaccion_por_nivel():
    p = regla.parametros(COSTOS)
    m2 = pd.Series([60.0, 60.0, 60.0, 60.0])
    obra = regla.costo_refaccion(pd.Series(["ninguna", "liviana", "media", "integral"]), m2, p)
    assert list(obra) == [0, 105 * 60, 12950 + 105 * 60, 1227 * 60]


def _aviso(estado="sin_marca", precio=100_000.0, esperado_m2=2500.0, m2=60.0):
    return pd.DataFrame({"precio_usd": [precio], "m2_final": [m2], "precio_m2_esperado": [esperado_m2],
                         "precio_m2_esperado_inf": [0.8 * esperado_m2], "estado_titulo": [estado]})


def test_brecha_neta_a_mano():
    p = regla.parametros(COSTOS)
    r = regla.calcular(_aviso(), {}, COSTOS).iloc[0]
    venta = 2500 * 60 * (1 - p["negociacion"])
    salida = (p["comision_vendedor"] + p["certificados"] + 0.027 * 0.5) * venta
    costo = 100_000 * (1 + 0.0876) + 105 * 60
    assert r["costo_total_usd"] == pytest.approx(costo)
    assert r["brecha_neta"] == pytest.approx((venta - salida - costo) / costo)


def test_refaccionar_quita_la_prima_negativa_del_estado():
    primas = {"a_reciclar": -0.2, "a_estrenar": 0.1}
    reciclar = regla.calcular(_aviso("a_reciclar"), primas, COSTOS).iloc[0]
    assert reciclar["nivel_refaccion"] == "integral"
    assert reciclar["valor_salida_usd"] == pytest.approx(2500 * 60 * np.exp(0.2))
    # Una prima positiva no se quita, y un aviso que no se refacciona conserva su valor esperado
    estrenar = regla.calcular(_aviso("a_estrenar"), primas, COSTOS).iloc[0]
    assert estrenar["valor_salida_usd"] == pytest.approx(2500 * 60)


def test_ganancias_solo_sobre_ganancia_positiva_y_limite_inferior_es_mas_conservador():
    caro = regla.calcular(_aviso(precio=200_000.0), {}, COSTOS, ganancias=0.35).iloc[0]
    assert caro["resultado_usd"] < 0 and caro["impuesto_usd"] == 0
    barato = _aviso(precio=80_000.0)
    sin = regla.calcular(barato, {}, COSTOS).iloc[0]
    con = regla.calcular(barato, {}, COSTOS, ganancias=0.35).iloc[0]
    assert con["impuesto_usd"] == pytest.approx(0.35 * sin["resultado_usd"])
    inferior = regla.calcular(barato, {}, COSTOS, valor_salida="limite_inferior").iloc[0]
    assert inferior["brecha_neta"] < sin["brecha_neta"]


def test_escenarios_ordenados():
    aviso = _aviso(precio=90_000.0)
    brechas = {e: regla.calcular(aviso, {}, COSTOS, escenario=e).iloc[0]["brecha_neta"]
               for e in ["optimista", "base", "pesimista"]}
    assert brechas["optimista"] > brechas["base"] > brechas["pesimista"]


def test_decidir_niveles_y_motivos():
    cumple = pd.Series([True, True, True, False])
    brecha = pd.Series([0.15, 0.05, 0.30, 0.50])
    descartar = pd.Series(["", "", "en pozo", ""])
    candidato, nivel, motivo = regla.decidir(cumple, brecha, descartar, umbral=0.10)
    assert list(candidato) == [True, False, False, False]
    assert list(nivel) == [regla.CANDIDATO, regla.SENAL, regla.SENAL, ""]
    assert motivo[1] == "brecha neta 5% < 10%" and motivo[2] == "riesgo legal: en pozo" and motivo[0] == ""


def test_senales_legales_separa_descartar_de_revisar():
    df = pd.DataFrame({"riesgo_en_pozo": [True, False], "riesgo_con_inquilino": [True, False]})
    descartar, revisar = regla.senales_legales(df, COSTOS)
    assert list(descartar) == ["en pozo", ""] and list(revisar) == ["con inquilino", ""]
