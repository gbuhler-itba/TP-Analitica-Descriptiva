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


OFICIALES = ["almagro", "balvanera", "belgrano", "boedo", "caballito", "flores", "nunez", "palermo", "parque patricios",
             "puerto madero", "recoleta", "retiro", "san cristobal", "villa crespo", "villa general mitre", "villa lugano"]


@pytest.mark.parametrize("titulo, barrio, esperado", [
    ("Departamento 5amb En Villa Lugano Av. General Paz 14600", "villa-general-mitre", ["villa lugano"]),   # testigo
    ("Departamento 2 Ambientes Venta Nuñez", "belgrano", ["nunez"]),                                       # sin tilde
    ("Venta 3 Ambientes En Boedo / Almagro Apto Crédito", "caballito", ["almagro", "boedo"]),
    ("Almagro: Boedo Y Rivadavia", "almagro", []),                 # nombra el barrio propio; además es una esquina
    ("2 Ambientes Sobre Av. Boedo", "almagro", []),                 # calle que se llama como un barrio
    ("Apto Credito - 3 Amb - Recoleta / Retiro", "recoleta", []),   # nombra el barrio propio
    ("Dúplex 6 Ambientes Vista Al Río - Recoleta", "barrio-norte", []),   # Barrio Norte equivale a Recoleta
    ("Departamento En Venta En Palermo Soho", "palermo", []),
    ("Monoambiente En Villa Crespo A Metros De Palermo", "villa-crespo", []),   # nombra el barrio propio
    ("Monoambiente A Metros De Palermo", "villa-crespo", ["palermo"]),
])
def test_barrio_dudoso_por_el_titulo(titulo, barrio, esperado):
    from src.eda import nombre_barrio
    assert exportar_dashboard.menciona_otro_barrio(titulo, nombre_barrio(barrio), OFICIALES) == esperado


@pytest.mark.parametrize("titulo, esperado", [
    ("4 Departamentos En Block En Venta En Liniers", True),        # testigo
    ("Departamentos Venta Puerto Madero", True),                    # plural: posible, no confirmado
    ("Venta 7 Deptos En Block Congreso Renta 10% Anual", True),
    ("Deptos A Estrenar En Venta - 1, Y 2 Ambientes - Piedrabuena 4700", True),
    ("Oportunidad!! Recoleta Venta Dos Departamentos Unidos (2 Y 3 Amb.) Apto Profesional", False),   # una sola unidad
    ("Semipiso 4 Ambientes Unificados Con Cochera", False),
    ("Departamento 3 Ambientes En Venta En Flores", False),
])
def test_posible_venta_de_varias_unidades(titulo, esperado):
    assert exportar_dashboard.posible_varias_unidades(titulo) is esperado


@pytest.mark.parametrize("titulo, esperado", [
    ("Venta Hotel 24 Habilitado Constitucion Permuta Financia", True),
    ("Apart Hotel En Venta Recoleta", True),
    ("Oficina En Venta En Retiro", True),
    ("Departamento 3 Ambientes Con Balcón", False),
])
def test_uso_no_residencial_incluye_hoteles(titulo, esperado):
    import re
    assert bool(re.search(exportar_dashboard.REGEX_USO_NO_RESIDENCIAL, titulo, re.I)) is esperado


@pytest.mark.parametrize("titulo, esperado", [
    ("Venta Departamento Monoambiente Constitución A Estrenar Con Financiacion", True),
    ("Monoambiente En Venta - Recoleta- Anticipo + Cuotas Fijas", True),
    ("3 Ambientes 64 M2 Reciclado Financiamiento Directo", True),
    ("Venta Departamento 4 Ambientes Apto Crédito", False),   # apto crédito no es financiación del vendedor
])
def test_precio_posiblemente_con_financiacion(titulo, esperado):
    import re
    assert bool(re.search(exportar_dashboard.REGEX_FINANCIACION, exportar_dashboard.normalizar(titulo))) is esperado


