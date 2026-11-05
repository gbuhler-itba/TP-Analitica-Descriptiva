"""
Chequeo del precio esperado con comparables simples (README, sección 10).

Para cada destacado del dashboard (candidato que marcan los dos modelos, sin
exclusiones) se buscan en la base departamentos del mismo barrio con ±1
ambiente, ±30% de superficie y ±15 años de antigüedad, sin la propia unidad ni
los atípicos (IQR sobre el log del precio por m² dentro de la zona, con los
parámetros de la etapa 6). Con al menos `minimo` comparables se compara el
precio esperado y el publicado contra la mediana del precio por m² de esos
comparables. No cambia ninguna salida del pipeline: es un chequeo de
plausibilidad del modelo con una referencia que no usa modelo.

Guarda la tabla por destacado en data/processed/chequeo_comparables.csv y el
resumen (los números del README) en data/processed/chequeo_comparables.json.

Uso:  python3 src/chequeo_comparables.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.configuracion import cargar_config  # noqa: E402
from src.limpieza import outliers_iqr_por_grupo  # noqa: E402
from src.rutas import resolver  # noqa: E402

TOLERANCIA = {"ambientes": 1, "m2_pct": 0.30, "antiguedad": 15}
MINIMO = 5
UMBRAL_BRECHA = -0.25


def cargar_base(cfg):
    """Base de avisos con lo que necesita el chequeo, más la marca de atípico de la etapa 6."""
    cfg_an = cfg["analisis"]
    limpio = pd.read_csv(resolver(cfg["rutas"]["limpio"]), sep="\t", low_memory=False,
                         usecols=["id_aviso", "ambientes", "antiguedad"])
    precio = pd.read_csv(resolver(cfg["rutas"]["precio_esperado"]), sep="\t", low_memory=False,
                         usecols=["id_aviso", "unidad", "barrio", "zona", "m2_final", "precio_m2_usd",
                                  "precio_m2_esperado"])
    base = precio.merge(limpio, on="id_aviso", how="left", validate="one_to_one")
    base["atipico"] = outliers_iqr_por_grupo(np.log(base["precio_m2_usd"]), base["zona"], k=cfg_an["iqr_k"],
                                             minimo_grupo=cfg_an["minimo_grupo"]).values
    return base


def comparables_de(aviso, base):
    """Comparables de un aviso: mismo barrio, ±1 ambiente, ±30% de m², ±15 años, otra unidad, no atípicos."""
    if pd.isna(aviso["ambientes"]) or pd.isna(aviso["antiguedad"]):
        return base.iloc[0:0]
    sel = base[(base["barrio"] == aviso["barrio"]) & (base["unidad"] != aviso["unidad"]) & ~base["atipico"]]
    sel = sel[(sel["ambientes"] - aviso["ambientes"]).abs() <= TOLERANCIA["ambientes"]]
    sel = sel[(sel["m2_final"] / aviso["m2_final"] - 1).abs() <= TOLERANCIA["m2_pct"]]
    return sel[(sel["antiguedad"] - aviso["antiguedad"]).abs() <= TOLERANCIA["antiguedad"]]


def chequear(base, destacados):
    """Una fila por destacado: comparables, mediana de su precio por m² y las dos diferencias."""
    filas = []
    for _, a in destacados.iterrows():
        comp = comparables_de(a, base)
        mediana = comp["precio_m2_usd"].median() if len(comp) else np.nan
        filas.append({"id_aviso": a["id_aviso"], "barrio": a["barrio"], "firme": a["firme"], "segmento": a["segmento"],
                      "comparables": len(comp), "precio_m2_comparables": mediana,
                      "esperado_vs_comparables": a["precio_m2_esperado"] / mediana - 1,
                      "publicado_vs_comparables": a["precio_m2_usd"] / mediana - 1})
    return pd.DataFrame(filas)


def resumir(tabla, minimo=MINIMO, umbral=UMBRAL_BRECHA):
    """Los números del párrafo del README."""
    con = tabla[tabla["comparables"] >= minimo]
    firmes = con[con["firme"]]
    por_segmento = con.groupby("segmento")["esperado_vs_comparables"].median().sort_values(ascending=False)
    return {
        "destacados": int(len(tabla)), "con_comparables": int(len(con)),
        "esperado_vs_comparables_mediana_pct": round(100 * con["esperado_vs_comparables"].median(), 1),
        "debajo_del_umbral_pct": round(100 * (con["publicado_vs_comparables"] <= umbral).mean(), 1),
        "firmes_con_comparables": int(len(firmes)),
        "firmes_debajo_del_umbral": int((firmes["publicado_vs_comparables"] <= umbral).sum()),
        "esperado_vs_comparables_por_segmento_pct": (100 * por_segmento).round(1).to_dict(),
    }


def destacados_del_dashboard(base, ruta=RAIZ / "docs" / "dashboard" / "data" / "avisos.json"):
    avisos = pd.DataFrame(json.load(open(ruta)))
    avisos = avisos[(avisos["nivel"] == "candidato después de costos") & avisos["consenso"]
                    & (avisos["exclusiones"].map(len) == 0)]
    return avisos[["id", "firme", "segmento"]].rename(columns={"id": "id_aviso"}).merge(base, on="id_aviso")


def guardar(tabla, resumen, carpeta):
    """Tabla por destacado (CSV) y resumen (JSON), versionados como evidencia del párrafo del README."""
    carpeta = Path(carpeta)
    tabla.round(4).to_csv(carpeta / "chequeo_comparables.csv", index=False)
    with open(carpeta / "chequeo_comparables.json", "w", encoding="utf-8") as f:
        json.dump({**resumen, "criterio": {**TOLERANCIA, "minimo_comparables": MINIMO, "umbral_brecha": UMBRAL_BRECHA}},
                  f, ensure_ascii=False, indent=1)


def main(carpeta=None):
    cfg = cargar_config()
    base = cargar_base(cfg)
    tabla = chequear(base, destacados_del_dashboard(base))
    resumen = resumir(tabla)
    guardar(tabla, resumen, carpeta or resolver(cfg["rutas"]["limpio"]).parent)
    sin = int((tabla["comparables"] < MINIMO).sum())
    print(f"Destacados: {resumen['destacados']} | con al menos {MINIMO} comparables: {resumen['con_comparables']} "
          f"(sin suficientes: {sin}, de los cuales sin ambientes o antigüedad: "
          f"{int(tabla.merge(base[['id_aviso', 'ambientes', 'antiguedad']], on='id_aviso')[['ambientes', 'antiguedad']].isna().any(axis=1).sum())})")
    print(f"Esperado contra la mediana de los comparables: {resumen['esperado_vs_comparables_mediana_pct']:+.1f}% (mediana)")
    print(f"Publicado 25% o más por debajo de los comparables: {resumen['debajo_del_umbral_pct']:.1f}% "
          f"({resumen['firmes_debajo_del_umbral']} de {resumen['firmes_con_comparables']} firmes con comparables)")
    print("Esperado contra comparables por segmento (mediana, %):")
    for k, v in resumen["esperado_vs_comparables_por_segmento_pct"].items():
        print(f"  {k}: {v:+.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
