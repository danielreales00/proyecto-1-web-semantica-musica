"""Lectores estrictos: vinculación exacta por track_id y conservación de evidencia."""

import csv
import gzip
import io
import json
import math
import zipfile

from descargar import FUENTES
from diagnostico import ROOT, escribir_csv


def generos(ids):
    found = []
    with zipfile.ZipFile(ROOT / "data/raw" / FUENTES["tagtraum"]["archivo"]) as z:
        with z.open("msd_tagtraum_cd2.cls") as raw:
            for line_no, line in enumerate(io.TextIOWrapper(raw, encoding="utf-8"), 1):
                if line.startswith("#") or not line.strip():
                    continue
                cells = line.strip().split("\t")
                if cells[0] not in ids:
                    continue
                if len(cells) not in (2, 3):
                    raise ValueError(f"Género: fila inesperada {line_no}")
                for rank, label in enumerate(cells[1:], 1):
                    found.append(
                        {
                            "track_id": cells[0],
                            "genero": label,
                            "papel": "mayoritario" if rank == 1 else "minoritario",
                            "fuente_id": "tagtraum",
                            "identificador_fuente": cells[0],
                            "metodo": "track_id_exacto",
                            "archivo_fuente": FUENTES["tagtraum"]["archivo"],
                            "linea_fuente": line_no,
                        }
                    )
    return found


def fila_acustica(attrs, values, line_no):
    tid = values[-1]
    feature_values = {}
    for key, val in zip(attrs[:-1], values[:-1]):
        feature_values[key] = "" if val == "?" or not math.isfinite(float(val)) else val
    return {
        "track_id": tid,
        **feature_values,
        "fuente_id": "jmir",
        "identificador_fuente": tid,
        "metodo": "track_id_exacto",
        "archivo_fuente": FUENTES["jmir"]["archivo"],
        "linea_fuente": line_no,
    }


def acustica(ids):
    found = []
    attrs = []
    in_data = False
    with gzip.open(ROOT / "data/raw" / FUENTES["jmir"]["archivo"], "rt") as f:
        for line_no, line in enumerate(f, 1):
            if not in_data:
                if line.lower().startswith("@attribute"):
                    attrs.append(line.split()[1])
                if line.lower().startswith("@data"):
                    in_data = True
                continue
            if not line.strip() or line.startswith("%"):
                continue
            # ARFF de esta fuente: números sin comas internas + ID entre comillas simples.
            values = next(csv.reader([line], quotechar="'"))
            if len(values) != len(attrs):
                raise ValueError(f"ARFF: columnas inesperadas {line_no}")
            tid = values[-1]
            if tid not in ids:
                continue
            found.append(fila_acustica(attrs, values, line_no))
    if not in_data or len(attrs) != 17:
        raise ValueError("Esquema ARFF inesperado")
    if len({r["track_id"] for r in found}) != len(found):
        raise ValueError("ID acústico duplicado")
    return found, attrs[:-1]


def ejecutar(piloto=False):
    file = "piloto_1000.csv" if piloto else "base_normalizada.csv"
    rows = list(csv.DictReader((ROOT / "data/processed" / file).open()))
    ids = {r["track_id"] for r in rows}
    g = generos(ids)
    a, attrs = acustica(ids)
    gs = {r["track_id"] for r in g}
    ass = {r["track_id"] for r in a if any(r[k] != "" for k in attrs)}
    result = {
        "filas": len(rows),
        "canciones_con_genero": len(gs),
        "canciones_con_acustica": len(ass),
        "canciones_enriquecidas": len(gs | ass),
        "relaciones_genero": len(g),
        "descriptores_acusticos": len(attrs),
        "cobertura_por_descriptor": {k: sum(r[k] != "" for r in a) for k in attrs},
    }
    if piloto:
        result["por_estrato"] = {
            s: {
                "filas": len([r for r in rows if r["estrato"] == s]),
                "enriquecidas": sum(
                    r["track_id"] in gs | ass for r in rows if r["estrato"] == s
                ),
            }
            for s in sorted({r["estrato"] for r in rows})
        }
        (ROOT / "docs/piloto_fuentes_masivas.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
    else:
        escribir_csv(ROOT / "output/csv/cancion_genero.csv", g)
        escribir_csv(ROOT / "output/csv/descriptores_acusticos.csv", a)
        (ROOT / "docs/cobertura_masiva.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--piloto", action="store_true")
    args = p.parse_args()
    ejecutar(args.piloto)
