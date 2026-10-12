"""Raíz del proyecto, sustituible para reproducir en una carpeta nueva."""

import os
from pathlib import Path

ROOT = Path(
    os.environ.get("PROYECTO_ROOT", Path(__file__).resolve().parents[3])
).resolve()
