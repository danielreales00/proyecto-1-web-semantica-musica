"""Comparación de cobertura sobre exactamente las mismas 1.000 canciones."""

import csv
import hashlib
import json

from musica.comun.rutas import ROOT


def ejemplo_tipos():
    example = {
        "artista": "Andrés Cabas",
        "artist_mbid": "0696ab5b-a92b-4190-addc-48d3a4601111",
        "alcance": "Clasificaciones de un mismo artista, verificadas en las respuestas guardadas del piloto.",
    }
    sources = {
        "dbpedia": (
            "43ba8cfead7d593f317909d8908345e849725b540bdad4f0b9ba0ffe5eb26c2c",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        ),
        "wikidata": (
            "ac87a0f83e8e6dd74b4f618a48bcf2fff3c4c85d1342d36ff6312d5f678328e8",
            "http://www.wikidata.org/prop/direct/P31",
        ),
    }
    for source, (key, prop) in sources.items():
        path = ROOT / "data/raw" / source / (key + ".json")
        env = json.loads(path.read_text())
        assert hashlib.sha256(env["consulta"].encode()).hexdigest() == key
        facts = []
        for binding in env["data"]["results"]["bindings"]:
            row = {k: v["value"] for k, v in binding.items()}
            if row["mbid"] == example["artist_mbid"] and row.get("propiedad") == prop:
                fact = {k: row[k] for k in ["artista", "propiedad", "valor"]}
                if fact not in facts:
                    facts.append(fact)
        facts.sort(key=lambda f: (f["artista"], f["valor"]))
        assert facts
        example[source] = {
            "servicio": env["endpoint"],
            "fecha_consulta": env["fecha_utc"],
            "consulta_sha256": key,
            "archivo_respuesta": path.relative_to(ROOT).as_posix(),
            "respuesta_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "afirmaciones_de_tipo": facts,
        }
    return example


def main():
    songs = list(csv.DictReader((ROOT / "data/processed/piloto_1000.csv").open()))
    summary = {}
    sets = {}
    for source in ["wikidata", "dbpedia"]:
        summary[source] = json.loads(
            (ROOT / "docs" / f"piloto_{source}.json").read_text()
        )
        links = list(
            csv.DictReader(
                (
                    ROOT / "data/processed" / f"piloto_{source}_correspondencias.csv"
                ).open()
            )
        )
        valid = {r["artist_mbid"] for r in links if r["estado"] == "unica"}
        assert valid <= {s["artist_mbid"] for s in songs}
        sets[source] = {s["track_id"] for s in songs if s["artist_mbid"] in valid}
        assert (
            len(sets[source])
            == summary[source]["canciones_con_artista_vinculado_unico"]
        )
    w, d = sets["wikidata"], sets["dbpedia"]
    result = {
        "piloto": 1000,
        "ambas": len(w & d),
        "solo_wikidata": len(w - d),
        "solo_dbpedia": len(d - w),
        "ninguna": 1000 - len(w | d),
        "diferencia_dbpedia_menos_wikidata": len(d) - len(w),
        "comparacion": "Cobertura de identidad por identificador suministrado. Los hechos no son equivalentes uno a uno: esquemas y propiedades consultadas distintos.",
    }
    result["ejemplo_conteo_tipos"] = ejemplo_tipos()
    (ROOT / "docs/comparacion_dbpedia_wikidata.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    text = [
        "# Prueba rápida: DBpedia frente a Wikidata",
        "Se usó el mismo piloto estratificado de 1.000 canciones (979 MBID). DBpedia se consultó directamente mediante enlaces MusicBrainz o su propiedad musicBrainzArtistId. No se utilizaron QID de Wikidata como puente.",
        "| Métrica | Wikidata | DBpedia |",
        "|---|---:|---:|",
    ]
    for field, label in [
        ("mbid_consultados", "MBID consultados"),
        ("mbid_encontrados", "MBID encontrados"),
        ("mbid_ambiguos", "MBID ambiguos"),
        (
            "canciones_con_artista_vinculado_unico",
            "Canciones con artista vinculado de forma única",
        ),
        ("hechos", "Afirmaciones recuperadas (no equivalentes entre esquemas)"),
    ]:
        text.append(
            f"| {label} | {summary['wikidata'][field]} | {summary['dbpedia'][field]} |"
        )
    text += [
        "",
        f"Coinciden en {len(w & d)} canciones; {len(w - d)} solo se vinculan con Wikidata y {len(d - w)} solo con DBpedia. Quedan {1000 - len(w | d)} sin vínculo único en ambas.",
        "## Alcance y limitaciones",
        "Se unificaron representaciones URI/IRI equivalentes con caracteres Unicode; no se fusionaron recursos únicamente por parecido del nombre. La URL original queda preservada. Esta prueba evalúa DBpedia como sustituta del enriquecimiento de artistas. No cambia los descriptores TU Wien, géneros tagtraum ni la reconciliación MusicBrainz. La comparación de cobertura usa el mismo universo de canciones; el número de hechos no es una comparación de calidad porque los esquemas y propiedades difieren. Los géneros de artistas no se convierten en géneros de canciones.",
        "Las consultas, respuestas, fechas y claves quedan en data/raw/dbpedia; los resultados del piloto están en data/processed/piloto_dbpedia_*.csv. Wikidata fue la fuente seleccionada para la ampliación final.",
        "## Reproducción",
        "```bash\npython src/wikidata.py --piloto --offline\npython src/dbpedia.py --offline\npython src/comparar_fuentes.py\n```",
        "Sin --offline se consultan únicamente los lotes ausentes de la caché.",
        "## Fuentes oficiales",
        "- https://dbpedia.org/ontology/musicBrainzArtistId\n- https://www.dbpedia.org/resources/sparql/",
    ]
    (ROOT / "docs/comparacion_dbpedia_wikidata.md").write_text("\n".join(text) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
