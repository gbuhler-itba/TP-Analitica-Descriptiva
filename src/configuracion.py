"""
Carga de la configuración central del pipeline (config/config.yaml).

La configuración define rutas, cuotas de scraping, delays, cuotas de
paginación y parámetros de geocodificación y enriquecimiento. Cada script
puede pisar cualquier valor por línea de comandos vía argparse.
"""

import argparse

import yaml

from src.rutas import CONFIG_POR_DEFECTO, resolver


def cargar_config(ruta=None) -> dict:
    """Lee el YAML de configuración y lo devuelve como diccionario."""
    destino = resolver(ruta) if ruta else CONFIG_POR_DEFECTO
    if not destino.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración: {destino}"
        )
    with open(destino, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def agregar_argumento_config(parser: argparse.ArgumentParser) -> None:
    """Agrega el flag --config, común a todos los scripts del pipeline."""
    parser.add_argument(
        "--config",
        default=None,
        help="Ruta al YAML de configuración (default: config/config.yaml).",
    )


def elegir(valor_cli, valor_config):
    """Devuelve el valor de CLI si fue especificado, si no el de config."""
    return valor_config if valor_cli is None else valor_cli
