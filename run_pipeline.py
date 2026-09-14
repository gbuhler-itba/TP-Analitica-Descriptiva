"""
Runner único del pipeline del TP 1.

Ejecuta la cadena completa en orden. Por defecto ARRANCA EN LA ETAPA 2,
asumiendo que las cuotas del scraping ya están descargadas en
data/raw/cuotas/ (vienen versionadas en el repositorio).

    python3 run_pipeline.py                      # etapas 2, 3 y 4
    python3 run_pipeline.py --desde-etapa 3      # etapas 3 y 4
    python3 run_pipeline.py --hasta-etapa 3      # etapas 2 y 3
    python3 run_pipeline.py --incluir-scraping   # etapas 1, 2, 3 y 4

La etapa 1 (scraping) solo corre con --incluir-scraping explícito: son
entre 8 y 15 horas y requiere IP residencial. La etapa 3 (geocodificación)
son unas 2 horas contra un servicio público gratuito.

Cada etapa cierra con su bloque de control de calidad, que se imprime y se
escribe en outputs/logs/.
"""

import sys

# Chequeo de versión ANTES de importar nada del proyecto o de terceros, para
# que un intérprete viejo falle con un mensaje claro y no con un SyntaxError
# o un ImportError.
if sys.version_info[:2] < (3, 9):
    sys.stderr.write(
        "[!] Python {}.{}.{} no alcanza: este pipeline requiere Python 3.9 o superior.\n"
        "    Las dependencias de requirements.txt no instalan en versiones anteriores.\n".format(
            *sys.version_info[:3]
        )
    )
    raise SystemExit(1)

import argparse
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import enriquecimiento, geocoding_propiedades, scrapper_mercadolibre, unir_cuotas
from src.entorno import verificar_python, version_actual
from src.configuracion import agregar_argumento_config, cargar_config
from src.rutas import resolver

ETAPAS = {
    1: "scraping",
    2: "consolidacion",
    3: "geocoding",
    4: "enriquecimiento",
}


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Corre el pipeline completo del TP 1 en orden.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Etapas:\n"
            "  1  scraping         MercadoLibre  -> data/raw/cuotas/cuota*.tsv\n"
            "  2  consolidacion    cuotas        -> data/interim/mercadolibre_CABA_completo.tsv\n"
            "  3  geocoding        consolidado   -> data/interim/propiedades_geocodificadas.tsv\n"
            "  4  enriquecimiento  geocodificado -> data/processed/propiedades_enriquecidas.tsv\n"
        ),
    )
    agregar_argumento_config(parser)
    parser.add_argument("--desde-etapa", type=int, default=None, choices=[1, 2, 3, 4],
                        help="Primera etapa a ejecutar (default: 2, o 1 con --incluir-scraping).")
    parser.add_argument("--hasta-etapa", type=int, default=4, choices=[1, 2, 3, 4],
                        help="Última etapa a ejecutar (default: 4).")
    parser.add_argument("--incluir-scraping", action="store_true",
                        help="Habilita la etapa 1. Sin este flag el scraping NUNCA corre.")
    parser.add_argument("--cuotas", nargs="+", default=None,
                        help="Cuotas a scrapear en la etapa 1 (default: todas las de config).")
    parser.add_argument("--sin-detalle", action="store_true",
                        help="Etapa 1 sin entrar a la ficha de cada aviso (mucho más rápido).")
    parser.add_argument("--max-paginas", type=int, default=None,
                        help="Etapa 1: tope de páginas por barrio.")
    parser.add_argument("--limite-geocoding", type=int, default=None,
                        help="Etapa 3: procesar solo las primeras N direcciones pendientes.")
    parser.add_argument("--verificar-geocoding", action="store_true",
                        help="Etapa 3 en modo verificación: valida el geocodificado ya "
                             "existente sin llamar a USIG. Permite validar la cadena entera "
                             "en segundos en vez de repetir dos horas de consultas.")
    parser.add_argument("--forzar-descarga-subte", action="store_true",
                        help="Etapa 4: rebajar el GeoJSON de subte aunque exista el cache.")
    return parser


def encabezado(texto: str) -> None:
    print()
    print("#" * 70)
    print(f"# {texto}")
    print("#" * 70)


