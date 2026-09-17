"""Diagnóstico y selección reproducible del piloto, sin modificar la entrada."""

import csv
import hashlib
import json
import math
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(
    os.environ.get("PROYECTO_ROOT", Path(__file__).resolve().parents[1])
).resolve()
MBID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


def normalizar(s):
    return " ".join(unicodedata.normalize("NFKC", s).casefold().split())


def escribir_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def evaluar_anio(value):
    flags = []
    try:
        year = int(value)
        if year == 0:
            flags.append("anio_desconocido")
        elif not 1850 <= year <= 2026:
            flags.append("anio_fuera_rango")
    except ValueError:
        year = 0
        flags.append("anio_no_entero")
    return year, flags


def diagnosticar_fila(row, ids, mb_names):
    year, flags = evaluar_anio(row["year"])
    try:
        duration = float(row["duration"])
        if not math.isfinite(duration) or duration <= 0:
            flags.append("duracion_invalida")
    except ValueError:
        flags.append("duracion_invalida")
    if not MBID.fullmatch(row["artist_mbid"]):
        flags.append("mbid_formato_invalido")
    if len(mb_names[row["artist_mbid"]]) > 1:
        flags.append("mbid_varios_nombres")
    if any(not value.strip() for value in row.values()):
        flags.append("campo_vacio")
    if re.search(r"\b(live|remaster|remix|version|edit)\b", row["title"], re.I):
        flags.append("version_en_titulo")
    if ids[row["track_id"]] > 1:
        flags.append("track_id_duplicado")
    return year, flags


def preparar_filas(rows, ids, mb_names):
    errors = []
    groups = defaultdict(list)
    clean = []
    for r in rows:
        y, flags = diagnosticar_fila(r, ids, mb_names)
        errors.extend({"track_id": r["track_id"], "incidencia": flag} for flag in flags)
        stratum = ("anio_desconocido" if y == 0 else "anio_conocido") + (
            "_variante" if "version_en_titulo" in flags else "_simple"
        )
        groups[stratum].append(r)
        clean.append(
            {
                **r,
                "titulo_normalizado": normalizar(r["title"]),
                "artista_normalizado": normalizar(r["artist_name"]),
                "lanzamiento_normalizado": normalizar(r["release"]),
                "anio_normalizado": y
                if y > 0 and "anio_fuera_rango" not in flags
                else "",
                "incidencias": "|".join(flags),
            }
        )
    return errors, groups, clean


def seleccionar_piloto(groups, total):
    rng = random.Random(20260916)
    sample = []
    allocation = {}
    remaining = 1000
    for i, (name, group) in enumerate(sorted(groups.items())):
        n = remaining if i == len(groups) - 1 else round(len(group) / total * 1000)
        remaining -= n
        allocation[name] = {"poblacion": len(group), "muestra": n}
        sample += [
            {**r, "estrato": name}
            for r in rng.sample(sorted(group, key=lambda r: r["track_id"]), n)
        ]
    sample.sort(key=lambda r: r["track_id"])
    return sample, allocation


def main():
    entrada = ROOT / "grupo_2.csv"
    rows = list(csv.DictReader(entrada.open(encoding="utf-8-sig", newline="")))
    ids = Counter(r["track_id"] for r in rows)
    mb_names = defaultdict(set)
    for row in rows:
        mb_names[row["artist_mbid"]].add(row["artist_name"])
    errors, groups, clean = preparar_filas(rows, ids, mb_names)
    sample, allocation = seleccionar_piloto(groups, len(rows))
    summary = {
        "archivo": "grupo_2.csv",
        "sha256": hashlib.sha256(entrada.read_bytes()).hexdigest(),
        "filas": len(rows),
        "track_id_unicos": len(ids),
        "columnas": list(rows[0]),
        "valores_unicos": {k: len(set(r[k] for r in rows)) for k in rows[0]},
        "incidencias": dict(Counter(e["incidencia"] for e in errors)),
        "mbid_con_varios_nombres": sum(len(v) > 1 for v in mb_names.values()),
        "anio_minimo_no_cero": min(int(r["year"]) for r in rows if int(r["year"]) > 0),
        "anio_maximo": max(int(r["year"]) for r in rows),
        "duracion_min": min(float(r["duration"]) for r in rows),
        "duracion_max": max(float(r["duration"]) for r in rows),
        "piloto": {"semilla": 20260916, "estratos": allocation, "filas": len(sample)},
    }
    (ROOT / "docs/diagnostico.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    escribir_csv(ROOT / "data/processed/base_normalizada.csv", clean)
    escribir_csv(ROOT / "data/processed/piloto_1000.csv", sample)
    escribir_csv(
        ROOT / "data/processed/incidencias.csv", errors, ["track_id", "incidencia"]
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
