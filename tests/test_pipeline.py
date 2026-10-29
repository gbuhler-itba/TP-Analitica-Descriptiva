"""
Tests de integración del pipeline, sin red.

Es la versión pytest de tests/verificar_offline.py: los mismos controles,
cada uno como una función test_... con nombre propio.

  etapa 1  Parseo del scraper contra HTML guardado en tests/fixtures/.
  etapa 2  unir_cuotas sobre las cuotas versionadas: SHA256 idéntico al
           consolidado versionado.
  etapa 3  geocoding_propiedades con las respuestas de USIG replayeadas desde
           el dataset geocodificado versionado: SHA256 idéntico.
  etapa 4  enriquecimiento con el GeoJSON de subte versionado: SHA256
           idéntico y las 93 columnas iguales.
  cadena   La salida de cada etapa es la entrada de la siguiente y no hay
           rutas absolutas en el código.

Cada etapa corre una sola vez por sesión (fixtures con scope="module") y
los tests miran su resultado. Tarda alrededor de 15 segundos.
"""

import hashlib

import pandas as pd
import pytest

from conftest import RAIZ
from src import enriquecimiento, geocoding_propiedades, scrapper_mercadolibre, unir_cuotas

FIXTURES = RAIZ / "tests" / "fixtures"
REF_CONSOLIDADO = RAIZ / "data" / "interim" / "mercadolibre_CABA_completo.tsv"
REF_GEOCODIFICADO = RAIZ / "data" / "interim" / "propiedades_geocodificadas.tsv"
REF_ENRIQUECIDO = RAIZ / "data" / "processed" / "propiedades_enriquecidas.tsv"
SUBTE_GEOJSON = RAIZ / "data" / "external" / "estaciones-de-subte.geojson"


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def test_datasets_de_referencia_versionados_existen():
    for ruta in (REF_CONSOLIDADO, REF_GEOCODIFICADO, REF_ENRIQUECIDO, SUBTE_GEOJSON):
        assert ruta.exists(), f"falta {ruta.relative_to(RAIZ)}"


# ---------------------------------------------------------------------------
# ETAPA 1 - parseo del scraper (sin red)
# ---------------------------------------------------------------------------

def test_parse_precio_simple():
    assert scrapper_mercadolibre.parse_precio("US$ 159.000") == ("USD", 159000, False)


def test_parse_precio_emprendimiento_marca_desde():
    assert scrapper_mercadolibre.parse_precio("Desde US$ 826.800") == ("USD", 826800, True)


def test_parse_precio_en_pesos():
    assert scrapper_mercadolibre.parse_precio("$ 45.000.000") == ("ARS", 45000000, False)


def test_parse_atributos_con_rangos_toma_el_minimo():
    attrs = scrapper_mercadolibre.parse_atributos("4 ambs.3 a 4 baños139 - 166 m² cubiertos")
    assert attrs == {"ambientes": 4, "dormitorios": None, "banos": 3, "m2": 139}


def test_normalizar_nombre_columna():
    assert scrapper_mercadolibre.normalizar_nombre_columna("Superficie total") == "superficie_total"


def test_construir_url_calcula_offset_de_paginacion():
    url = scrapper_mercadolibre.construir_url("palermo", 3, 48)
    assert "_Desde_97" in url


def test_parsear_caracteristicas_sobre_ficha_guardada():
    ficha = FIXTURES / "ficha_detalle.html"
    html = ficha.read_text(encoding="utf-8", errors="ignore")
    carac = scrapper_mercadolibre.parsear_caracteristicas(html)
    assert len(carac) > 0