def test_exclusiones_nuevas_en_los_casos_testigo(exportado):
    """Las reglas de barrio dudoso y varias unidades marcan los testigos y no tocan la lista oficial."""
    cfg, avisos, resumen, salida = exportado
    por_id = {a["id"]: a for a in avisos}
    if "MLA3650073484" in por_id:
        assert exportar_dashboard.EXCLUSION_BARRIO_DUDOSO in por_id["MLA3650073484"]["exclusiones"]
        assert por_id["MLA3650073484"]["lat"] is None
    if "MLA2837616540" in por_id:
        assert exportar_dashboard.EXCLUSION_VARIAS_UNIDADES in por_id["MLA2837616540"]["exclusiones"]
    if "MLA1942707213" in por_id:   # "dos departamentos unidos": una sola unidad, no se marca
        assert exportar_dashboard.EXCLUSION_VARIAS_UNIDADES not in por_id["MLA1942707213"]["exclusiones"]
    if "MLA1961460081" in por_id:   # monoambiente a estrenar con financiación: sale del top, sigue en la lista
        assert exportar_dashboard.EXCLUSION_FINANCIACION in por_id["MLA1961460081"]["exclusiones"]
    if "MLA3571943468" in por_id:   # hotel: uso no residencial
        assert "uso comercial u oficina" in por_id["MLA3571943468"]["exclusiones"]
    # Barrio dudoso solo aplica a avisos sin coordenadas
    assert all(a["lat"] is None for a in avisos if exportar_dashboard.EXCLUSION_BARRIO_DUDOSO in a["exclusiones"])
    # Financiación coincide con la señal de revisión del pipeline; en pozo nunca es candidato
    assert all(("financ" in a["riesgo_revisar"]) == (exportar_dashboard.EXCLUSION_FINANCIACION in a["exclusiones"]) for a in avisos)
    assert all(a["nivel"] != regla.CANDIDATO for a in avisos if exportar_dashboard.EXCLUSION_EN_POZO in a["exclusiones"])
    # Las exclusiones no cambian señales, candidatos ni firmes: esos vienen de la etapa 6 y del escenario conservador
    embudo = {e["paso"]: e["unidades"] for e in resumen["embudo"]}
    assert len(avisos) == embudo["cumple_regla"]
    assert sum(a["nivel"] == regla.CANDIDATO for a in avisos) == embudo["candidato"]
    assert sum(a["firme"] for a in avisos) == resumen["sensibilidad"]["conservador"]
    # El resumen por barrio suma lo mismo que el total
    barrios = resumen["barrios"]
    assert sum(b["senales"] for b in barrios) == embudo["cumple_regla"]
    assert sum(b["candidatos"] for b in barrios) == embudo["candidato"]
    assert sum(b["avisos"] for b in barrios) == resumen["indicadores"]["avisos_analizados"]
    assert all(b["candidatos"] <= b["senales"] <= b["unidades"] for b in barrios)


def test_la_alerta_de_segmento_no_cambia_la_lista_destacada(exportado):
    """El segmento del notebook 06 es descriptivo: la alerta se muestra, no excluye ni descarta."""
    cfg, avisos, resumen, salida = exportado
    nombres = {"Chicos y recientes", "Compactos de edificio antiguo", "Nuevos con amenities",
               "Familiares amplios y antiguos"}
    assert all(a["segmento"] in nombres for a in avisos)
    i = resumen["indicadores"]
    assert i["segmento_alerta"] == exportar_dashboard.SEGMENTO_ALERTA in nombres
    assert i["error_mediano_segmento_alerta_pct"] > i["error_mediano_pct"]
    assert 0 < i["avisos_segmento_alerta_pct"] < 50
    destacados = [a for a in avisos if a["nivel"] == regla.CANDIDATO and a["consenso"] and not a["exclusiones"]]
    # Conteos del 04/11 con todas las exclusiones: la alerta no saca a nadie de la lista destacada ni de los firmes
    assert len(destacados) == 486
    assert sum(a["firme"] for a in destacados) == 38
    con_alerta = [a for a in destacados if a["segmento"] == i["segmento_alerta"]]
    assert con_alerta and any(a["firme"] for a in con_alerta)
    assert not any("segmento" in e or "tipo" in e for a in avisos for e in a["exclusiones"])


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


def test_las_estaciones_de_todos_los_modos_estan_en_latitud_y_longitud(exportado):
    # El premetro viene en metros (POSGAR 2007 / CABA 2019): sin reproyectar, el mapa no lo mostraba
    cfg, _, _, salida = exportado
    capas = json.loads((salida / "estaciones.json").read_text(encoding="utf-8"))
    assert set(capas) == {"subte", "tren", "metrobus", "premetro"}
    for modo, puntos in capas.items():
        assert len(puntos) > 0, modo
        assert all(-34.8 < p["lat"] < -34.5 and -58.6 < p["lon"] < -58.3 for p in puntos), modo
    # Las mismas coordenadas que usa el análisis para dist_premetro_m
    from src import fuentes_externas
    premetro = fuentes_externas.cargar_estaciones(resolver(cfg["fuentes_externas"]["rutas"]["premetro"]))
    exportadas = sorted((p["lat"], p["lon"]) for p in capas["premetro"])
    assert len(exportadas) == len(premetro)
    assert np.allclose(exportadas, sorted(map(tuple, np.round(premetro, 5))), atol=1e-5)


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


def test_el_estado_del_segundo_relevamiento_no_cambia_ninguna_lista(exportado):
    """Cada aviso lleva su estado al 28/10 (seguimiento_avisos.csv) y eso no toca los conteos del dashboard."""
    cfg, avisos, resumen, salida = exportado
    seg = pd.read_csv(resolver(cfg["rutas"]["seguimiento"])).set_index("id_aviso")["estado"]
    assert all(a["estado_r2"] in {"sigue", "republicado", "salio"} for a in avisos)
    assert all(a["estado_r2"] == seg[a["id"]] for a in avisos)
    salieron = np.mean([a["estado_r2"] == "salio" for a in avisos])
    assert 0.45 < salieron < 0.6   # "la mitad ya no estaba publicada al 28/10", en la línea del resumen
    destacados = [a for a in avisos if a["nivel"] == regla.CANDIDATO and a["consenso"] and not a["exclusiones"]]
    assert len(destacados) == 486 and sum(a["firme"] for a in destacados) == 38
