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

Uso:  python3 src/exportar_dashboard.py
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import regla, validacion  # noqa: E402
from src.configuracion import agregar_argumento_config, cargar_config  # noqa: E402
from src.eda import nombre_barrio  # noqa: E402
from src.rutas import asegurar_directorio, resolver  # noqa: E402

SALIDA = RAIZ / "docs" / "dashboard" / "data"
ESCENARIOS = ["optimista", "base", "pesimista"]
ESTADOS = {"sin_marca": "sin marca en el título", "a_reciclar": "a reciclar", "a_refaccionar": "a refaccionar",
           "ya_reformado": "ya reformado", "a_estrenar": "a estrenar"}


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


def tabla_avisos(ranking, precio, limpio, explicacion, costos):
    """Una fila por unidad de la lista oficial: la ficha más lo que necesita el simulador."""
    # De la lista: la posición y lo que solo está ahí; el resto, sin redondear, de precio_esperado.tsv
    propias = ["id_aviso", "posicion", "ambientes", "antiguedad", "avisos_de_la_unidad", "avisos_discordantes",
               "brecha_otro_modelo_%", "link"]
    lista = ranking[propias].merge(precio, on="id_aviso", how="left", validate="one_to_one")
    lista["brecha_%"] = 100 * lista["brecha"]
    lista["brecha_neta_%"] = 100 * lista["brecha_neta"]
    lista["tasa_salida_ambientes_%"] = 100 * lista["tasa_salida_ambientes"]
    lista = lista.merge(limpio[["id_aviso", "titulo", "dormitorios"]], on="id_aviso", how="left")
    lista = lista.merge(explicacion.drop(columns=["precio_m2_esperado"]), on="id_aviso", how="left")
    niveles = {v: regla.nivel_de_refaccion(lista["estado_titulo"], costos, v) for v in ["central", "baja", "alta"]}
    filas = []
    for i, f in lista.iterrows():
        factores = [{"factor": f[f"{s}_{k}"], "efecto_pct": _limpio(f[f"{s}_{k}_%"])}
                    for s in ["sube", "baja"] for k in (1, 2, 3) if isinstance(f.get(f"{s}_{k}"), str)]
        filas.append({
            "id": f["id_aviso"], "posicion": int(f["posicion"]), "barrio": f["barrio"],
            "barrio_nombre": nombre_barrio(f["barrio"]), "zona": f["zona"], "titulo": f["titulo"],
            "link": str(f["link"]).split("#")[0].split("?")[0],   # sin los parámetros de tracking
            "lat": _limpio(f["lat"]), "lon": _limpio(f["lon"]),
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
            "brecha_neta_pct": _limpio(f["brecha_neta_%"]), "nivel": f["nivel_decision"],
            "motivo": f["motivo_decision"] if isinstance(f["motivo_decision"], str) else "",
            "costos": {k: _limpio(f[c]) for k, c in [
                ("entrada", "costo_entrada_usd"), ("refaccion", "refaccion_usd"), ("total", "costo_total_usd"),
                ("valor_salida", "valor_salida_usd"), ("venta_cierre", "venta_cierre_usd"),
                ("salida", "costo_salida_usd"), ("resultado", "resultado_usd")]},
            "tasa_salida_ambientes_pct": _limpio(f["tasa_salida_ambientes_%"]),
            "factores": factores,
        })
    return filas


def resumen_por_barrio(precio, ranking):
    """Por barrio: avisos y unidades analizados, señales y candidatos (unidades), precio por m² y error del modelo."""
    por_barrio = precio.groupby("barrio").agg(
        avisos=("id_aviso", "size"), unidades=("unidad", "nunique"),
        precio_m2_mediano=("precio_m2_usd", "median"),
        error_mediano_pct=("brecha", lambda b: 100 * b.abs().median()),
        con_coordenadas=("lat", lambda s: int(s.notna().sum())))
    lista = ranking.groupby("barrio").agg(
        senales=("id_aviso", "size"),
        candidatos=("nivel_decision", lambda n: int((n == regla.CANDIDATO).sum())),
        brecha_mediana_pct=("brecha_%", "median"), brecha_neta_mediana_pct=("brecha_neta_%", "median"))
    tabla = por_barrio.join(lista, how="left").fillna({"senales": 0, "candidatos": 0})
    return [{"barrio": b, "nombre": nombre_barrio(b), "avisos": int(f["avisos"]), "unidades": int(f["unidades"]),
             "con_coordenadas": int(f["con_coordenadas"]), "senales": int(f["senales"]),
             "candidatos": int(f["candidatos"]), "precio_m2_mediano": round(float(f["precio_m2_mediano"])),
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


def estaciones(cfg_fe, cfg_enr):
    """Capas del mapa: puntos con nombre y línea."""
    capas = {}
    for capa, ruta, nombre, linea, filtro in [
        ("subte", cfg_enr["subte_geojson"] if "subte_geojson" in cfg_enr else "data/external/estaciones-de-subte.geojson",
         "ESTACION", "LINEA", None),
        ("tren", cfg_fe["rutas"]["tren"], "nombre", "linea", lambda p: pd.notna(p.get("comuna"))),
        ("metrobus", cfg_fe["rutas"]["metrobus"], "CALLE", "L1", None),
        ("premetro", cfg_fe["rutas"]["premetro"], "nam", "ral", None),
    ]:
        g = json.load(open(resolver(ruta), encoding="utf-8"))
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
    limpio = pd.read_csv(resolver(rutas["limpio"]), sep="\t", low_memory=False,
                         usecols=["id_aviso", "titulo", "dormitorios"])
    explicacion = pd.read_csv(resolver(rutas["explicacion"]), sep="\t")
    embudo = pd.read_csv(resolver(rutas["embudo"]))

    avisos = tabla_avisos(ranking, precio, limpio, explicacion, costos)
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
            "error_mediano_pct": round(100 * error, 1),
            "cobertura_intervalo_pct": round(100 * float((precio["precio_m2_usd"].between(
                precio["precio_m2_esperado_inf"], precio["precio_m2_esperado_sup"])).mean()), 1),
            "tasa_salida_marcados_pct": None, "tasa_salida_resto_pct": None,
            "brecha_neta_mediana_senales_pct": round(100 * float(precio.loc[precio["cumple_regla"], "brecha_neta"].median()), 1),
        },
        "sensibilidad": sensibilidad(precio, costos, cfg_an["umbral_brecha_neta"]),
        "parametros_costos": {e: regla.parametros(costos, e) for e in ESCENARIOS},
        "primas_estado": precio.groupby("estado_titulo")["prima_estado"].first().round(4).to_dict(),
        "tasa_salida_ambientes_pct": None,
        "barrios": resumen_por_barrio(precio, ranking),
    }
    ruta_seg = resolver(rutas["seguimiento"])
    if ruta_seg.exists():
        seg = pd.read_csv(ruta_seg)
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

    salida = asegurar_directorio(Path(salida) / "avisos.json").parent
    for nombre, contenido in [("avisos.json", avisos), ("resumen.json", resumen),
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
          f"conservador: {resumen['sensibilidad']['conservador']:,} | archivos: {tam}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
