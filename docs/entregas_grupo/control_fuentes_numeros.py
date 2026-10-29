"""
Números citados en control_fuentes.md.
Correr desde la raíz del repo, después de src/fuentes_externas.py:
    python3 docs/entregas_grupo/control_fuentes_numeros.py
No modifica ningún archivo. Imprime las tablas en Markdown.

Las medianas por barrio se calculan por barrio oficial (el polígono donde cae
el punto), no por la categoría de búsqueda de MercadoLibre.
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np
import pandas as pd

from src import fuentes_externas as fe
from src.configuracion import cargar_config
from src.enriquecimiento import calcular_distancia_transporte

parser = argparse.ArgumentParser(description="Números del control de fuentes externas.")
parser.add_argument("--config", default=None, help="YAML de configuración (default: config/config.yaml).")
parser.add_argument("--accesibilidad", default=None, help="TSV de accesibilidad (default: el de config).")
ARGS = parser.parse_args()
CFG = cargar_config(ARGS.config)["fuentes_externas"]
RUTAS = {k: RAIZ / v for k, v in CFG["rutas"].items()}
if ARGS.accesibilidad:
    RUTAS["salida"] = Path(ARGS.accesibilidad)
SUR_OESTE = ["Villa Lugano", "Mataderos", "Villa Soldati", "Liniers", "Villa Riachuelo",
             "Versalles", "Villa Luro", "Parque Avellaneda", "Nueva Pompeya", "Floresta"]


def num(v, decimales=0):
    """Número con separador de miles y coma decimal, a la argentina."""
    if isinstance(v, (int, np.integer)):
        return f"{v:,}".replace(",", ".")
    if v is None or np.isnan(v):
        return ""
    return f"{v:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabla(df, decimales=0):
    """DataFrame a tabla Markdown; decimales puede ser un número o un dict por columna."""
    def fmt(col, v):
        if isinstance(v, (int, np.integer, float, np.floating)):
            d = decimales.get(col, 0) if isinstance(decimales, dict) else decimales
            return num(v, d)
        return str(v)
    cab = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    filas = ["| " + " | ".join(fmt(c, v) for c, v in zip(df.columns, fila)) + " |"
             for fila in df.itertuples(index=False)]
    return "\n".join([cab, sep] + filas)


enr = pd.read_csv(RAIZ / "data/processed/propiedades_enriquecidas.tsv", sep="\t", low_memory=False)
acc = pd.read_csv(RUTAS["salida"], sep="\t", low_memory=False)
df = enr[["link", "barrio", "ubicacion", "geo_status", "lat", "lon", "dist_transporte_m"]].merge(acc, on="link", validate="1:1")
ok = df[df["geo_status"] == "OK"].copy()
assert len(acc) == len(enr) and acc["link"].is_unique

# --- 1. Conteos por fuente ---------------------------------------------------
print("## 1. Conteos por fuente\n")
tren_raw = fe.leer_geojson(RUTAS["tren"])["features"]
tren_caba = [f for f in tren_raw if f["properties"].get("barrio")]
metro_raw = fe.leer_geojson(RUTAS["metrobus"])["features"]
nombres_mb = {f["properties"].get("NOMBRE PAR") for f in metro_raw} - {None}
premetro_raw = fe.leer_geojson(RUTAS["premetro"])["features"]
verdes, rep_v = fe.cargar_poligonos(RUTAS["espacios_verdes"], CFG["crs_metrico"])
barrios, rep_b = fe.cargar_poligonos(RUTAS["barrios"], CFG["crs_metrico"])
populares, rep_p = fe.cargar_poligonos(RUTAS["barrios_populares"], CFG["crs_metrico"])
clase = verdes["clasificac"].map(fe.normalizar_texto)
en_dist = clase.isin({fe.normalizar_texto(c) for c in CFG["verdes"]["clases_distancia"]})
en_area = ~clase.isin({fe.normalizar_texto(c) for c in CFG["verdes"]["clases_excluidas_area"]}) \
    & ~verdes["id"].isin(CFG["verdes"]["ids_excluidos_area"])
conteos = pd.DataFrame([
    ["Estaciones de tren", len(tren_raw), f"{len(tren_caba)} en CABA; 1 cerrada excluida"],
    ["Paradas de Metrobus", len(metro_raw), f"{len(nombres_mb)} nombres de parada distintos (una parada por sentido)"],
    ["Estaciones de premetro", len(premetro_raw), ""],
    ["Espacios verdes públicos", len(verdes), f"{int(en_dist.sum())} para la distancia; {int(en_area.sum())} para el área; {rep_v} geometrías reparadas"],
    ["Barrios oficiales", len(barrios), f"{rep_b} geometrías reparadas"],
    ["Barrios populares", len(populares), f"{rep_p} geometrías reparadas"],
], columns=["Fuente", "Registros", "Detalle"])
print(tabla(conteos))
print("\nClases de espacio verde:\n")
cl = verdes.assign(ha=verdes.geometry.area / 1e4).groupby("clasificac").agg(
    Polígonos=("id", "size"), Hectáreas=("ha", "sum")).sort_values("Polígonos", ascending=False).reset_index()
cl["Distancia"] = np.where(cl["clasificac"].map(fe.normalizar_texto).isin(
    {fe.normalizar_texto(c) for c in CFG["verdes"]["clases_distancia"]}), "sí", "no")
cl["Área"] = np.where(cl["clasificac"].map(fe.normalizar_texto).isin(
    {fe.normalizar_texto(c) for c in CFG["verdes"]["clases_excluidas_area"]}), "no", "sí")
print(tabla(cl.rename(columns={"clasificac": "Clase"}), 1))

# --- 2. Medianas por barrio ----------------------------------------------------
print("\n## 2. Mediana de cada distancia por barrio oficial (metros)\n")
cols = {"dist_transporte_m": "Subte", "dist_tren_m": "Tren", "dist_premetro_m": "Premetro",
        "dist_metrobus_m": "Metrobus", "dist_riel_m": "Riel", "dist_transporte_pesado_m": "Pesado",
        "dist_espacio_verde_m": "Verde", "area_verde_500m_ha": "Verde 500 m (ha)"}
med = ok.groupby("barrio_oficial").agg(n=("link", "size"), **{v: (k, "median") for k, v in cols.items()})
med["Caída pesado vs subte"] = ((med["Pesado"] / med["Subte"] - 1) * 100).round(0) + 0.0  # evita el -0
med = med.reset_index().rename(columns={"barrio_oficial": "Barrio"})
foco = med[med["Barrio"].isin(SUR_OESTE)].sort_values("Caída pesado vs subte")
print("Sur y oeste:\n")
print(tabla(foco, {"Verde 500 m (ha)": 2}))
print("\nTodos los barrios:\n")
print(tabla(med.sort_values("Barrio"), {"Verde 500 m (ha)": 2}))
tot = ok[list(cols)].median()
print("\nTotal (medianas):", "; ".join(f"{cols[k]} {num(float(v), 2 if 'ha' in cols[k] else 0)}" for k, v in tot.items()))

# --- 3. Efecto borde -------------------------------------------------------------
lat, lon = ok["lat"].to_numpy(), ok["lon"].to_numpy()
solo_caba = fe.parsear_estaciones({"features": tren_caba})
d_caba = calcular_distancia_transporte(lat, lon, solo_caba).round(0)
borde = d_caba > ok["dist_tren_m"].to_numpy()
print(f"\n## 3. Efecto borde\n\nAvisos con la estación de tren más cercana en la provincia: {int(borde.sum())}. "
      f"Con solo estaciones de CABA quedarían una mediana de {num(np.median(d_caba[borde] - ok['dist_tren_m'].to_numpy()[borde]))} m "
      f"más lejos (máximo {num(np.max(d_caba[borde] - ok['dist_tren_m'].to_numpy()[borde]))} m).\n")
print(f"Metrobus es el transporte más cercano para el {num((ok['dist_metrobus_m'] < ok['dist_riel_m']).mean() * 100, 1)}% de los avisos.\n")
pm = ok["dist_premetro_m"] < np.fmin(ok["dist_transporte_m"], ok["dist_tren_m"])
print(f"El premetro es el riel más cercano para {num(int(pm.sum()))} avisos: "
      + ", ".join(f"{b} {n}" for b, n in ok[pm]["barrio_oficial"].value_counts().items()) + ".\n")
# Spearman = Pearson sobre los rangos (promedio en los empates); así no depende de scipy.
print(f"Correlación de Spearman entre riel y Metrobus: {num(ok['dist_riel_m'].rank().corr(ok['dist_metrobus_m'].rank()), 2)}.")

# --- 4. Barrio de MercadoLibre contra barrio oficial ------------------------------
print("\n## 4. Barrio de MercadoLibre contra barrio oficial\n")
print(f"Avisos con coordenadas: {num(len(ok))}. Fuera de todo barrio oficial: {int(ok['barrio_oficial'].isna().sum())}.\n")
bn = ok["barrio"] == "barrio-norte"
resumen = pd.DataFrame([
    ["Coincide (nombre normalizado)", int(((ok["barrio_coincide"] == 1) & ~bn).sum())],
    ["Barrio Norte en Recoleta, Retiro o Palermo", int(((ok["barrio_coincide"] == 1) & bn).sum())],
    ["Discrepancia", int((ok["barrio_coincide"] == 0).sum())],
], columns=["Resultado", "Avisos"])
resumen["%"] = (resumen["Avisos"] / len(ok) * 100).round(1)
print(tabla(resumen, 1))
pares = (ok[ok["barrio_coincide"] == 0].groupby(["barrio", "barrio_oficial"]).size()
         .sort_values(ascending=False).head(20).reset_index(name="Avisos")
         .rename(columns={"barrio": "Búsqueda de MercadoLibre", "barrio_oficial": "Barrio oficial"}))
print("\nPares más frecuentes:\n")
print(tabla(pares))
no_buscados = ok[ok["barrio_oficial"].isin(["San Cristobal", "Parque Chas"])].groupby(
    ["barrio_oficial", "barrio"]).size().sort_values(ascending=False).reset_index(name="Avisos").rename(
    columns={"barrio_oficial": "Barrio oficial", "barrio": "Búsqueda de MercadoLibre"})
print("\nBarrios oficiales que el scraping no buscaba:\n")
print(tabla(no_buscados))

# Distancia de cada discrepancia al barrio buscado: a pocos metros es un aviso
# de borde; a más de 1 km es casi seguro un error de geocodificación.
import shapely  # noqa: E402

abrev = CFG["abreviaturas_barrio"]
eq = fe.preparar_equivalencias(CFG["equivalencias_barrio"], abrev)
poly = dict(zip(barrios["nombre"].map(lambda s: fe.normalizar_texto(s, abrev)), barrios.geometry))
geom_busqueda = {}
for b in ok["barrio"].unique():
    k = fe.normalizar_texto(b, abrev)
    geom_busqueda[b] = shapely.union_all([poly[x] for x in eq.get(k, {k})])
pts_ok = fe.puntos_proyectados(lat, lon, CFG["crs_metrico"]).geometry.to_numpy()
ok["dist_barrio_busqueda_m"] = [shapely.distance(p, geom_busqueda[b]) for p, b in zip(pts_ok, ok["barrio"])]
dis = ok[ok["barrio_coincide"] == 0]
tramos = ["Hasta 200 m del barrio buscado", "De 200 m a 1 km", "A más de 1 km"]
dis = dis.assign(Tramo=pd.cut(dis["dist_barrio_busqueda_m"], [0, 200, 1000, np.inf], labels=tramos, include_lowest=True))
t = dis["Tramo"].value_counts().reindex(tramos).reset_index(name="Avisos")
t["% de las discrepancias"] = (t["Avisos"] / len(dis) * 100).round(1)
print("\nDistancia de cada discrepancia al barrio en el que se publicó el aviso:\n")
print(tabla(t, 1))
lejos = dis[dis["dist_barrio_busqueda_m"] > 1000]
nombra = [fe.normalizar_texto(b, abrev) in (fe.normalizar_texto(u, abrev) or "")
          for b, u in zip(lejos["barrio"], lejos["ubicacion"])]
print(f"\nA más de 1 km: {len(lejos)} avisos en {len(lejos[['lat', 'lon']].drop_duplicates())} ubicaciones distintas. "
      f"En {sum(nombra)} la dirección publicada nombra el barrio de la búsqueda (error de geocodificación); "
      f"en {len(lejos) - sum(nombra)}, no (aviso publicado en otra categoría). "
      "Ejemplos (la dirección publicada y dónde la ubicó el geocoding):\n")
ej = (lejos.groupby(["barrio", "ubicacion", "barrio_oficial"])["dist_barrio_busqueda_m"].agg(["size", "first"])
      .reset_index().sort_values("size", ascending=False).head(8))
ej["first"] = (ej["first"] / 1000).round(1)
print(tabla(ej.rename(columns={"barrio": "Búsqueda", "ubicacion": "Dirección publicada", "barrio_oficial": "Ubicado en",
                               "size": "Avisos", "first": "Km al barrio buscado"}), 1))

# --- 5. Barrios populares -----------------------------------------------------------
print("\n## 5. Avisos en barrios populares\n")
pts = fe.puntos_proyectados(lat, lon, CFG["crs_metrico"])
prio = {t: i for i, t in enumerate(CFG["barrios_populares"]["prioridad_tipo"])}
populares["_prioridad"] = populares["tipo"].map(prio).fillna(len(prio))
asig, multi = fe.asignar_poligono(pts, populares, ["nombre", "tipo"], orden=["_prioridad", "id"])
ok["bp_nombre"] = asig["nombre"].to_numpy()
en = ok[ok["en_barrio_popular"] == 1]
print(f"Total: {len(en)} avisos ({num(len(en) / len(ok) * 100, 2)}% de los geocodificados). En dos polígonos a la vez: {multi}.\n")
print(tabla(en.groupby("tipo_barrio_popular").size().sort_values(ascending=False).reset_index(name="Avisos")
            .rename(columns={"tipo_barrio_popular": "Tipo"})))
print()
print(tabla(en.groupby(["bp_nombre", "tipo_barrio_popular", "barrio_oficial"]).size()
            .sort_values(ascending=False).reset_index(name="Avisos")
            .rename(columns={"bp_nombre": "Barrio popular", "tipo_barrio_popular": "Tipo", "barrio_oficial": "Barrio oficial"})))
rb = enr["titulo"].str.contains("rodrigo bueno", case=False, na=False)
print(f"\nAvisos que mencionan Rodrigo Bueno en el título: {int(rb.sum())}, "
      f"sin coordenadas: {int((rb & (enr['geo_status'] != 'OK')).sum())}.")

# --- 6. Criterio de espacio verde -----------------------------------------------------
print("\n## 6. Distancia a espacio verde según el criterio\n")
canteros = clase == "CANTERO CENTRAL"
plazoletas = clase == "PLAZOLETA"
criterios = [
    ("Todos los polígonos", verdes),
    ("Sin canteros centrales", verdes[~canteros]),
    ("Sin canteros ni plazoletas", verdes[~canteros & ~plazoletas]),
    ("Criterio elegido: plazas, parques, jardines y parques semipúblicos", verdes[en_dist]),
]
filas = []
for nombre, sub in criterios:
    d = fe.distancia_a_poligonos(pts, sub)
    filas.append([nombre, len(sub), float(np.median(d)), float(np.percentile(d, 90)), float((d == 0).mean() * 100)])
print(tabla(pd.DataFrame(filas, columns=["Criterio", "Polígonos", "Mediana (m)", "P90 (m)", "% adentro"]), 1))
gp = verdes[verdes["id"].isin(CFG["verdes"]["ids_excluidos_area"])]
con_gp = fe.area_en_radio(pts, verdes[~canteros], CFG["verdes"]["radio_area_m"], CFG["verdes"]["segmentos_cuarto"])
efecto = pd.DataFrame({"Barrio": ok["barrio_oficial"].to_numpy(),
                       "extra": con_gp - ok["area_verde_500m_ha"].to_numpy()})
efecto = efecto[efecto["extra"] > 0.01]
print(f"\nFranja de la General Paz (id {gp['id'].tolist()}, {num(gp.geometry.area.sum() / 1e4, 1)} ha): "
      f"incluirla sumaría verde a {len(efecto)} avisos.\n")
print(tabla(efecto.groupby("Barrio").agg(Avisos=("extra", "size"), **{"Hectáreas extra (media)": ("extra", "mean")})
            .reset_index().sort_values("Avisos", ascending=False), 2))

# --- 7. Control de proyección --------------------------------------------------------
print("\n## 7. Control de proyección\n")
mb = fe.cargar_estaciones(RUTAS["metrobus"])
err = fe.control_proyeccion(lat, lon, mb, CFG["crs_metrico"])
print(f"Error máximo contra la distancia geodésica (WGS84), 2.000 pares aviso-parada: "
      f"haversine {num(err['haversine'], 3)}%, UTM 21S {num(err['proyeccion'], 3)}%.")
