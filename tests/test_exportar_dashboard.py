"""La capa de datos del dashboard tiene que coincidir con las salidas de la etapa 6."""

import json

import numpy as np
import pandas as pd
import pytest

from src import exportar_dashboard, regla, validacion
from src.configuracion import cargar_config
from src.rutas import resolver


@pytest.fixture(scope="module")
def exportado(tmp_path_factory):
    cfg = cargar_config()
    if not resolver(cfg["rutas"]["precio_esperado"]).exists():
        pytest.skip("faltan las salidas de la etapa 6")
    salida = tmp_path_factory.mktemp("dashboard")
    avisos, resumen = exportar_dashboard.exportar(cfg, salida)
    return cfg, avisos, resumen, salida


def test_conteos_coinciden_con_el_embudo(exportado):
    cfg, avisos, resumen, salida = exportado
    embudo = {e["paso"]: e["unidades"] for e in resumen["embudo"]}
    assert len(avisos) == embudo["cumple_regla"] == resumen["indicadores"]["senales_unidades"]
    assert sum(a["nivel"] == regla.CANDIDATO for a in avisos) == embudo["candidato"]
    assert resumen["indicadores"]["candidatos_unidades"] == embudo["candidato"]
    assert resumen["sensibilidad"]["base"] == embudo["candidato"]
    assert resumen["sensibilidad"]["conservador"] <= resumen["sensibilidad"]["base"]
    # Candidato firme: el escenario conservador, por unidad, marcado en cada aviso y en cada barrio
    firmes = sum(a["firme"] for a in avisos)
    assert firmes == resumen["indicadores"]["candidatos_firmes_unidades"] == resumen["sensibilidad"]["conservador"]
    assert all(a["nivel"] == regla.CANDIDATO for a in avisos if a["firme"])
    assert sum(b["firmes"] for b in resumen["barrios"]) == firmes
    assert all(b["firmes"] <= b["candidatos"] for b in resumen["barrios"])
    # Lista destacada: candidatos de los dos modelos sin exclusiones; los motivos salen de las marcas exportadas
    destacados = [a for a in avisos if a["nivel"] == regla.CANDIDATO and a["consenso"] and not a["exclusiones"]]
    assert len(destacados) == resumen["indicadores"]["destacados_unidades"] > 0
    assert sum(a["firme"] for a in destacados) == resumen["indicadores"]["destacados_firmes_unidades"]
    for a in avisos:
        assert ("barrio popular" in a["exclusiones"]) >= a["titulo_barrio_popular"]
        assert ("casa" in a["exclusiones"]) >= a["titulo_casa"]
        if a["dist_barrio_popular_m"] is not None and a["dist_barrio_popular_m"] < exportar_dashboard.RADIO_BARRIO_POPULAR_M:
            assert any("barrio popular" in e for e in a["exclusiones"])
    assert any("PH" in a["exclusiones"] for a in avisos)
    assert any("uso comercial u oficina" in a["exclusiones"] for a in avisos)
    # El resumen por barrio suma lo mismo que el total
    barrios = resumen["barrios"]
    assert sum(b["senales"] for b in barrios) == embudo["cumple_regla"]
    assert sum(b["candidatos"] for b in barrios) == embudo["candidato"]
    assert sum(b["avisos"] for b in barrios) == resumen["indicadores"]["avisos_analizados"]
    assert all(b["candidatos"] <= b["senales"] <= b["unidades"] for b in barrios)


def test_los_json_son_validos_y_sin_nan(exportado):
    cfg, avisos, resumen, salida = exportado
    for nombre in ["avisos.json", "resumen.json", "estaciones.json", "fondo.json"]:
        texto = (salida / nombre).read_text(encoding="utf-8")
        assert "NaN" not in texto
        json.loads(texto)
    assert all(a["lat"] is None or -35 < a["lat"] < -34 for a in avisos)
    assert all(isinstance(a["factores"], list) for a in avisos)
    fondo = json.loads((salida / "fondo.json").read_text(encoding="utf-8"))
    assert len(fondo["puntos"]) == sum(b["con_coordenadas"] for b in resumen["barrios"])
    assert len(fondo["barrios"]) == len(fondo["nombres"])
    deciles = resumen["salida_por_brecha"]
    assert len(deciles) == 10 and all(d["ic_inf_pct"] <= d["tasa_pct"] <= d["ic_sup_pct"] for d in deciles)


def test_el_simulador_puede_reproducir_la_brecha_neta_base(exportado):
    """Con los campos exportados y los parámetros base, la regla reproduce la brecha neta de la etapa 6."""
    cfg, avisos, resumen, salida = exportado
    costos = validacion.cargar_reglas_titulo()
    df = pd.DataFrame({
        "precio_usd": [a["precio_usd"] for a in avisos], "m2_final": [a["m2"] for a in avisos],
        "precio_m2_esperado": [a["precio_m2_esperado"] for a in avisos],
        "precio_m2_esperado_inf": [a["precio_m2_inf"] for a in avisos],
        "estado_titulo": [a["estado"] for a in avisos],
    })
    calculo = regla.calcular(df, resumen["primas_estado"], costos)
    exportada = np.array([a["brecha_neta_pct"] for a in avisos])
    assert np.allclose(100 * calculo["brecha_neta"].values, exportada, atol=0.15)
    assert resumen["parametros_costos"]["base"]["negociacion"] == pytest.approx(0.0479)
