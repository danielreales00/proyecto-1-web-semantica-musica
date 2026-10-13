"""Verificación de integridad, evidencia y correspondencias exportadas."""

import csv
import gzip
import hashlib
import json
import math
import random
import zipfile

from integrar import leer
from musica.comun.rutas import ROOT


def validar_canciones(original, songs, check):
    ids = {r["track_id"] for r in original}
    outids = {r["track_id"] for r in songs}
    check(
        len(songs) == len(original) == len(outids),
        "100.000 filas e identificadores únicos conservados",
    )
    check(ids == outids, "Igualdad exacta de identificadores de entrada y salida")
    check(
        all(all(a[k] == b[k] for k in a) for a, b in zip(original, songs)),
        "Todas las celdas originales y su orden conservados",
    )
    check(
        all(s["anio_normalizado"] == "" for s in songs if s["year"] == "0"),
        "Año cero normalizado como desconocido",
    )
    # Integridad de claves de canciones en todos los CSV que usan track_id.
    for p in sorted((ROOT / "output/csv").glob("*.csv")):
        with p.open(newline="") as f:
            reader = csv.DictReader(f)
            if "track_id" in reader.fieldnames:
                check(
                    all(r["track_id"] in ids for r in reader),
                    f"Claves de canción válidas: {p.name}",
                )


def validar_descriptores(acoustic, check):
    check(
        len(acoustic) == len({r["track_id"] for r in acoustic}),
        "Descriptores sin multiplicación de filas",
    )
    feature_cols = [k for k in acoustic[0] if "_Overall_" in k]
    check(len(feature_cols) == 16, "Esquema acústico de 16 características")
    check(
        all(math.isfinite(float(r[k])) for r in acoustic for k in feature_cols if r[k]),
        "Descriptores numéricos finitos",
    )
    # Revisión independiente de valores publicados contra 30 líneas del archivo fuente.
    chosen = random.Random(47).sample(acoustic, min(30, len(acoustic)))
    line_index = {int(r["linea_fuente"]): r for r in chosen}
    review = []
    with gzip.open(ROOT / "data/raw/msd-jmir-spectral-all-all-v1.0.arff.gz", "rt") as f:
        for num, line in enumerate(f, 1):
            if num in line_index:
                cells = next(csv.reader([line], quotechar="'"))
                r = line_index[num]
                check(
                    cells[-1] == r["track_id"]
                    and cells[:-1] == [r[k] for k in feature_cols],
                    f"Evidencia acústica exacta: {r['track_id']}",
                )
                review.append(
                    {
                        "track_id": r["track_id"],
                        "tipo": "acustica",
                        "linea": num,
                        "resultado": "coincide_exacto",
                    }
                )
    return review


def validar_generos(genres, check):
    review = []
    with zipfile.ZipFile(ROOT / "data/raw/msd_tagtraum_cd2.cls.zip") as z:
        lines = z.read("msd_tagtraum_cd2.cls").decode().splitlines()
    for r in random.Random(48).sample(genres, min(30, len(genres))):
        cells = lines[int(r["linea_fuente"]) - 1].split("\t")
        index = 1 if r["papel"] == "mayoritario" else 2
        check(
            cells[0] == r["track_id"] and cells[index] == r["genero"],
            f"Evidencia de género exacta: {r['track_id']}",
        )
        review.append(
            {
                "track_id": r["track_id"],
                "tipo": "genero",
                "linea": r["linea_fuente"],
                "resultado": "coincide_exacto",
            }
        )
    return review


