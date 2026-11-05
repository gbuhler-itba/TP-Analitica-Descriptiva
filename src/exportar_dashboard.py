"""
Capa de datos del dashboard (docs/dashboard/data/*.json), a partir de las salidas de la etapa 6.

El dashboard es HTML estático (GitHub Pages) y no recalcula nada del modelo:
lee estos JSON. Lo único que recalcula en el navegador es la regla de
decisión del simulador, con los mismos parámetros de config/costos.yaml que
exporta este script (`parametros` de src/regla.py, por escenario).

SALIDAS (docs/dashboard/data/):
  avisos.json      una fila por unidad de la lista oficial (señales a investigar), con lo que
                   muestra la ficha y lo que necesita el simulador
  resumen.json     embudo, indicadores, resumen por barrio, sensibilidad de la regla, parámetros de
                   costos y metadatos
  estaciones.json  subte, tren, Metrobus y premetro (capas del mapa)
  fondo.json       todos los avisos con coordenadas (lat, lon, barrio): el fondo gris del mapa

Niveles de decisión: a los dos de la etapa 6 ("señal a investigar", "candidato
después de costos") el dashboard suma "candidato firme": candidato que sigue
dejando el margen mínimo aun vendiendo al límite inferior del rango del 80% (el
escenario conservador del notebook 07). Se calcula acá, por unidad, con la misma
regla.

Lista destacada del resumen: candidatos que marcan los dos modelos, sin los casos
que la PE2 mostró como especiales (barrio popular o a menos de 500 m de uno, casa
o PH), usos que no son vivienda (oficina, comercial, local, hotel), avisos sin
coordenadas cuyo título nombra otro barrio oficial ("barrio dudoso"), posibles
ventas de varias unidades (en block, departamentos en plural), precio posiblemente
con financiación (anticipo, cuotas) y en pozo. Cada aviso lleva sus
`exclusiones` (vacías si entra); el dashboard las muestra en la tabla y en la
ficha. Las exclusiones no tocan la lista oficial ni los candidatos de la etapa 6.
No existe una marca de "brecha extrema" en el pipeline: los casos extremos se
filtran antes como errores de carga (`senal_error_carga`).

Segmento de departamento: cada aviso lleva su segmento del notebook 06 (MCA
más K-means, misma semilla; `segmento_por_aviso`). En "Familiares amplios y
antiguos" el modelo tiene más error y el precio esperado tiende a quedar alto:
el dashboard muestra una alerta de revisión en la tabla y en la ficha. Es
descriptiva: no excluye de la lista destacada ni cambia ningún conteo.

Estado en el segundo relevamiento: cada aviso lleva `estado_r2` ("sigue",
"republicado" o "salio", de `seguimiento_avisos.csv`), para avisar en la ficha y
en las tablas que muchos ya no estaban publicados al 28/10. No cambia ningún
conteo ni ninguna lista.

Uso:  python3 src/exportar_dashboard.py
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import fuentes_externas, inferencia, regla, segmentos, validacion  # noqa: E402
from src.configuracion import agregar_argumento_config, cargar_config  # noqa: E402
from src.eda import nombre_barrio  # noqa: E402
from src.rutas import asegurar_directorio, resolver  # noqa: E402

SALIDA = RAIZ / "docs" / "dashboard" / "data"
ESCENARIOS = ["optimista", "base", "pesimista"]
ESTADOS = {"sin_marca": "sin marca en el título", "a_reciclar": "a reciclar", "a_refaccionar": "a refaccionar",
           "ya_reformado": "ya reformado", "a_estrenar": "a estrenar"}
# Motivos por los que un aviso no entra a la lista destacada del resumen ("los que más vale la pena mirar"):
# casos que la PE2 mostró como especiales (barrio popular, PH o casa) y usos que no son vivienda. Siguen en el
# mapa, en el buscador y en la ficha, con el motivo a la vista.
RADIO_BARRIO_POPULAR_M = 500
REGEX_PH = r"\bph\b"
REGEX_USO_NO_RESIDENCIAL = r"\boficinas?\b|comercial|\blocal(?:es)?\b|\bhotel(?:es)?\b|\bhostel\b|apart\s*-?\s*hotel"
# Precio posiblemente con financiación: el publicado puede ser un anticipo y no el total (misma regex que la
# señal "con_financiacion" de costos.yaml, que es de revisión; para la lista destacada se descarta).
REGEX_FINANCIACION = r"financ|anticipo|cuotas"
EXCLUSION_FINANCIACION = "precio posiblemente con financiación"
# En pozo: ya es de descarte en la regla de decisión (nunca es candidato); acá queda la alerta para la lista.
EXCLUSION_EN_POZO = "en pozo: precio no comparable con usados"
# Notebook 06: el tipo de departamento donde el modelo tiene más error y el precio esperado queda alto
SEGMENTO_ALERTA = "Familiares amplios y antiguos"
# Posible venta de varias unidades: "en block", "unidades", "departamentos" o "deptos" en plural. "Dos
# departamentos unidos" es una sola unidad física: "unidos" y "unificados" anulan la marca.
REGEX_VARIAS_UNIDADES = r"\ben\s+block\b|\bunidades\b|\bdepartamentos\b|\bd(?:e)?ptos\.?\b"
REGEX_UNA_UNIDAD = r"\bunid[oa]s\b|\bunificad[oa]s\b"
# Barrio dudoso: sin coordenadas y el título nombra otro barrio oficial. "Barrio Norte" es una categoría
# del portal dentro de Recoleta. Se ignora el nombre si va después de "av./calle/pasaje" (una calle que se
# llama como un barrio), si forma una esquina con una calle ("Boedo y Rivadavia") o si el título también
# nombra el barrio propio ("Recoleta / Retiro").
EQUIVALENCIAS_BARRIO = {"barrio norte": "recoleta"}
REGEX_CALLE_ANTES = re.compile(r"(?:\bav\.?|\bavenida|\bcalle|\bpasaje|\bpje\.?)\s*$")
EXCLUSION_BARRIO_DUDOSO = "barrio dudoso"
EXCLUSION_VARIAS_UNIDADES = "posible venta de varias unidades"


def normalizar(texto):
    """Minúsculas y sin tildes, para comparar nombres de barrios con títulos."""
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()


def barrios_oficiales(cfg_fe):
    """Nombres normalizados de los 48 barrios oficiales (BA Data), con "gral." como "general"."""
    g = json.load(open(resolver(cfg_fe["rutas"]["barrios"]), encoding="utf-8"))
    return sorted({normalizar(f["properties"]["nombre"]).replace("gral.", "general") for f in g["features"]})


def menciona_otro_barrio(titulo, barrio_busqueda, oficiales):
    """Barrios oficiales distintos al de búsqueda que el título nombra (lista vacía si ninguno)."""
    t = normalizar(titulo)
    propio = normalizar(barrio_busqueda)
    propio = EQUIVALENCIAS_BARRIO.get(propio, propio)
    patrones = {b: re.compile(r"(?<![a-z])" + re.escape(b).replace(r"\ ", r"\s+") + r"(?![a-z])") for b in oficiales}
    if propio in patrones and patrones[propio].search(t):
        return []
    otros = []
    for b, p in patrones.items():
        if b == propio or b in propio or propio in b:
            continue
        for m in p.finditer(t):
            if REGEX_CALLE_ANTES.search(t[:m.start()]):
                continue
            despues = re.match(r"\s+y\s+([a-z]+)", t[m.end():])
            if despues and not any(o.startswith(despues.group(1)) for o in oficiales):
                continue
            otros.append(b)
            break
    return otros


def posible_varias_unidades(titulo):
    """True si el título sugiere una venta en block o varias unidades (y no "unidos" o "unificados")."""
    t = normalizar(titulo)
    return bool(re.search(REGEX_VARIAS_UNIDADES, t)) and not re.search(REGEX_UNA_UNIDAD, t)


def _limpio(v):
    """Valores aptos para JSON: NaN -> None, numpy -> Python."""
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 2)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v


def commit_actual():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=RAIZ,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "desconocido"


def unidades_firmes(precio, costos, umbral):
    """Unidades candidatas aun vendiendo al límite inferior del rango del 80% (candidato firme)."""
    senales = precio[precio["cumple_regla"]]
    primas = senales.groupby("estado_titulo")["prima_estado"].first().to_dict()
    calculo = regla.calcular(senales, primas, costos, valor_salida="limite_inferior")
    candidato, _, _ = regla.decidir(senales["cumple_regla"], calculo["brecha_neta"], senales["riesgo_descartar"], umbral)
    return set(senales.loc[candidato, "unidad"])


def distancia_a_barrio_popular(lista, cfg_fe):
    """Metros desde cada aviso con coordenadas al barrio popular más cercano (como en el notebook 05, H3)."""
    import geopandas as gpd

    crs = cfg_fe["crs_metrico"]
    populares = gpd.read_file(resolver(cfg_fe["rutas"]["barrios_populares"])).to_crs(crs)
    con = lista["lat"].notna() & lista["lon"].notna()
    puntos = gpd.GeoSeries(gpd.points_from_xy(lista.loc[con, "lon"], lista.loc[con, "lat"]), crs="EPSG:4326").to_crs(crs)
    distancia = pd.Series(np.nan, index=lista.index)
    distancia[con] = puntos.distance(populares.union_all()).to_numpy()
    return distancia


def exclusiones_del_destacado(lista, oficiales):
    """Por aviso, la lista de motivos por los que no entra a la lista destacada (vacía si entra).
    `oficiales`: nombres normalizados de los barrios oficiales, para la regla de barrio dudoso."""
    titulo = lista["titulo"].fillna("").astype(str)
    en_popular = lista["titulo_barrio_popular"].astype(bool) | (lista["en_barrio_popular"].fillna(0) == 1)
    cerca_popular = ~en_popular & (lista["dist_barrio_popular_m"] < RADIO_BARRIO_POPULAR_M)
    casa = lista["titulo_casa"].astype(bool) | lista["titulo_tipo_casa"].astype(bool)
    ph = titulo.str.contains(REGEX_PH, case=False, regex=True)
    uso = titulo.str.contains(REGEX_USO_NO_RESIDENCIAL, case=False, regex=True)
    sin_coordenadas = lista["lat"].isna()
    dudoso = pd.Series([bool(sin) and bool(menciona_otro_barrio(t, nombre_barrio(b), oficiales))
                        for sin, t, b in zip(sin_coordenadas, titulo, lista["barrio"])], index=lista.index)
    varias = titulo.map(posible_varias_unidades)
    financiacion = titulo.map(normalizar).str.contains(REGEX_FINANCIACION, regex=True)
    en_pozo = lista["riesgo_en_pozo"].astype(bool)
    motivos = [("barrio popular", en_popular), (f"a menos de {RADIO_BARRIO_POPULAR_M} m de un barrio popular", cerca_popular),
               ("casa", casa), ("PH", ph), ("uso comercial u oficina", uso),
               (EXCLUSION_BARRIO_DUDOSO, dudoso), (EXCLUSION_VARIAS_UNIDADES, varias),
               (EXCLUSION_FINANCIACION, financiacion), (EXCLUSION_EN_POZO, en_pozo)]
    return [[nombre for nombre, marca in motivos if bool(marca.iloc[i])] for i in range(len(lista))]


def segmento_por_aviso(limpio, semilla):
    """Segmento de departamento de cada aviso, como en el notebook 06 (sección 3): índice de equipamiento
    con MCA (el vacío como "No") y K-means con K = 4 sobre ambientes, m² por ambiente, antigüedad,
    expensas por m² e índice, con la misma semilla. Es descriptivo: no entra a la lista ni a la regla."""
    X = segmentos.tabla_mca(limpio, "no")
    mca = segmentos.ajustar_mca(X, semilla=semilla)
    V, _ = segmentos.variables_kmeans(limpio, segmentos.indice_mca(mca, X))
    Z, parametros = segmentos.escalar(V)
    km = segmentos.ajustar_kmeans(Z, 4, semilla=semilla)
    centroides = segmentos.a_escala_original(pd.DataFrame(km.cluster_centers_, columns=V.columns), parametros)
    return pd.Series(km.labels_, index=limpio["id_aviso"].values).map(segmentos.nombrar_segmentos(centroides))


def tabla_avisos(ranking, precio, limpio, explicacion, costos, cfg_fe, firmes=frozenset(), segmento=None,
                 estado_r2=None):
    """Una fila por unidad de la lista oficial: la ficha más lo que necesita el simulador.
    `firmes`: unidades que son candidato firme. `segmento`: segmento de departamento por id_aviso.
    `estado_r2`: estado en el segundo relevamiento por id_aviso (sigue, republicado, salio)."""
    # De la lista: la posición y lo que solo está ahí; el resto, sin redondear, de precio_esperado.tsv
    propias = ["id_aviso", "posicion", "ambientes", "antiguedad", "avisos_de_la_unidad", "avisos_discordantes",
               "brecha_otro_modelo_%", "link"]
    lista = ranking[propias].merge(precio, on="id_aviso", how="left", validate="one_to_one")
    lista["brecha_%"] = 100 * lista["brecha"]
    lista["brecha_neta_%"] = 100 * lista["brecha_neta"]
    lista["tasa_salida_ambientes_%"] = 100 * lista["tasa_salida_ambientes"]
    lista = lista.merge(limpio[["id_aviso", "titulo", "dormitorios"]], on="id_aviso", how="left")
    lista["segmento"] = lista["id_aviso"].map(segmento) if segmento is not None else ""
    lista["estado_r2"] = lista["id_aviso"].map(estado_r2) if estado_r2 is not None else ""
    lista = lista.merge(explicacion.drop(columns=["precio_m2_esperado"]), on="id_aviso", how="left")
    niveles = {v: regla.nivel_de_refaccion(lista["estado_titulo"], costos, v) for v in ["central", "baja", "alta"]}
    lista["dist_barrio_popular_m"] = distancia_a_barrio_popular(lista, cfg_fe)
    exclusiones = exclusiones_del_destacado(lista, barrios_oficiales(cfg_fe))
    filas = []
    for i, f in lista.iterrows():
        factores = [{"factor": f[f"{s}_{k}"], "efecto_pct": _limpio(f[f"{s}_{k}_%"])}
                    for s in ["sube", "baja"] for k in (1, 2, 3) if isinstance(f.get(f"{s}_{k}"), str)]
        filas.append({
            "id": f["id_aviso"], "posicion": int(f["posicion"]), "barrio": f["barrio"],
            "barrio_nombre": nombre_barrio(f["barrio"]), "zona": f["zona"], "titulo": f["titulo"],
            "link": str(f["link"]).split("#")[0].split("?")[0],   # sin los parámetros de tracking
            "lat": None if pd.isna(f["lat"]) else round(float(f["lat"]), 5),   # 2 decimales serían una grilla de 1 km
            "lon": None if pd.isna(f["lon"]) else round(float(f["lon"]), 5),
            "precio_usd": _limpio(f["precio_usd"]), "m2": _limpio(f["m2_final"]),
            "ambientes": _limpio(f["ambientes"]), "antiguedad": _limpio(f["antiguedad"]),
            "precio_m2": _limpio(f["precio_m2_usd"]), "precio_m2_esperado": _limpio(f["precio_m2_esperado"]),
            "precio_m2_inf": _limpio(f["precio_m2_esperado_inf"]), "precio_m2_sup": _limpio(f["precio_m2_esperado_sup"]),
            "precio_m2_referencia_zona": _limpio(f["precio_m2_referencia_zona"]),
            "brecha_pct": _limpio(f["brecha_%"]), "brecha_otro_modelo_pct": _limpio(f["brecha_otro_modelo_%"]),
            "consenso": bool(f["marcado_consenso"]), "debajo_del_intervalo": bool(f["debajo_del_intervalo"]),
            "avisos_de_la_unidad": int(f["avisos_de_la_unidad"]), "avisos_discordantes": bool(f["avisos_discordantes"]),
            "bajo_de_precio": bool(f["bajo_de_precio"]), "tasa_completitud": _limpio(f["tasa_completitud"]),
            "estado": f["estado_titulo"], "estado_nombre": ESTADOS.get(f["estado_titulo"], f["estado_titulo"]),
            "prima_estado": _limpio(f["prima_estado"]),
            "nivel_refaccion": {v: niveles[v][i] for v in niveles},
            "riesgo_descartar": f["riesgo_descartar"] if isinstance(f["riesgo_descartar"], str) else "",
            "riesgo_revisar": f["riesgo_revisar"] if isinstance(f["riesgo_revisar"], str) else "",
            "titulo_casa": bool(f["titulo_casa"]), "titulo_barrio_popular": bool(f["titulo_barrio_popular"]),
            "geo_dudoso": bool(f["geo_dudoso"]) if pd.notna(f["geo_dudoso"]) else False,
            "dist_barrio_popular_m": None if pd.isna(f["dist_barrio_popular_m"]) else int(round(f["dist_barrio_popular_m"])),
            "exclusiones": exclusiones[i],
            "segmento": f["segmento"] if isinstance(f["segmento"], str) else "",
            "estado_r2": f["estado_r2"] if isinstance(f["estado_r2"], str) else "",
            "brecha_neta_pct": _limpio(f["brecha_neta_%"]), "nivel": f["nivel_decision"],
            "firme": bool(f["unidad"] in firmes),
            "motivo": f["motivo_decision"] if isinstance(f["motivo_decision"], str) else "",
            "costos": {k: _limpio(f[c]) for k, c in [
                ("entrada", "costo_entrada_usd"), ("refaccion", "refaccion_usd"), ("total", "costo_total_usd"),
                ("valor_salida", "valor_salida_usd"), ("venta_cierre", "venta_cierre_usd"),
                ("salida", "costo_salida_usd"), ("resultado", "resultado_usd")]},
            "tasa_salida_ambientes_pct": _limpio(f["tasa_salida_ambientes_%"]),
            "factores": factores,
        })
    return filas


def resumen_por_barrio(precio, ranking, firmes=frozenset()):
    """Por barrio: avisos y unidades analizados, señales, candidatos y firmes (unidades), precio por m² y error."""
    ranking = ranking.merge(precio[["id_aviso", "unidad"]], on="id_aviso", how="left")
    ranking["firme"] = ranking["unidad"].isin(firmes)
    por_barrio = precio.groupby("barrio").agg(
        avisos=("id_aviso", "size"), unidades=("unidad", "nunique"),
        precio_m2_mediano=("precio_m2_usd", "median"),
        error_mediano_pct=("brecha", lambda b: 100 * b.abs().median()),
        con_coordenadas=("lat", lambda s: int(s.notna().sum())))
    lista = ranking.groupby("barrio").agg(
        senales=("id_aviso", "size"),
        candidatos=("nivel_decision", lambda n: int((n == regla.CANDIDATO).sum())),
        firmes=("firme", "sum"),
        brecha_mediana_pct=("brecha_%", "median"), brecha_neta_mediana_pct=("brecha_neta_%", "median"))
    tabla = por_barrio.join(lista, how="left").fillna({"senales": 0, "candidatos": 0, "firmes": 0})
    return [{"barrio": b, "nombre": nombre_barrio(b), "avisos": int(f["avisos"]), "unidades": int(f["unidades"]),
             "con_coordenadas": int(f["con_coordenadas"]), "senales": int(f["senales"]),
             "candidatos": int(f["candidatos"]), "firmes": int(f["firmes"]),
             "precio_m2_mediano": round(float(f["precio_m2_mediano"])),
             "error_mediano_pct": round(float(f["error_mediano_pct"]), 1),
             "brecha_mediana_pct": _limpio(f["brecha_mediana_pct"]),
             "brecha_neta_mediana_pct": _limpio(f["brecha_neta_mediana_pct"])}
            for b, f in tabla.sort_index().iterrows()]


def sensibilidad(precio, costos, umbral):
    """Unidades candidatas en los escenarios del notebook 07 (mismo cálculo)."""
    senales = precio[precio["cumple_regla"]]
    primas = senales.groupby("estado_titulo")["prima_estado"].first().to_dict()

    def unidades(**kw):
        calculo = regla.calcular(senales, primas, costos, kw.get("escenario", "base"), kw.get("refaccion", "central"),
                                 kw.get("valor_salida", "esperado"), kw.get("ganancias"))
        candidato, _, _ = regla.decidir(senales["cumple_regla"], calculo["brecha_neta"], senales["riesgo_descartar"],
                                        kw.get("umbral", umbral))
        return int(senales.loc[candidato, "unidad"].nunique())

    return {
        "base": unidades(),
        "costos_optimistas": unidades(escenario="optimista"),
        "costos_pesimistas": unidades(escenario="pesimista"),
        "refaccion_baja": unidades(refaccion="baja"),
        "refaccion_alta": unidades(refaccion="alta"),
        "salida_limite_inferior": unidades(valor_salida="limite_inferior"),
        "ganancias_15": unidades(ganancias=0.15),
        "ganancias_35": unidades(ganancias=0.35),
        "umbral_0": unidades(umbral=0.0),
        "umbral_20": unidades(umbral=0.20),
        "conservador": unidades(valor_salida="limite_inferior"),
    }


def salida_por_brecha(precio, seg, umbral, semilla=42):
    """Tasa de salida del portal por decil de brecha, con IC 95% por bootstrap de unidades (notebook 05, H1b).
    Sin barrios truncados."""
    ok = ~seg["barrio_truncado"].astype(bool).values
    df = pd.DataFrame({"brecha": precio["brecha"].values, "unidad": precio["unidad"].values,
                       "salio": seg["salio"].astype(float).values})[ok]
    df["decil"] = pd.qcut(df["brecha"], 10, labels=False)
    filas = []
    for d, g in df.groupby("decil"):
        tasa, inf, sup = inferencia.bootstrap_estadistico(g["salio"], g["unidad"], b=300, semilla=semilla)
        mediana = float(g["brecha"].median())
        filas.append({"decil": int(d) + 1, "brecha_mediana_pct": round(100 * mediana, 1),
                      "brecha_min_pct": round(100 * float(g["brecha"].min()), 1),
                      "brecha_max_pct": round(100 * float(g["brecha"].max()), 1),
                      "tasa_pct": round(100 * tasa, 1), "ic_inf_pct": round(100 * inf, 1),
                      "ic_sup_pct": round(100 * sup, 1), "avisos": int(len(g)), "marcado": bool(mediana < umbral)})
    return filas


def fondo(precio):
    """Todos los avisos con coordenadas (sin los geo_dudoso), para el fondo gris del mapa: [lat, lon, barrio]."""
    con = precio[precio["lat"].notna()]
    barrios = sorted(con["barrio"].unique())
    indice = {b: i for i, b in enumerate(barrios)}
    return {"barrios": barrios, "nombres": [nombre_barrio(b) for b in barrios],
            "puntos": [[round(float(f["lat"]), 4), round(float(f["lon"]), 4), indice[f["barrio"]]]
                       for _, f in con[["lat", "lon", "barrio"]].iterrows()]}


def estaciones(cfg_fe, cfg_enr):
    """Capas del mapa: puntos con nombre y línea, en latitud y longitud."""
    capas = {}
    for capa, ruta, nombre, linea, filtro in [
        ("subte", cfg_enr["subte_geojson"] if "subte_geojson" in cfg_enr else "data/external/estaciones-de-subte.geojson",
         "ESTACION", "LINEA", None),
        ("tren", cfg_fe["rutas"]["tren"], "nombre", "linea", lambda p: pd.notna(p.get("comuna"))),
        ("metrobus", cfg_fe["rutas"]["metrobus"], "CALLE", "L1", None),
        ("premetro", cfg_fe["rutas"]["premetro"], "nam", "ral", None),
    ]:
        # Misma reproyección que el análisis (fuentes_externas.cargar_estaciones): el premetro viene en
        # POSGAR 2007 / CABA 2019, en metros, y leído como grados caía fuera del mapa.
        g = fuentes_externas.a_wgs84(json.load(open(resolver(ruta), encoding="utf-8")))
        puntos = []
        for f in g["features"]:
            p = f["properties"]
            if filtro is not None and not filtro(p):
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            puntos.append({"lat": round(lat, 5), "lon": round(lon, 5), "nombre": str(p.get(nombre, "")).title(),
                           "linea": str(p.get(linea, ""))})
        capas[capa] = puntos
    return capas


def exportar(cfg, salida=SALIDA):
    rutas, cfg_an = cfg["rutas"], cfg["analisis"]
    costos = validacion.cargar_reglas_titulo()
    precio = pd.read_csv(resolver(rutas["precio_esperado"]), sep="\t", low_memory=False)
    for col in ["riesgo_descartar", "riesgo_revisar", "motivo_decision", "nivel_decision"]:
        precio[col] = precio[col].fillna("")
    ranking = pd.read_csv(resolver(rutas["ranking"]))
    limpio = pd.read_csv(resolver(rutas["limpio"]), sep="\t", low_memory=False)
    explicacion = pd.read_csv(resolver(rutas["explicacion"]), sep="\t")
    embudo = pd.read_csv(resolver(rutas["embudo"]))

    firmes = unidades_firmes(precio, costos, cfg_an["umbral_brecha_neta"])
    segmento = segmento_por_aviso(limpio, cfg_an["semilla"])
    ruta_seg = resolver(rutas["seguimiento"])
    seg = pd.read_csv(ruta_seg) if ruta_seg.exists() else None
    estado_r2 = seg.set_index("id_aviso")["estado"] if seg is not None else None
    avisos = tabla_avisos(ranking, precio, limpio, explicacion, costos, cfg["fuentes_externas"], firmes, segmento,
                          estado_r2)
    en_segmento_alerta = precio["id_aviso"].map(segmento) == SEGMENTO_ALERTA
    destacados = [a for a in avisos if a["nivel"] == regla.CANDIDATO and a["consenso"] and not a["exclusiones"]]
    error = precio["brecha"].abs().median()
    resumen = {
        "metadatos": {
            "generado": date.today().isoformat(), "commit": commit_actual(),
            "relevamiento_1": cfg["permisos_obra"]["fecha_scraping"], "relevamiento_2": "2026-10-27",
            "modelo_oficial": precio["modelo_oficial"].iloc[0], "nivel_intervalo": cfg_an["nivel_intervalo"],
            "umbral_brecha": cfg_an["umbral"], "umbral_brecha_neta": cfg_an["umbral_brecha_neta"],
        },
        "embudo": [{"paso": r["paso"], "filtro": r["filtro"], "avisos": int(r["avisos"]), "unidades": int(r["unidades"])}
                   for _, r in embudo.iterrows()],
        "indicadores": {
            "avisos_analizados": int(len(precio)), "unidades_analizadas": int(precio["unidad"].nunique()),
            "senales_unidades": int(len(ranking)), "candidatos_unidades": int((ranking["nivel_decision"] == regla.CANDIDATO).sum()),
            "candidatos_firmes_unidades": int(len(firmes)),
            "destacados_unidades": len(destacados),
            "destacados_firmes_unidades": sum(a["firme"] for a in destacados),
            "error_mediano_pct": round(100 * error, 1),
            "segmento_alerta": SEGMENTO_ALERTA,
            "error_mediano_segmento_alerta_pct": round(100 * float(precio.loc[en_segmento_alerta, "brecha"].abs().median()), 1),
            "avisos_segmento_alerta_pct": round(100 * float(en_segmento_alerta.mean()), 1),
            "cobertura_intervalo_pct": round(100 * float((precio["precio_m2_usd"].between(
                precio["precio_m2_esperado_inf"], precio["precio_m2_esperado_sup"])).mean()), 1),
            "tasa_salida_marcados_pct": None, "tasa_salida_resto_pct": None,
            "brecha_neta_mediana_senales_pct": round(100 * float(precio.loc[precio["cumple_regla"], "brecha_neta"].median()), 1),
        },
        "sensibilidad": sensibilidad(precio, costos, cfg_an["umbral_brecha_neta"]),
        "parametros_costos": {e: regla.parametros(costos, e) for e in ESCENARIOS},
        "primas_estado": precio.groupby("estado_titulo")["prima_estado"].first().round(4).to_dict(),
        "tasa_salida_ambientes_pct": None,
        "salida_por_brecha": None,
        "barrios": resumen_por_barrio(precio, ranking, firmes),
    }
    if seg is not None:
        ok = ~seg["barrio_truncado"].astype(bool)
        marc = precio["marcado"].values
        resumen["indicadores"]["tasa_salida_marcados_pct"] = round(100 * float(seg.loc[ok & marc, "salio"].mean()), 1)
        resumen["indicadores"]["tasa_salida_resto_pct"] = round(100 * float(seg.loc[ok & ~marc, "salio"].mean()), 1)
        ambientes = limpio.set_index("id_aviso").loc[precio["id_aviso"]].reset_index()
        ambientes["ambientes"] = pd.read_csv(resolver(rutas["limpio"]), sep="\t", low_memory=False,
                                             usecols=["ambientes"])["ambientes"]
        grupo = ambientes["ambientes"].fillna(ambientes["dormitorios"] + 1).clip(1, 5).astype(int)
        tasas = seg.loc[ok, "salio"].astype(float).groupby(grupo[ok.values].values).mean()
        resumen["tasa_salida_ambientes_pct"] = {int(k): round(100 * v, 1) for k, v in tasas.items()}
        resumen["salida_por_brecha"] = salida_por_brecha(precio, seg, cfg_an["umbral"], cfg_an["semilla"])

    salida = asegurar_directorio(Path(salida) / "avisos.json").parent
    for nombre, contenido in [("avisos.json", avisos), ("resumen.json", resumen), ("fondo.json", fondo(precio)),
                              ("estaciones.json", estaciones(cfg["fuentes_externas"], cfg["enriquecimiento"]))]:
        with open(salida / nombre, "w", encoding="utf-8") as fh:
            json.dump(contenido, fh, ensure_ascii=False, separators=(",", ":"))
    return avisos, resumen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exporta la capa de datos del dashboard (docs/dashboard/data).")
    agregar_argumento_config(parser)
    args = parser.parse_args(argv)
    avisos, resumen = exportar(cargar_config(args.config))
    tam = {f.name: f"{f.stat().st_size / 1024:.0f} KB" for f in SALIDA.glob("*.json")}
    print(f"Unidades exportadas: {len(avisos):,} | candidatos: {resumen['indicadores']['candidatos_unidades']:,} | "
          f"firmes: {resumen['indicadores']['candidatos_firmes_unidades']:,} | "
          f"destacados en el resumen: {resumen['indicadores']['destacados_unidades']:,} | archivos: {tam}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
