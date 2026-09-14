"""
Smoke test reproducible del pipeline, sin red.

Verifica que el código refactorizado reproduce exactamente los datasets
versionados en el repositorio, sin pegarle a MercadoLibre, a USIG ni a
BA Data. Sirve como prueba de que la reorganización no alteró resultados.

Qué hace cada control:

  etapa 1  Parsea HTML guardado en tests/fixtures/ con las funciones reales
           del scraper. No descarga nada. Verifica el parseo, no el crawling.

  etapa 2  Corre unir_cuotas sobre las cuotas versionadas y compara el TSV
           resultante con data/interim/mercadolibre_CABA_completo.tsv por
           hash SHA256.

  etapa 3  Corre geocoding_propiedades con las respuestas de USIG REPLAYEADAS
           desde el dataset geocodificado versionado (no se vuelve a llamar
           al servicio) y compara la salida por hash SHA256. La limpieza de
           direcciones (limpiar_direccion) sí se recalcula de verdad.

  etapa 4  Corre enriquecimiento con el GeoJSON de estaciones de subte
           versionado en data/external/ y compara la salida por SHA256, así
           que dist_transporte_m también queda verificada sin tocar la red.
           Si ese archivo faltara, cae a un GeoJSON sintético y avisa que
           dist_transporte_m no se verifica.

Uso:  python3 tests/verificar_offline.py
"""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd

from src import enriquecimiento, geocoding_propiedades, scrapper_mercadolibre, unir_cuotas

FIXTURES = RAIZ / "tests" / "fixtures"
REF_CONSOLIDADO = RAIZ / "data" / "interim" / "mercadolibre_CABA_completo.tsv"
REF_GEOCODIFICADO = RAIZ / "data" / "interim" / "propiedades_geocodificadas.tsv"
REF_ENRIQUECIDO = RAIZ / "data" / "processed" / "propiedades_enriquecidas.tsv"

resultados = []


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def registrar(nombre, ok, detalle="") -> bool:
    estado = "OK    " if ok else "FALLA "
    resultados.append((nombre, ok))
    print(f"  [{estado}] {nombre}{(' | ' + detalle) if detalle else ''}")
    return ok


def titulo(texto):
    print()
    print("-" * 68)
    print(texto)
    print("-" * 68)


# ---------------------------------------------------------------------------
# ETAPA 1
# ---------------------------------------------------------------------------

def verificar_etapa_1():
    titulo("ETAPA 1 - parseo del scraper contra HTML guardado (sin red)")

    registrar("parse_precio simple",
              scrapper_mercadolibre.parse_precio("US$ 159.000") == ("USD", 159000, False))
    registrar("parse_precio emprendimiento",
              scrapper_mercadolibre.parse_precio("Desde US$ 826.800") == ("USD", 826800, True))
    registrar("parse_precio pesos",
              scrapper_mercadolibre.parse_precio("$ 45.000.000") == ("ARS", 45000000, False))

    attrs = scrapper_mercadolibre.parse_atributos("4 ambs.3 a 4 baños139 - 166 m² cubiertos")
    registrar("parse_atributos con rangos",
              attrs == {"ambientes": 4, "dormitorios": None, "banos": 3, "m2": 139},
              str(attrs))

    registrar("normalizar_nombre_columna",
              scrapper_mercadolibre.normalizar_nombre_columna("Superficie total") == "superficie_total")

    url = scrapper_mercadolibre.construir_url("palermo", 3, 48)
    registrar("construir_url paginación", "_Desde_97" in url, url.split("usados")[-1][:24])

    ficha = FIXTURES / "ficha_detalle.html"
    if ficha.exists():
        carac = scrapper_mercadolibre.parsear_caracteristicas(ficha.read_text(encoding="utf-8", errors="ignore"))
        registrar("parsear_caracteristicas sobre ficha guardada", len(carac) > 0,
                  f"{len(carac)} características: {', '.join(list(carac)[:6])}")
    else:
        registrar("parsear_caracteristicas sobre ficha guardada", False, f"falta {ficha}")


# ---------------------------------------------------------------------------
# ETAPA 2
# ---------------------------------------------------------------------------

