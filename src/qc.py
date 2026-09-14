"""
Controles de calidad del pipeline.

Cada etapa cierra con un bloque de control que reporta, como mínimo:
  - filas de entrada y filas de salida
  - duplicados detectados y eliminados
  - nulos por columna clave
  - tasa de éxito de geocodificación (en las etapas que corresponde)

El reporte se imprime por pantalla y se escribe en dos archivos dentro de
outputs/logs/:
  - pipeline.log       texto acumulativo, legible, con timestamp por corrida
  - qc_<etapa>.json    la misma información en formato consumible por código
"""

import json
from datetime import datetime

import pandas as pd

from src.rutas import resolver

SEPARADOR = "=" * 62


class ControlCalidad:
    """Acumula métricas de una etapa, las imprime y las persiste a log."""

    def __init__(self, etapa: str, logs_dir, corrida: str = None):
        self.etapa = etapa
        self.logs_dir = resolver(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.corrida = corrida or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.metricas = {}
        self.lineas = []

    # -- registro -----------------------------------------------------------

    def metrica(self, nombre: str, valor) -> None:
        """Registra una métrica escalar."""
        if hasattr(valor, "item"):
            valor = valor.item()
        self.metricas[nombre] = valor

    def desglose(self, nombre: str, mapping: dict) -> None:
        """Registra una métrica compuesta (por ejemplo, conteo por estado)."""
        self.metricas[nombre] = {
            str(k): int(v) if hasattr(v, "item") or isinstance(v, bool) else v
            for k, v in mapping.items()
        }

    def nulos_por_columna(self, df: pd.DataFrame, columnas, nombre="nulos_columnas_clave") -> None:
        """Cuenta nulos en las columnas clave que existan en el DataFrame."""
        presentes = [c for c in columnas if c in df.columns]
        faltantes = [c for c in columnas if c not in df.columns]
        self.desglose(nombre, {c: int(df[c].isna().sum()) for c in presentes})
        if faltantes:
            self.metricas[f"{nombre}_columnas_ausentes"] = faltantes

    def duplicados(self, df: pd.DataFrame, subset, nombre="duplicados") -> int:
        """Cuenta duplicados sobre una clave y registra el resultado."""
        n = int(df.duplicated(subset=subset).sum())
        self.metrica(nombre, n)
        return n

    def tasa_geocoding(self, df: pd.DataFrame, columna="geo_status", sufijo="") -> None:
        """
        Registra el desglose de estados de geocodificación y la tasa de éxito.

        El sufijo permite distinguir el alcance. En una corrida parcial
        (--limite) la tasa sobre el dataset completo no dice nada útil, así
        que se reporta además la tasa sobre las filas realmente procesadas.
        """
        if columna not in df.columns:
            return
        conteo = df[columna].value_counts(dropna=False)
        self.desglose(f"geocoding_por_estado{sufijo}", {str(k): int(v) for k, v in conteo.items()})
        total = len(df)
        ok = int((df[columna] == "OK").sum())
        self.metrica(f"geocoding_ok{sufijo}", ok)
        self.metrica(f"geocoding_tasa_exito{sufijo}_pct", round(100 * ok / total, 2) if total else 0.0)

    # -- salida -------------------------------------------------------------

    def _formatear(self) -> str:
        out = [SEPARADOR, f"CONTROL DE CALIDAD | etapa: {self.etapa} | corrida: {self.corrida}", SEPARADOR]
        for nombre, valor in self.metricas.items():
            if isinstance(valor, dict):
                out.append(f"{nombre}:")
                ancho = max((len(str(k)) for k in valor), default=0)
                for k, v in valor.items():
                    out.append(f"    {str(k):<{ancho}}  {v}")
            elif isinstance(valor, list):
                out.append(f"{nombre}: {', '.join(str(v) for v in valor)}")
            else:
                out.append(f"{nombre}: {valor}")
        out.append(SEPARADOR)
        return "\n".join(out)

    def cerrar(self) -> dict:
        """Imprime el reporte y lo persiste en outputs/logs/."""
        texto = self._formatear()
        print()
        print(texto)

        with open(self.logs_dir / "pipeline.log", "a", encoding="utf-8") as fh:
            fh.write(texto + "\n\n")

        destino_json = self.logs_dir / f"qc_{self.etapa}.json"
        payload = {"etapa": self.etapa, "corrida": self.corrida, "metricas": self.metricas}
        with open(destino_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        print(f"[qc] Log:  {self.logs_dir / 'pipeline.log'}")
        print(f"[qc] JSON: {destino_json}")
        return self.metricas
