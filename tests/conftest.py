"""
Configuración común de pytest.

Agrega la raíz del repositorio al sys.path para que los tests puedan hacer
`from src import ...` sin instalar el proyecto como paquete, igual que los
scripts de src/.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
