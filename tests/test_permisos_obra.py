"""Tests de src/permisos_obra.py: funciones puras con casos chicos y una
corrida completa sobre el snapshot versionado (sin red)."""

import numpy as np
import pandas as pd
import pytest

from conftest import RAIZ
from src import permisos_obra
from src.permisos_obra import calcular, contar_en_radio, filtrar_permisos, parsear_punto_wkt

OBELISCO = (-34.60372, -58.38159)
# 1 grado de latitud mide ~111.195 m, así que 0,004° ~ 445 m y 0,005° ~ 556 m
A_445_M = (OBELISCO[0] + 0.004, OBELISCO[1])
A_556_M = (OBELISCO[0] + 0.005, OBELISCO[1])


def test_parsear_punto_wkt_invierte_lon_lat():
    puntos = parsear_punto_wkt(pd.Series(["POINT(-58.4498845747938 -34.6229797647752)"]))
    assert puntos.iloc[0].tolist() == [-34.6229797647752, -58.4498845747938]


def _permisos(*filas):
    df = pd.DataFrame(filas, columns=["fecha", "descripcio", "smp"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    # Un punto distinto por parcela, salvo que el test lo pise
    df["wkt_2"] = [f"POINT(-58.4 -34.{i:04d})" for i in pd.factorize(df["smp"])[0]]
    return df


def test_filtrar_permisos_deja_solo_tramites_de_obra():
    df = _permisos(
        ("2025-01-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "001"),
        ("2025-01-01", "REGISTRO DE PROYECTO DE INSTALACIÓN VENTILACIÓN MECÁNICA", "002"),
        ("2025-01-01", "PERMISO DE DEMOLICION", "003"),
    )
    assert filtrar_permisos(df)["smp"].tolist() == ["001"]


def test_filtrar_permisos_respeta_la_ventana_de_3_anios_antes_del_scraping():
    obra = "PERMISO DE EJECUCION DE OBRA CIVIL"
    df = _permisos(
        ("2023-08-13", obra, "antes_de_la_ventana"),
        ("2023-08-14", obra, "primer_dia"),
        ("2026-08-13", obra, "ultimo_dia"),
        ("2026-08-14", obra, "dia_del_scraping"),
    )
    assert sorted(filtrar_permisos(df)["smp"]) == ["primer_dia", "ultimo_dia"]


def test_filtrar_permisos_cuenta_una_vez_cada_parcela():
    df = _permisos(
        ("2024-01-01", "PERMISO TEMPRANO DE EJECUCION DE OBRA CIVIL", "001"),
        ("2024-06-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "001"),
        ("2024-06-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "002"),
    )
    assert len(filtrar_permisos(df)) == 2


def test_contar_en_radio_incluye_a_445_m_y_excluye_a_556_m():
    conteo = contar_en_radio([OBELISCO[0]], [OBELISCO[1]],
                             [A_445_M[0], A_556_M[0]], [A_445_M[1], A_556_M[1]], radio_m=500)
    assert conteo.tolist() == [1]


def test_contar_en_radio_sin_puntos_da_cero():
    assert contar_en_radio([OBELISCO[0]], [OBELISCO[1]], [], []).tolist() == [0]


def test_calcular_deja_vacio_el_aviso_sin_coordenadas():
    avisos = pd.DataFrame({
        "link": ["con_coords", "sin_coords"],
        "lat": [OBELISCO[0], np.nan],
        "lon": [OBELISCO[1], np.nan],
        "geo_status": ["OK", "SIN_RESULTADO"],
    })
    permisos = pd.DataFrame({"wkt_2": [f"POINT({A_445_M[1]} {A_445_M[0]})"]})
    salida = calcular(avisos, permisos)
    assert salida["link"].tolist() == ["con_coords", "sin_coords"]
    assert salida["permisos_obra_500m"].iloc[0] == 1
    assert pd.isna(salida["permisos_obra_500m"].iloc[1])


# ---------------------------------------------------------------------------
# Corrida completa sobre el snapshot versionado
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    salida = tmp_path_factory.mktemp("permisos") / "permisos_obra.tsv"
    codigo = permisos_obra.main(["--salida", str(salida)])
    return codigo, pd.read_csv(salida, sep="\t")


def test_permisos_obra_corre_sin_red_desde_el_snapshot(corrida):
    codigo, _ = corrida
    assert codigo == 0


def test_permisos_obra_una_fila_por_aviso_del_dataset_enriquecido(corrida):
    _, salida = corrida
    enriquecido = pd.read_csv(RAIZ / permisos_obra.ENTRADA, sep="\t", usecols=["link", "geo_status"])
    assert salida["link"].tolist() == enriquecido["link"].tolist()
    assert salida["link"].is_unique


def test_permisos_obra_completo_solo_para_avisos_geocodificados(corrida):
    _, salida = corrida
    enriquecido = pd.read_csv(RAIZ / permisos_obra.ENTRADA, sep="\t", usecols=["geo_status"])
    con_coords = (enriquecido["geo_status"] == "OK").values
    assert salida["permisos_obra_500m"][con_coords].notna().all()
    assert salida["permisos_obra_500m"][~con_coords].isna().all()


def test_permisos_obra_reproduce_el_tsv_versionado(corrida):
    _, salida = corrida
    versionado = pd.read_csv(RAIZ / permisos_obra.SALIDA, sep="\t")
    pd.testing.assert_frame_equal(salida, versionado)


def test_filtrar_permisos_cuenta_una_vez_la_obra_con_varias_parcelas_en_el_mismo_punto():
    df = _permisos(
        ("2025-03-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "005-037-010"),
        ("2025-03-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "005-037-008a"),
        ("2025-04-01", "PERMISO DE EJECUCION DE OBRA CIVIL", "otra"),
    )
    df.loc[1, "wkt_2"] = df.loc[0, "wkt_2"]   # misma obra, dos parcelas
    assert len(filtrar_permisos(df)) == 2