def correr_etapa_1(args, cfg) -> int:
    cuotas = args.cuotas or list(cfg["scraping"]["cuotas"])
    for nombre in cuotas:
        encabezado(f"ETAPA 1/4 - SCRAPING ({nombre})")
        argv = ["--cuota", nombre]
        if args.config:
            argv += ["--config", args.config]
        if args.sin_detalle:
            argv.append("--sin-detalle")
        if args.max_paginas is not None:
            argv += ["--max-paginas", str(args.max_paginas)]
        codigo = scrapper_mercadolibre.main(argv)
        if codigo != 0:
            return codigo
    return 0


def correr_etapa_2(args) -> int:
    encabezado("ETAPA 2/4 - CONSOLIDACIÓN DE CUOTAS")
    argv = ["--config", args.config] if args.config else []
    return unir_cuotas.main(argv)


def correr_etapa_3(args) -> int:
    if args.verificar_geocoding:
        encabezado("ETAPA 3/4 - GEOCODIFICACIÓN (modo verificación, sin red)")
        argv = ["--config", args.config] if args.config else []
        return geocoding_propiedades.main(argv + ["--verificar"])

    encabezado("ETAPA 3/4 - GEOCODIFICACIÓN (USIG)")
    argv = ["--config", args.config] if args.config else []
    if args.limite_geocoding is not None:
        argv += ["--limite", str(args.limite_geocoding)]
    return geocoding_propiedades.main(argv)


def correr_etapa_4(args) -> int:
    encabezado("ETAPA 4/4 - ENRIQUECIMIENTO")
    argv = ["--config", args.config] if args.config else []
    if args.forzar_descarga_subte:
        argv.append("--forzar-descarga")
    return enriquecimiento.main(argv)


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    verificar_python(avisar=True)
    cfg = cargar_config(args.config)

    desde = args.desde_etapa
    if desde is None:
        desde = 1 if args.incluir_scraping else 2
    hasta = args.hasta_etapa

    if desde > hasta:
        print(f"[!] --desde-etapa ({desde}) es mayor que --hasta-etapa ({hasta}).")
        return 2

    if desde == 1 and not args.incluir_scraping:
        print("[!] La etapa 1 (scraping) requiere --incluir-scraping explícito.")
        print("    Son entre 8 y 15 horas y hace falta IP residencial.")
        print("    Las cuotas ya descargadas están versionadas en data/raw/cuotas/.")
        return 2

    etapas = [e for e in (1, 2, 3, 4) if desde <= e <= hasta]
    inicio = datetime.now()

    print("=" * 70)
    print("PIPELINE TP 1 - FONDO DE INVERSIÓN INMOBILIARIO (CABA)")
    print("=" * 70)
    print(f"Python:               {version_actual()}")
    print(f"Raíz del repositorio: {RAIZ}")
    print(f"Configuración:        {resolver(args.config) if args.config else 'config/config.yaml'}")
    print(f"Etapas a ejecutar:    {', '.join(f'{e} ({ETAPAS[e]})' for e in etapas)}")
    print(f"Inicio:               {inicio.strftime('%Y-%m-%d %H:%M:%S')}")

    corredores = {1: lambda: correr_etapa_1(args, cfg), 2: lambda: correr_etapa_2(args),
                  3: lambda: correr_etapa_3(args), 4: lambda: correr_etapa_4(args)}

    duraciones = {}
    for etapa in etapas:
        t0 = time.time()
        codigo = corredores[etapa]()
        duraciones[etapa] = time.time() - t0
        if codigo != 0:
            print(f"\n[!] La etapa {etapa} ({ETAPAS[etapa]}) terminó con código {codigo}. Se corta el pipeline.")
            return codigo

    fin = datetime.now()
    print()
    print("=" * 70)
    print("PIPELINE COMPLETO")
    print("=" * 70)
    for etapa, seg in duraciones.items():
        print(f"  etapa {etapa} ({ETAPAS[etapa]}): {seg / 60:.1f} min")
    print(f"  total: {(fin - inicio).total_seconds() / 60:.1f} min")
    print(f"  logs:  {resolver(cfg['rutas']['logs_dir'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
