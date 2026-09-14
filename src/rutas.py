"""
Resolución de rutas del proyecto.

Todas las rutas del pipeline se derivan de la raíz del repositorio, que se
calcula a partir de la ubicación de este archivo. Ningún script depende del
directorio de trabajo desde el que se lo invoque ni de rutas absolutas de
una máquina en particular.
"""

from pathlib import Path

# src/rutas.py -> src/ -> raíz del repo
RAIZ = Path(__file__).resolve().parents[1]

CONFIG_POR_DEFECTO = RAIZ / "config" / "config.yaml"


def resolver(ruta) -> Path:
    """
    Convierte una ruta de la configuración en una ruta absoluta.

    Las rutas relativas se interpretan siempre respecto de la raíz del repo.
    Las rutas absolutas se respetan tal cual, para permitir que alguien
    apunte a un disco externo vía --entrada / --salida sin editar código.
    """
    p = Path(ruta).expanduser()
    return p if p.is_absolute() else (RAIZ / p)


def asegurar_directorio(ruta_archivo) -> Path:
    """Crea el directorio contenedor de un archivo y devuelve la ruta resuelta."""
    destino = resolver(ruta_archivo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


def ruta_relativa(ruta) -> str:
    """
    Devuelve la ruta relativa a la raíz del repo, para mostrar en logs.

    Si la ruta cae fuera del repo (por ejemplo, porque se pasó una salida
    absoluta por línea de comandos) devuelve la ruta completa.
    """
    destino = resolver(ruta)
    try:
        return str(destino.relative_to(RAIZ))
    except ValueError:
        return str(destino)