# ---------------------------------------------------------------------------
# ETAPA 2 - consolidación
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def salida_etapa_2(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("etapa2")
    salida = tmp / "consolidado.tsv"
    codigo = unir_cuotas.main(["--salida", str(salida), "--logs-dir", str(tmp / "logs")])
    return codigo, salida


def test_etapa_2_unir_cuotas_corre_sin_error(salida_etapa_2):
    codigo, _ = salida_etapa_2
    assert codigo == 0


def test_etapa_2_sha256_identico_al_consolidado_versionado(salida_etapa_2):
    _, salida = salida_etapa_2
    assert sha256(salida) == sha256(REF_CONSOLIDADO)


# ---------------------------------------------------------------------------
# ETAPA 3 - geocodificación con USIG replayeado
# ---------------------------------------------------------------------------

class RespuestaFalsa:
    """Imita la respuesta de requests para replayear USIG."""

    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def construir_replay_usig():
    """Mapa dir_limpia -> respuesta de USIG, armado desde el dataset
    geocodificado versionado. Ninguna dirección tiene dos resultados distintos
    en la corrida original, así que el mapeo es determinista."""
    ref = pd.read_csv(REF_GEOCODIFICADO, sep="\t", low_memory=False,
                      dtype={"lat": str, "lon": str, "geo_status": str, "dir_limpia": str})
    replay = {}
    for direccion, lat, lon, status in zip(ref["dir_limpia"], ref["lat"], ref["lon"], ref["geo_status"]):
        if pd.isna(direccion) or direccion in replay:
            continue
        if status == "OK":
            replay[direccion] = {"direccionesNormalizadas": [{"coordenadas": {"x": float(lon), "y": float(lat)}}]}
        elif status == "SIN_COORDENADAS":
            replay[direccion] = {"direccionesNormalizadas": [{"coordenadas": {}}]}
        else:
            replay[direccion] = {"direccionesNormalizadas": []}
    return replay


@pytest.fixture(scope="module")
def salida_etapa_3(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("etapa3")
    replay = construir_replay_usig()
    llamadas = {"n": 0}

    def get_falso(url, params=None, timeout=None):
        llamadas["n"] += 1
        direccion = params["direccion"].rsplit(", caba", 1)[0]
        if direccion not in replay:
            raise AssertionError(f"dirección fuera del fixture: {direccion!r}")
        return RespuestaFalsa(replay[direccion])

    mp = pytest.MonkeyPatch()
    mp.setattr(geocoding_propiedades.requests, "get", get_falso)
    mp.setattr(geocoding_propiedades.time, "sleep", lambda *_a, **_k: None)
    try:
        salida = tmp / "geocodificado.tsv"
        codigo = geocoding_propiedades.main([
            "--salida", str(salida),
            "--parcial", str(tmp / "geocoding_parcial.tsv"),
            "--logs-dir", str(tmp / "logs"),
            "--guardar-cada", "1000000000",
            "--reportar-cada", "5000",
            "--sin-resume",
        ])
    finally:
        mp.undo()
    return {"codigo": codigo, "salida": salida, "replay": replay, "llamadas": llamadas["n"]}


def test_etapa_3_replay_de_usig_tiene_direcciones(salida_etapa_3):
    assert len(salida_etapa_3["replay"]) > 0


def test_etapa_3_geocoding_corre_sin_error(salida_etapa_3):
    assert salida_etapa_3["codigo"] == 0


def test_etapa_3_las_llamadas_a_usig_se_replayean(salida_etapa_3):
    assert salida_etapa_3["llamadas"] > 0


def test_etapa_3_sha256_identico_al_geocodificado_versionado(salida_etapa_3):
    assert sha256(salida_etapa_3["salida"]) == sha256(REF_GEOCODIFICADO)


# ---------------------------------------------------------------------------
# ETAPA 4 - enriquecimiento con el GeoJSON de subte versionado
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def salida_etapa_4(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("etapa4")
    salida = tmp / "enriquecido.tsv"
    codigo = enriquecimiento.main([
        "--salida", str(salida),
        "--logs-dir", str(tmp / "logs"),
        "--subte-geojson", str(SUBTE_GEOJSON),
    ])
    return codigo, salida


@pytest.fixture(scope="module")
def tablas_etapa_4(salida_etapa_4):
    _, salida = salida_etapa_4
    ref = pd.read_csv(REF_ENRIQUECIDO, sep="\t", low_memory=False)
    obt = pd.read_csv(salida, sep="\t", low_memory=False)
    return ref, obt


def columna_igual(a, b) -> bool:
    if a.dtype.kind == "f" and b.dtype.kind == "f":
        return bool((((a - b).abs() < 1e-9) | (a.isna() & b.isna())).all())
    return bool((a.fillna("<NA>").astype(str) == b.fillna("<NA>").astype(str)).all())


def test_etapa_4_enriquecimiento_corre_sin_error(salida_etapa_4):
    codigo, _ = salida_etapa_4
    assert codigo == 0


def test_etapa_4_misma_cantidad_de_filas(tablas_etapa_4):
    ref, obt = tablas_etapa_4
    assert len(obt) == len(ref)


def test_etapa_4_mismas_columnas_en_el_mismo_orden(tablas_etapa_4):
    ref, obt = tablas_etapa_4
    assert list(obt.columns) == list(ref.columns)


def test_etapa_4_sha256_identico_al_enriquecido_versionado(salida_etapa_4):
    _, salida = salida_etapa_4
    assert sha256(salida) == sha256(REF_ENRIQUECIDO)


@pytest.mark.parametrize("columna", ["dist_centralidad_m", "dist_transporte_m", "subzona"])
def test_etapa_4_columna_derivada_reproducida_exactamente(tablas_etapa_4, columna):
    ref, obt = tablas_etapa_4
    assert columna_igual(ref[columna], obt[columna])


def test_etapa_4_todas_las_columnas_coinciden(tablas_etapa_4):
    ref, obt = tablas_etapa_4
    distintas = [c for c in ref.columns if not columna_igual(ref[c], obt[c])]
    assert not distintas, f"difieren: {', '.join(distintas)}"


# ---------------------------------------------------------------------------
# ENCADENADO
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rutas_config():
    from src.configuracion import cargar_config
    from src.rutas import resolver

    rutas = cargar_config()["rutas"]
    return {clave: resolver(valor) for clave, valor in rutas.items()}


@pytest.mark.parametrize("clave", ["consolidado", "geocodificado", "enriquecido"])
def test_cadena_la_salida_de_cada_etapa_existe_donde_la_lee_la_siguiente(rutas_config, clave):
    assert rutas_config[clave].exists(), f"{clave}: {rutas_config[clave]}"


def test_cadena_etapa_1_escribe_donde_lee_la_etapa_2(rutas_config):
    assert rutas_config["cuotas_dir"].is_dir()


def test_ninguna_ruta_absoluta_en_el_codigo():
    encontradas = []
    for archivo in sorted((RAIZ / "src").glob("*.py")) + [RAIZ / "run_pipeline.py"]:
        texto = archivo.read_text(encoding="utf-8")
        for marca in ("/Users/", "C:\\\\", "/home/"):
            if marca in texto:
                encontradas.append(f"{archivo.name}: {marca}")
    assert not encontradas, "; ".join(encontradas)
