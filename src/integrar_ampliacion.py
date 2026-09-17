"""Promueve exclusivamente las fuentes ampliadas validadas y recalcula las coberturas."""

import json
import shutil
from collections import Counter

from ampliar_albumes import read
from diagnostico import ROOT, escribir_csv

NEW = [
    "wikidata_hechos",
    "wikidata_correspondencias",
    "wikidata_entidades",
    "grupo_lanzamiento_correspondencias",
    "grupo_lanzamiento_candidatos",
    "grupos_lanzamientos",
    "grupo_lanzamiento_genero",
    "creditos_grupo_lanzamiento",
    "relaciones_grupo_lanzamiento",
    "artistas_masivos",
    "grabaciones_masivas",
    "lanzamientos_masivos",
    "obras_masivas",
    "creditos_grabaciones_masivos",
    "grabacion_lanzamiento_masivo",
    "isrc_masivos",
    "relaciones_musicales_masivas",
    "eventos_lanzamientos_masivos",
    "grabaciones_correspondencias_masivas",
    "sellos_masivos",
    "lanzamiento_sello_masivo",
]
NEW += ["acousticbrainz_masivo", "acousticbrainz_correspondencias_masivas"]


def integrar_catalogo_artistas(out):
    # Catálogo común: también los artistas adicionales acreditados en grupos.
    artist_rows = read(out / "artistas.csv")
    artist_index = {r["artist_mbid"]: r for r in artist_rows}
    for file, source in [
        ("artistas_masivos.csv", "musicbrainz_completo"),
        ("creditos_grupo_lanzamiento.csv", "musicbrainz_dump"),
    ]:
        for item in read(out / file):
            mid = item["artist_mbid"]
            if mid not in artist_index:
                artist_index[mid] = {
                    "artist_mbid": mid,
                    "nombres_en_dataset": "",
                    "nombre_musicbrainz": item["nombre"],
                    "tipo_musicbrainz": item.get("tipo", ""),
                    "pais_musicbrainz": "",
                    "fuentes": source,
                    "estado_credito": "participante_recuperado_en_relacion",
                    "url_musicbrainz": item["url_evidencia"],
                }
            else:
                row = artist_index[mid]
                sources = row["fuentes"].split("|")
                if source not in sources:
                    sources.append(source)
                row["fuentes"] = "|".join(sources)
                if not row["nombre_musicbrainz"]:
                    row["nombre_musicbrainz"] = item["nombre"]
                    row["url_musicbrainz"] = item["url_evidencia"]
    escribir_csv(out / "artistas.csv", list(artist_index.values()))
    return artist_index


