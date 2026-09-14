"""
Chequeo de la versión de Python.

El pipeline se desarrolló y se corrió sobre Python 3.9, que es la versión de
la corrida documentada. Las versiones posteriores también funcionan, pero se
avisa cuando no coinciden: un intérprete distinto, o versiones de
dependencias distintas, pueden cambiar detalles de formato al escribir los
TSV y romper la reproducción byte a byte.
"""

import sys

VERSION_MINIMA = (3, 9)
VERSION_REFERENCIA = (3, 9)


def version_actual() -> str:
    return "{}.{}.{}".format(*sys.version_info[:3])


def verificar_python(avisar=True) -> bool:
    """
    Corta la ejecución si la versión de Python es menor que la mínima.

    Con avisar=True, además imprime una nota cuando la versión no coincide
    con la de la corrida documentada. Devuelve True si coincide.
    """
    actual = sys.version_info[:2]

    if actual < VERSION_MINIMA:
        sys.stderr.write(
            "[!] Python {} no alcanza: este pipeline requiere Python {}.{} o superior.\n"
            "    Las dependencias de requirements.txt no instalan en versiones anteriores.\n".format(
                version_actual(), VERSION_MINIMA[0], VERSION_MINIMA[1]
            )
        )
        raise SystemExit(1)

    if actual != VERSION_REFERENCIA:
        if avisar:
            print(
                "[i] Estás usando Python {}. La corrida documentada se hizo con Python {}.{}.".format(
                    version_actual(), VERSION_REFERENCIA[0], VERSION_REFERENCIA[1]
                )
            )
            print(
                "    El pipeline funciona igual, pero para reproducir los datasets "
                "byte a byte conviene usar la versión de referencia."
            )
        return False

    return True