def validar_musicbrainz(check):
    recs = leer(ROOT / "output/csv/grabaciones.csv")
    recids = {r["recording_mbid"] for r in recs}
    releases = leer(ROOT / "output/csv/lanzamientos.csv")
    relids = {r["release_mbid"] for r in releases}
    joins = leer(ROOT / "output/csv/grabacion_lanzamiento.csv")
    check(
        all(
            r["recording_mbid"] in recids and r["release_mbid"] in relids for r in joins
        ),
        "Integridad grabación-lanzamiento",
    )
    matches = leer(ROOT / "output/csv/musicbrainz_correspondencias.csv")
    cands = leer(ROOT / "output/csv/musicbrainz_candidatos.csv")
    for m in matches:
        eligible = {
            r["recording_mbid"]
            for r in cands
            if r["track_id"] == m["track_id"] and r["elegible"] == "True"
        }
        if m["estado"] == "aceptada":
            check(
                eligible == {m["recording_mbid"]},
                f"Candidato único aceptado: {m['track_id']}",
            )
        else:
            check(
                not m["recording_mbid"],
                f"No se acepta caso no resuelto: {m['track_id']}",
            )
    check(
        all(
            m["recording_mbid"] in recids for m in matches if m["estado"] == "aceptada"
        ),
        "Toda correspondencia aceptada referencia una grabación exportada",
    )
    artists = {r["artist_mbid"] for r in leer(ROOT / "output/csv/artistas.csv")}
    check(
        all(
            r["artist_mbid"] in artists
            for r in leer(ROOT / "output/csv/creditos_grabacion.csv")
        ),
        "Todos los créditos referencian artistas exportados",
    )
    works = {r["work_mbid"] for r in leer(ROOT / "output/csv/obras.csv")}
    for rel in leer(ROOT / "output/csv/relaciones_musicbrainz.csv"):
        check(
            rel["sujeto_id"]
            in (recids if rel["sujeto_tipo"] == "grabacion" else works),
            "Sujeto de relación musical exportado",
        )
        if rel["objeto_tipo"] == "artist":
            check(rel["objeto_id"] in artists, "Artista relacionado exportado")
        if rel["objeto_tipo"] == "work":
            check(rel["objeto_id"] in works, "Obra relacionada exportada")
    ab = leer(ROOT / "output/csv/acousticbrainz.csv")
    matchmap = {m["track_id"]: m for m in matches}
    check(
        all(
            r["recording_mbid"] in recids
            and matchmap[r["track_id"]]["recording_mbid"] == r["recording_mbid"]
            for r in ab
        ),
        "AcousticBrainz vinculado a grabaciones reconciliadas",
    )


def validar_evidencia(check):
    for name in [
        "grabaciones.csv",
        "lanzamientos.csv",
        "obras.csv",
        "relaciones_musicbrainz.csv",
        "acousticbrainz.csv",
    ]:
        for r in leer(ROOT / "output/csv" / name):
            check(
                (
                    ROOT
                    / "data/raw/api"
                    / f"{hashlib.sha256(r['url_evidencia'].encode()).hexdigest()}.json"
                ).exists(),
                "Evidencia API disponible: " + name,
            )
    for path in (ROOT / "data/raw").glob("*.json"):
        m = json.loads(path.read_text())
        check(
            hashlib.file_digest(
                (ROOT / "data/raw" / m["archivo"]).open("rb"), "sha256"
            ).hexdigest()
            == m["sha256"],
            f"SHA-256 fuente {m['fuente_id']}",
        )


def main():
    checks = []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        checks.append(message)

    original = leer(ROOT / "grupo_2.csv")
    songs = leer(ROOT / "output/csv/canciones.csv")
    validar_canciones(original, songs, check)
    genres = leer(ROOT / "output/csv/cancion_genero.csv")
    acoustic = leer(ROOT / "output/csv/descriptores_acusticos.csv")
    review = validar_descriptores(acoustic, check)
    review.extend(validar_generos(genres, check))
    validar_musicbrainz(check)
    validar_evidencia(check)
    metrics = json.loads((ROOT / "docs/resultados.json").read_text())
    check(
        metrics["canciones_enriquecidas"]
        == sum(r["enriquecida"] == "True" for r in songs),
        "Métricas y CSV coinciden",
    )
    from musica.comun.archivos_csv import escribir_csv

    escribir_csv(ROOT / "docs/auditoria_evidencia.csv", review)
    result = {
        "estado": "correcto",
        "comprobaciones": len(checks),
        "muestra_evidencia": len(review),
        "detalle": checks,
    }
    (ROOT / "docs/validacion.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        f"{len(checks)} comprobaciones correctas; {len(review)} registros contrastados con fuentes originales."
    )


if __name__ == "__main__":
    main()
