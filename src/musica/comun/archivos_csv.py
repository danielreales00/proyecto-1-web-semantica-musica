"""Escritura uniforme de los CSV consolidados."""

import csv
from pathlib import Path


def escribir_csv(path, rows, fields=None):
    """Conserva el orden de columnas y las convenciones de la entrega inicial."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)