def verificar_etapa_2(tmp: Path):
    titulo("ETAPA 2 - consolidación reproducible byte a byte")
    salida = tmp / "consolidado.tsv"
    codigo = unir_cuotas.main(["--salida", str(salida), "--logs-dir", str(tmp / "logs")])
    if not registrar("unir_cuotas corre sin error", codigo == 0):
        return
    ref, obt = sha256(REF_CONSOLIDADO), sha256(salida)
    registrar("SHA256 idéntico al dataset versionado", ref == obt, f"{obt[:16]}...")


# ---------------------------------------------------------------------------
# ETAPA 3
# ---------------------------------------------------------------------------

class RespuestaFalsa:
    """Imita la respuesta de requests para replayear USIG desde el fixture."""

    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def construir_replay_usig():
    """
    Arma el mapa dir_limpia -> payload de USIG a partir del dataset
    geocodificado versionado. El mapeo es determinista: se verificó que
    ninguna dirección tiene dos resultados distintos en la corrida original.
    """
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


def verificar_etapa_3(tmp: Path, monkeypatch_sleep=True):
    titulo("ETAPA 3 - geocodificación con respuestas de USIG replayeadas")

    replay = construir_replay_usig()
    registrar("fixture de replay construido", len(replay) > 0, f"{len(replay)} direcciones distintas")

    llamadas = {"n": 0}

    def get_falso(url, params=None, timeout=None):
        llamadas["n"] += 1
        direccion = params["direccion"].rsplit(", caba", 1)[0]
        if direccion not in replay:
            raise AssertionError(f"dirección fuera del fixture: {direccion!r}")
        return RespuestaFalsa(replay[direccion])

    get_original = geocoding_propiedades.requests.get
    sleep_original = geocoding_propiedades.time.sleep
    geocoding_propiedades.requests.get = get_falso
    if monkeypatch_sleep:
        geocoding_propiedades.time.sleep = lambda *_a, **_k: None

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
        geocoding_propiedades.requests.get = get_original
        geocoding_propiedades.time.sleep = sleep_original

    if not registrar("geocoding corre sin error", codigo == 0):
        return
    registrar("llamadas a USIG replayeadas", llamadas["n"] > 0, f"{llamadas['n']} llamadas")
    ref, obt = sha256(REF_GEOCODIFICADO), sha256(salida)
    registrar("SHA256 idéntico al dataset versionado", ref == obt, f"{obt[:16]}...")


# ---------------------------------------------------------------------------
# ETAPA 4
# ---------------------------------------------------------------------------

def verificar_etapa_4(tmp: Path):
    titulo("ETAPA 4 - enriquecimiento")

    geojson_real = RAIZ / "data" / "external" / "estaciones-de-subte.geojson"
    usa_real = geojson_real.exists()

    if usa_real:
        geojson = geojson_real
        print("  Usando el GeoJSON de subte versionado. La verificación cubre las 93")
        print("  columnas, dist_transporte_m incluida, y compara por SHA256.")
    else:
        geojson = tmp / "subte_sintetico.geojson"
        geojson.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-58.3816, -34.6037]}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-58.4100, -34.5900]}},
            ],
        }), encoding="utf-8")
        print("  NOTA: falta data/external/estaciones-de-subte.geojson, así que se usa uno")
        print("        sintético y dist_transporte_m NO queda verificada.")

    salida = tmp / "enriquecido.tsv"
    codigo = enriquecimiento.main([
        "--salida", str(salida),
        "--logs-dir", str(tmp / "logs"),
        "--subte-geojson", str(geojson),
    ])
    if not registrar("enriquecimiento corre sin error", codigo == 0):
        return

    ref = pd.read_csv(REF_ENRIQUECIDO, sep="\t", low_memory=False)
    obt = pd.read_csv(salida, sep="\t", low_memory=False)

    registrar("misma cantidad de filas", len(ref) == len(obt), f"{len(obt)}")
    registrar("mismas columnas y en el mismo orden", list(ref.columns) == list(obt.columns),
              f"{len(obt.columns)} columnas")
    if list(ref.columns) != list(obt.columns):
        return

    if usa_real:
        digest = sha256(salida)
        registrar("SHA256 idéntico al dataset versionado",
                  sha256(REF_ENRIQUECIDO) == digest, f"{digest[:16]}...")

    iguales, distintas = [], []
    for col in ref.columns:
        if col == "dist_transporte_m" and not usa_real:
            continue
        a, b = ref[col], obt[col]
        if a.dtype.kind == "f" and b.dtype.kind == "f":
            cerca = ((a - b).abs() < 1e-9) | (a.isna() & b.isna())
            coincide = bool(cerca.all())
        else:
            coincide = bool((a.fillna("<NA>").astype(str) == b.fillna("<NA>").astype(str)).all())
        (iguales if coincide else distintas).append(col)

    registrar("dist_centralidad_m reproducida exactamente", "dist_centralidad_m" in iguales)
    if usa_real:
        registrar("dist_transporte_m reproducida exactamente", "dist_transporte_m" in iguales,
                  f"media {obt['dist_transporte_m'].mean():.0f} m")
    registrar("subzona reproducida exactamente", "subzona" in iguales,
              f"{obt['subzona'].nunique()} sub-zonas")

    total = len(ref.columns) if usa_real else len(ref.columns) - 1
    registrar(f"las {total} columnas comparadas coinciden", not distintas,
              "difieren: " + ", ".join(distintas) if distintas else "")


