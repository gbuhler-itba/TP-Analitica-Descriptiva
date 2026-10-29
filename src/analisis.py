"""
Etapa 6 del pipeline: precio esperado, brecha y ranking de avisos a investigar.

Es la lógica estable que produce las salidas oficiales del proyecto. Los
notebooks leen estas salidas y las explican; no las generan.

ENTRADA: data/processed/propiedades_limpias.tsv (etapa 5, src/limpiar.py)
SALIDAS:
  data/processed/precio_esperado.tsv     una fila por aviso: precio esperado,
                                         brecha, marcas, señales y KPIs
  data/processed/unidades_marcadas.csv   una fila por unidad con algún aviso
                                         marcado, con el paso del embudo al
                                         que llega
  data/processed/avisos_a_investigar.csv la lista oficial que recibe el
                                         analista (unidades que cumplen la regla)
  data/processed/embudo_ranking.csv      el embudo: filtro, denominador y
                                         cantidad de avisos y de unidades por paso

Pasos:
  1. Precio esperado fuera de muestra, sin fuga de información
     (modelo.precio_esperado_sin_fuga).
  2. Brecha = precio publicado / precio esperado - 1.
  3. Marca con el umbral de la ciudad y con el umbral según el error del barrio.
  4. Señales de error de carga.
  5. Unidades: avisos de la misma dirección y superficie; si declaran pisos
     distintos, son unidades distintas.
  6. Embudo por aviso y por unidad. Una unidad pasa un paso si al menos uno
     de sus avisos lo pasa; su aviso representativo es el que llega más lejos
     y, entre esos, el de menor precio.

Uso:  python3 src/analisis.py   (o python3 run_pipeline.py --desde-etapa 6)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import modelo  # noqa: E402
from src.configuracion import agregar_argumento_config, cargar_config  # noqa: E402
from src.indice_confort import tipo_de_columna  # noqa: E402
from src import validacion  # noqa: E402
from src.limpieza import estado_y_riesgo_del_titulo  # noqa: E402
from src.qc import ControlCalidad  # noqa: E402
from src.rutas import asegurar_directorio, resolver, ruta_relativa  # noqa: E402

PASOS = [
    ("analizados", "Avisos del dataset limpio", None),
    ("marcado", "Brecha menor que el umbral de la ciudad (−25%)", "analizados"),
    ("marcado_barrio", "Además, por debajo del umbral según el error de su barrio", "marcado"),
    ("cumple_regla", "Además, sin señales de error de carga (regla R1: lista oficial)", "marcado_barrio"),
]


# ---------------------------------------------------------------------------
# Señales y marcas
# ---------------------------------------------------------------------------
def senales_error_carga(df):
    """Señales de que el dato del aviso puede estar mal cargado (DataFrame booleano)."""
    m2_por_ambiente = df["m2_final"] / df["ambientes"].fillna(df["dormitorios"] + 1).clip(lower=1)
    limites = m2_por_ambiente.quantile([0.01, 0.99])
    return pd.DataFrame({
        "senal_m2_por_ambiente": ~m2_por_ambiente.between(*limites),
        "senal_superficie_recuperada": df["m2_origen"] == "recuperada_de_total",
        "senal_dormitorios": df["incoherencia_dormitorios"].astype(bool),
        "senal_piso": df["incoherencia_piso"].astype(bool),   # ver src/limpiar.py
        "senal_alquiler": df["menciona_alquiler"].astype(bool),
    }, index=df.index)


def marca_por_barrio(brecha, barrio, umbral, minimo_avisos=50):
    """Umbral ajustado al error del modelo en cada barrio.

    El umbral de la ciudad equivale a `veces` el error mediano de la ciudad; en
    cada barrio se exige la misma cantidad de veces su propio error mediano.
    Barrios con menos de `minimo_avisos` usan el error de la ciudad.
    """
    error_ciudad = brecha.abs().median()
    veces = umbral / -error_ciudad
    error_barrio = brecha.abs().groupby(barrio).transform("median")
    avisos = brecha.groupby(barrio).transform("size")
    error_barrio = error_barrio.where(avisos >= minimo_avisos, error_ciudad)
    return brecha < -veces * error_barrio, veces, error_ciudad


def kpis_del_aviso(df, zona):
    """Tasa de completitud y eficiencia de expensas (definidas en la PreEntrega 2)."""
    si_no = [c for c in df.columns if tipo_de_columna(df[c]) == "si_no"]
    principales = ["antiguedad", "cocheras", "bauleras", "numero_de_piso_de_la_unidad", "cantidad_de_pisos",
                   "disposicion", "orientacion", "tipo_de_departamento", "expensas_usd", "superficie_cubierta"]
    completitud = df[si_no + principales].notna().mean(axis=1)
    expensas_m2 = df["expensas_usd"] / df["m2_final"]
    log_exp = np.log(expensas_m2)
    rel_zona = log_exp - log_exp.groupby(zona).transform("median")
    return pd.DataFrame({
        "tasa_completitud": completitud,
        "expensas_usd_m2": expensas_m2,
        "expensas_rel_zona": rel_zona,
    }, index=df.index)


# ---------------------------------------------------------------------------
# Unidades y embudo
# ---------------------------------------------------------------------------
def unidad_ranking(df):
    """Unidad para el ranking: misma dirección y superficie, separando pisos distintos.

    Parte del grupo de la validación cruzada (modelo.grupo_de_unidad). Dentro
    de cada grupo, si los avisos declaran pisos distintos, cada piso es una
    unidad. Un aviso sin piso se suma a la unidad del grupo si en el grupo se
    declara un solo piso; si se declaran varios, queda como unidad aparte.
    """
    grupo = modelo.grupo_de_unidad(df)
    piso = df["numero_de_piso_de_la_unidad"]
    pisos_del_grupo = piso.groupby(grupo).transform("nunique")
    unico = piso.groupby(grupo).transform("first")   # el único piso declarado, si hay uno
    piso_efectivo = piso.where(piso.notna(), unico.where(pisos_del_grupo == 1))
    clave = grupo.astype(str) + "|" + piso_efectivo.astype(str)
    return pd.Series(pd.factorize(clave)[0], index=df.index)


def resumir_unidades(df):
    """Una fila por unidad con algún aviso marcado: paso del embudo y aviso representativo."""
    marcados = df[df["marcado"]].copy()
    marcados["paso"] = (marcados["marcado"].astype(int) + marcados["marcado_barrio"].astype(int)
                        + marcados["cumple_regla"].astype(int))
    # Representativo: el que llega más lejos en el embudo y, entre esos, el más barato
    orden = marcados.sort_values(["unidad", "paso", "precio_usd", "brecha"], ascending=[True, False, True, True])
    rep = orden.drop_duplicates("unidad").set_index("unidad")
    todos = df.groupby("unidad").agg(
        avisos_de_la_unidad=("id_aviso", "size"),
        brecha_min=("brecha", "min"),
        brecha_max=("brecha", "max"),
    )
    pasos = marcados.groupby("unidad")[["marcado", "marcado_barrio", "cumple_regla"]].any()
    salida = rep.drop(columns=["marcado", "marcado_barrio", "cumple_regla", "paso"]).join(pasos).join(todos)
    # Discordantes: los avisos de la unidad no llegan todos al mismo paso del embudo
    paso_todos = df["marcado"].astype(int) + df["marcado_barrio"].astype(int) + df["cumple_regla"].astype(int)
    salida["avisos_discordantes"] = paso_todos.groupby(df["unidad"]).nunique().loc[salida.index] > 1
    return salida.reset_index()


def embudo(df, unidades):
    """Cantidad de avisos y de unidades en cada paso, con su filtro y su denominador."""
    filas = []
    total_unidades = df["unidad"].nunique()
    for paso, descripcion, previo in PASOS:
        if paso == "analizados":
            avisos, n_unidades = len(df), total_unidades
        else:
            avisos = int(df[paso].sum())
            n_unidades = int(unidades[paso].sum())
        filas.append({"paso": paso, "filtro": descripcion, "avisos": avisos, "unidades": n_unidades})
    tabla = pd.DataFrame(filas)
    tabla["avisos_%_del_paso_anterior"] = (100 * tabla["avisos"] / tabla["avisos"].shift()).round(1)
    tabla["unidades_%_del_paso_anterior"] = (100 * tabla["unidades"] / tabla["unidades"].shift()).round(1)
    return tabla


# ---------------------------------------------------------------------------
# Etapa completa
# ---------------------------------------------------------------------------
def unir_fuentes_externas(df, rutas):
    """Suma accesibilidad (tarea 2) y permisos de obra (tarea 1) por `link`."""
    acc = pd.read_csv(resolver(rutas["accesibilidad"]), sep="\t")
    perm = pd.read_csv(resolver(rutas["permisos_obra"]), sep="\t")
    df = df.merge(acc, on="link", how="left", validate="one_to_one")
    return df.merge(perm, on="link", how="left", validate="one_to_one")


def tratar_geo_dudoso(df, cfg_enr=None):
    """Avisos con geocodificación dudosa (punto a más de 1 km del barrio buscado): se tratan
    como si no tuvieran coordenadas, así el modelo los compara contra su barrio.

    Las sub-zonas se recalculan sin esos avisos, con el mismo k-means de la etapa 4
    (`enriquecimiento.asignar_subzonas`): en algunos barrios los puntos mal ubicados
    formaban una sub-zona entera lejos del barrio (por ejemplo, en Belgrano).
    """
    from src.enriquecimiento import asignar_subzonas

    dudoso = df["geo_dudoso"].fillna(0).astype(bool)
    df = df.copy()
    df.loc[dudoso, ["lat", "lon", "subzona"]] = np.nan
    espaciales = [c for c in df.columns if c.startswith(("dist_", "area_verde", "permisos_obra"))]
    df.loc[dudoso, espaciales] = np.nan
    if cfg_enr is not None:
        ok = df["lat"].notna() & df["lon"].notna()
        df.loc[ok, "subzona"] = asignar_subzonas(df[ok], cfg_enr["subzonas_por_barrio"],
                                                 cfg_enr["min_propiedades_subzona"], cfg_enr["kmeans"])
    return df


def analizar(df, cfg_an, cfg_enr=None):
    """Corre el análisis completo sobre el dataset limpio. Devuelve (df, unidades, embudo, info).

    Decisiones de la PreEntrega 3 (notebook 04):
      - avisos con geocodificación dudosa: sin coordenadas para el modelo;
      - barrios con sub-zonas inestables (ARI < `ari_minimo_subzona`): comparados contra el barrio;
      - modelo oficial configurable (`modelo_oficial`); se calcula también el otro modelo y la
        marca de consenso (los dos lo marcan);
      - intervalo de predicción por aviso (conformal cruzado, por barrio).
    """
    df = tratar_geo_dudoso(df, cfg_enr)
    y = np.log(df["precio_m2_usd"])

    estab = validacion.estabilidad_subzonas(df, repeticiones=cfg_an["repeticiones_estabilidad"])
    inestables = list(estab.index[estab["ari_mediano"] < cfg_an["ari_minimo_subzona"]])
    modelos = ["mediana_zona", "lineal_ampliado", "gbm"]
    pred, vuelta = validacion.comparar_modelos(
        df, y, k=cfg_an["k_folds"], semilla=cfg_an["semilla"], minimo_grupo=cfg_an["minimo_grupo"],
        iqr_k=cfg_an["iqr_k"], modelos=modelos, barrios_excluidos=inestables,
    )
    oficial = cfg_an["modelo_oficial"]
    otro = "gbm" if oficial == "lineal_ampliado" else "lineal_ampliado"
    df["zona"] = pred.attrs["zona"]
    df["vuelta"] = vuelta.astype(int)
    df["modelo_oficial"] = oficial
    df["precio_m2_esperado"] = np.exp(pred[oficial])
    df["precio_m2_mediana_zona"] = np.exp(pred["mediana_zona"])
    df["brecha"] = df["precio_m2_usd"] / df["precio_m2_esperado"] - 1
    df["brecha_otro_modelo"] = df["precio_m2_usd"] / np.exp(pred[otro]) - 1

    # Intervalo de predicción (nivel configurable), por barrio, con los residuos de las otras vueltas
    residuo = y - pred[oficial]
    inf, sup = validacion.intervalos_conformes(residuo, df["barrio"], vuelta, cfg_an["nivel_intervalo"])
    df["precio_m2_esperado_inf"] = np.exp(pred[oficial] + inf)
    df["precio_m2_esperado_sup"] = np.exp(pred[oficial] + sup)
    df["debajo_del_intervalo"] = df["precio_m2_usd"] < df["precio_m2_esperado_inf"]

    df["marcado"] = df["brecha"] < cfg_an["umbral"]
    df["marcado_otro_modelo"] = df["brecha_otro_modelo"] < cfg_an["umbral"]
    df["marcado_consenso"] = df["marcado"] & df["marcado_otro_modelo"]
    marca_barrio, veces, error_ciudad = marca_por_barrio(
        df["brecha"], df["barrio"], cfg_an["umbral"], cfg_an["minimo_avisos_barrio"])
    df["marcado_barrio"] = df["marcado"] & marca_barrio

    senales = senales_error_carga(df)
    df[senales.columns] = senales
    df["senal_error_carga"] = senales.any(axis=1)
    df["cumple_regla"] = df["marcado_barrio"] & ~df["senal_error_carga"]

    df = df.join(estado_y_riesgo_del_titulo(df["titulo"], validacion.cargar_reglas_titulo()))
    df = df.join(kpis_del_aviso(df, df["zona"]))

    df["unidad"] = unidad_ranking(df)
    unidades = resumir_unidades(df)
    tabla_embudo = embudo(df, unidades)
    info = {"veces_error": veces, "error_mediano_ciudad": error_ciudad,
            "error_mediano_mediana_zona": float((df["precio_m2_usd"] / df["precio_m2_mediana_zona"] - 1).abs().median()),
            "error_mediano_otro_modelo": float(df["brecha_otro_modelo"].abs().median()),
            "barrios_subzona_inestable": inestables, "modelo_oficial": oficial,
            "cobertura_intervalo": float(((residuo >= inf) & (residuo <= sup)).mean())}
    return df, unidades, tabla_embudo, info


COLUMNAS_PRECIO = [
    "id_aviso", "unidad", "barrio", "zona", "vuelta", "modelo_oficial", "precio_usd", "m2_final", "precio_m2_usd",
    "precio_m2_esperado", "precio_m2_esperado_inf", "precio_m2_esperado_sup", "precio_m2_mediana_zona",
    "brecha", "brecha_otro_modelo", "debajo_del_intervalo",
    "marcado", "marcado_otro_modelo", "marcado_consenso", "marcado_barrio",
    "senal_m2_por_ambiente", "senal_superficie_recuperada", "senal_dormitorios", "senal_piso", "senal_alquiler",
    "senal_error_carga", "cumple_regla", "bajo_de_precio", "estado_titulo", "titulo_casa", "titulo_tipo_casa",
    "titulo_barrio_popular", "riesgo_nuda_propiedad", "riesgo_sucesion", "riesgo_con_inquilino", "riesgo_ocupado",
    "riesgo_sin_escritura", "riesgo_subasta", "riesgo_credito_pendiente", "riesgo_parte_indivisa", "riesgo_en_pozo",
    "riesgo_con_financiacion", "riesgo_no_apto_credito", "tasa_completitud", "expensas_usd_m2", "expensas_rel_zona",
    "geo_dudoso", "barrio_oficial", "en_barrio_popular", "tipo_barrio_popular", "dist_transporte_m", "dist_tren_m",
    "dist_metrobus_m", "dist_riel_m", "dist_transporte_pesado_m", "dist_espacio_verde_m", "area_verde_500m_ha",
    "permisos_obra_500m", "lat", "lon",
]

COLUMNAS_RANKING = [
    "id_aviso", "barrio", "zona", "precio_usd", "m2_final", "ambientes", "antiguedad", "precio_m2_usd",
    "precio_m2_esperado", "precio_m2_esperado_inf", "precio_m2_esperado_sup", "brecha_%", "brecha_otro_modelo_%",
    "marcado_consenso", "debajo_del_intervalo", "avisos_de_la_unidad", "brecha_min_%", "brecha_max_%",
    "avisos_discordantes", "bajo_de_precio", "estado_titulo", "riesgo_con_inquilino", "titulo_casa",
    "geo_dudoso", "tasa_completitud", "link",
]


def guardar(df, unidades, tabla_embudo, rutas):
    """Escribe las cuatro salidas oficiales."""
    df[COLUMNAS_PRECIO].to_csv(asegurar_directorio(rutas["precio_esperado"]), sep="\t", index=False)

    u = unidades.sort_values("brecha").copy()
    for col in ["brecha", "brecha_min", "brecha_max", "brecha_otro_modelo"]:
        u[f"{col}_%"] = (100 * u[col]).round(1)
    for col in ["precio_m2_esperado", "precio_m2_esperado_inf", "precio_m2_esperado_sup"]:
        u[col] = u[col].round(0)
    u["tasa_completitud"] = u["tasa_completitud"].round(2)
    pasos = ["marcado", "marcado_barrio", "cumple_regla"]
    u[["unidad"] + COLUMNAS_RANKING[:-1] + pasos + ["link"]].to_csv(
        asegurar_directorio(rutas["unidades_marcadas"]), index=False)

    oficial = u[u["cumple_regla"]][COLUMNAS_RANKING].reset_index(drop=True)
    oficial.index += 1
    oficial.to_csv(asegurar_directorio(rutas["ranking"]), index_label="posicion")
    tabla_embudo.to_csv(asegurar_directorio(rutas["embudo"]), index=False)
    return oficial


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 6: precio esperado, brecha y ranking de avisos a investigar.")
    agregar_argumento_config(parser)
    return parser


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    cfg = cargar_config(args.config)
    rutas, cfg_an = cfg["rutas"], cfg["analisis"]

    entrada = resolver(rutas["limpio"])
    if not entrada.exists():
        print(f"[!] No se encontró el dataset limpio: {entrada}")
        print("    Corré primero la etapa 5 (src/limpiar.py).")
        return 1

    print("=== ETAPA 6: ANÁLISIS (PRECIO ESPERADO, BRECHA Y RANKING) ===")
    df = pd.read_csv(entrada, sep="\t", low_memory=False)
    print(f"  {len(df):,} avisos.")
    df = unir_fuentes_externas(df, rutas)
    df, unidades, tabla_embudo, info = analizar(df, cfg_an, cfg["enriquecimiento"])
    oficial = guardar(df, unidades, tabla_embudo, rutas)

    print(f"  Modelo oficial: {info['modelo_oficial']} | error mediano fuera de muestra {100 * info['error_mediano_ciudad']:.1f}% "
          f"(otro modelo {100 * info['error_mediano_otro_modelo']:.1f}%, mediana de la zona "
          f"{100 * info['error_mediano_mediana_zona']:.1f}%)")
    print(f"  Cobertura del intervalo: {100 * info['cobertura_intervalo']:.1f}% | barrios con sub-zona inestable: "
          f"{', '.join(info['barrios_subzona_inestable'])}")
    print("\nEmbudo del ranking:")
    print(tabla_embudo[["filtro", "avisos", "unidades"]].to_string(index=False))

    qc = ControlCalidad("06_analisis", rutas["logs_dir"])
    qc.metrica("filas_entrada", len(df))
    qc.metrica("filas_salida_precio_esperado", len(df))
    qc.metrica("error_mediano_modelo", round(float(info["error_mediano_ciudad"]), 4))
    qc.metrica("error_mediano_mediana_zona", round(info["error_mediano_mediana_zona"], 4))
    qc.metrica("umbral_en_veces_el_error", round(float(info["veces_error"]), 2))
    qc.metrica("modelo_oficial", info["modelo_oficial"])
    qc.metrica("error_mediano_otro_modelo", round(info["error_mediano_otro_modelo"], 4))
    qc.metrica("cobertura_intervalo", round(info["cobertura_intervalo"], 4))
    qc.metrica("barrios_subzona_inestable", ", ".join(info["barrios_subzona_inestable"]))
    qc.metrica("geo_dudoso", int(df["geo_dudoso"].fillna(0).sum()))
    qc.metrica("marcados_consenso", int(df["marcado_consenso"].sum()))
    qc.desglose("embudo_avisos", dict(zip(tabla_embudo["paso"], tabla_embudo["avisos"])))
    qc.desglose("embudo_unidades", dict(zip(tabla_embudo["paso"], tabla_embudo["unidades"])))
    qc.metrica("lista_oficial_unidades", len(oficial))
    qc.metrica("precio_esperado_nulos", int(df["precio_m2_esperado"].isna().sum()))
    for nombre in ["precio_esperado", "unidades_marcadas", "ranking", "embudo"]:
        qc.metrica(f"archivo_{nombre}", ruta_relativa(resolver(rutas[nombre])))
    qc.cerrar()

    if df["precio_m2_esperado"].isna().any():
        print("[!] Hay avisos sin precio esperado.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