def main():
    src = ROOT / "output/ampliacion"
    out = ROOT / "output/csv"
    for name in NEW + ["canciones"]:
        shutil.copyfile(src / (name + ".csv"), out / (name + ".csv"))
    artist_index = integrar_catalogo_artistas(out)
    songs = read(out / "canciones.csv")
    metrics = json.loads((ROOT / "docs/resultados.json").read_text())
    metrics["cobertura_por_fuente"] = dict(
        Counter(
            source
            for s in songs
            for source in s["fuentes_enriquecimiento"].split("|")
            if source
        )
    )
    metrics["canciones_enriquecidas"] = sum(s["enriquecida"] == "True" for s in songs)
    metrics["canciones_sin_enriquecer"] = len(songs) - metrics["canciones_enriquecidas"]
    for key, file in [
        ("ampliacion_artistas", "ampliacion_artistas"),
        ("ampliacion_albumes", "ampliacion_albumes"),
        ("ampliacion_grabaciones", "ampliacion_musicbrainz_completo"),
    ]:
        metrics[key] = json.loads((ROOT / "docs" / f"{file}.json").read_text())
    metrics["ampliacion_acousticbrainz"] = json.loads(
        (ROOT / "docs/ampliacion_acousticbrainz.json").read_text()
    )
    substantive = {
        "wikidata_artista",
        "musicbrainz_artista",
        "musicbrainz_artista_completo",
    }
    metrics["canciones_con_metadatos_artista_union"] = sum(
        bool(substantive & set(s["fuentes_enriquecimiento"].split("|"))) for s in songs
    )
    metrics["canciones_con_grabacion_union"] = sum(
        bool(s["recording_mbid"] or s["recording_mbid_dump"]) for s in songs
    )
    metrics["tablas_csv"] = 16 + len(NEW)
    metrics["artistas_referenciados"] = len(artist_index)
    (ROOT / "docs/resultados.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
    )
    sources = read(out / "fuentes.csv")
    ids = {s["fuente_id"] for s in sources}
    for row in [
        {
            "fuente_id": "wikidata",
            "url": "https://query.wikidata.org/sparql",
            "documentacion": "https://www.wikidata.org/wiki/Wikidata:Data_access",
            "archivo": "data/raw/wikidata/;data/raw/wikidata_etiquetas/",
            "sha256": "ver manifiesto_archivos.json",
            "licencia": "CC0 datos estructurados",
            "fecha_descarga_utc": "por consulta",
        },
        {
            "fuente_id": "musicbrainz_dump",
            "url": "https://ftp.musicbrainz.org/pub/musicbrainz/data/json-dumps/20260912-001001/release-group.tar.xz",
            "documentacion": "https://musicbrainz.org/doc/MusicBrainz_Database/Download",
            "archivo": "release-group.tar.xz",
            "sha256": metrics["ampliacion_albumes"]["archivo_fuente_sha256"],
            "licencia": "CC0 datos básicos; CC BY-NC-SA 3.0 datos suplementarios",
            "fecha_descarga_utc": "ver manifiesto de extracción",
        },
        {
            "fuente_id": "musicbrainz_completo",
            "url": "https://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/20260916-002105/mbdump.tar.bz2",
            "documentacion": "https://musicbrainz.org/doc/MusicBrainz_Database/Download",
            "archivo": "mbdump.tar.bz2",
            "sha256": json.loads(
                (
                    ROOT
                    / "data/raw/musicbrainz_completo/20260916-002105/subconjunto/extraccion.json"
                ).read_text()
            )["sha256"],
            "licencia": "CC0 núcleo relacional",
            "fecha_descarga_utc": "ver manifiesto de extracción",
        },
    ]:
        if row["fuente_id"] not in ids:
            sources.append(row)
    abmeta = json.loads(
        (
            ROOT / "data/raw/acousticbrainz_dump/20220623/subconjunto/extraccion.json"
        ).read_text()
    )
    for kind, info in abmeta["fuentes"].items():
        sid = "acousticbrainz_dump_" + kind
        if sid not in ids:
            sources.append(
                {
                    "fuente_id": sid,
                    "url": info["url"],
                    "documentacion": "https://acousticbrainz.org/download",
                    "archivo": info["archivo"],
                    "sha256": info["sha256"],
                    "licencia": "CC0",
                    "fecha_descarga_utc": info["fecha_descarga_utc"],
                }
            )
    if "acousticbrainz_dump" not in ids:
        sources.append(
            {
                "fuente_id": "acousticbrainz_dump",
                "url": "https://acousticbrainz.org/download",
                "documentacion": "https://acousticbrainz.org/download",
                "archivo": "Tres archivos: acousticbrainz_dump_lowlevel, acousticbrainz_dump_rhythm, acousticbrainz_dump_tonal",
                "sha256": "Ver hashes individuales en esta tabla y manifiesto de extracción",
                "licencia": "CC0",
                "fecha_descarga_utc": "Ver fechas individuales",
            }
        )
    escribir_csv(out / "fuentes.csv", sources)
    print(
        json.dumps(
            {
                "coberturas": metrics["cobertura_por_fuente"],
                "tablas": metrics["tablas_csv"],
                "enriquecidas": metrics["canciones_enriquecidas"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