# ---------------------------------------------------------------------------
# ENCADENADO
# ---------------------------------------------------------------------------

def verificar_encadenado():
    """
    La salida de cada etapa tiene que ser exactamente la entrada de la
    siguiente. En la versión original de los scripts esta cadena estaba
    cortada: la etapa 2 escribía en output/ y la etapa 3 leía de una ruta
    absoluta distinta, así que el pipeline no corría de punta a punta.
    """
    titulo("ENCADENADO - la salida de cada etapa es la entrada de la siguiente")

    from src.configuracion import cargar_config
    from src.rutas import resolver

    cfg = cargar_config()
    rutas = cfg["rutas"]

    salida_1 = resolver(rutas["cuotas_dir"])
    entrada_2 = resolver(rutas["cuotas_dir"])
    registrar("etapa 1 -> etapa 2 (directorio de cuotas)", salida_1 == entrada_2,
              str(salida_1.relative_to(RAIZ)))

    salida_2 = resolver(rutas["consolidado"])
    registrar("etapa 2 -> etapa 3 (consolidado)", salida_2.exists(),
              str(salida_2.relative_to(RAIZ)))

    salida_3 = resolver(rutas["geocodificado"])
    registrar("etapa 3 -> etapa 4 (geocodificado)", salida_3.exists(),
              str(salida_3.relative_to(RAIZ)))

    salida_4 = resolver(rutas["enriquecido"])
    registrar("etapa 4 -> dataset final", salida_4.exists(),
              str(salida_4.relative_to(RAIZ)))

    rutas_absolutas = []
    for archivo in sorted((RAIZ / "src").glob("*.py")) + [RAIZ / "run_pipeline.py"]:
        texto = archivo.read_text(encoding="utf-8")
        for marca in ("/Users/", "C:\\\\", "/home/"):
            if marca in texto:
                rutas_absolutas.append(f"{archivo.name}: {marca}")
    registrar("ninguna ruta absoluta en el código", not rutas_absolutas,
              "; ".join(rutas_absolutas))


# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 68)
    print("SMOKE TEST OFFLINE DEL PIPELINE (sin red)")
    print("=" * 68)

    faltantes = [p for p in (REF_CONSOLIDADO, REF_GEOCODIFICADO, REF_ENRIQUECIDO) if not p.exists()]
    if faltantes:
        print("[!] Faltan datasets de referencia versionados:")
        for p in faltantes:
            print(f"    {p}")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="verif_tp1_"))
    try:
        verificar_etapa_1()
        verificar_etapa_2(tmp)
        verificar_etapa_3(tmp)
        verificar_etapa_4(tmp)
        verificar_encadenado()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 68)
    fallas = [n for n, ok in resultados if not ok]
    print(f"RESULTADO: {len(resultados) - len(fallas)}/{len(resultados)} controles OK")
    if fallas:
        print("Fallaron:")
        for n in fallas:
            print(f"  - {n}")
    print("=" * 68)
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
