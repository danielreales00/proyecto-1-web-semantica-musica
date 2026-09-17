"""Verifica las identidades masivas nuevamente desde evidencia relacional conservada."""

import json
from collections import defaultdict

from ampliar_albumes import read
from diagnostico import ROOT, normalizar
from extraer_musicbrainz_completo import load_json


def validar_entidades(csv, check):
    artists = {r["artist_mbid"] for r in read(csv / "artistas_masivos.csv")}
    recs = {r["recording_mbid"] for r in read(csv / "grabaciones_masivas.csv")}
    works = {r["work_mbid"] for r in read(csv / "obras_masivas.csv")}
    releases = {r["release_mbid"] for r in read(csv / "lanzamientos_masivos.csv")}
    for r in read(csv / "creditos_grabaciones_masivos.csv"):
        check(
            r["recording_mbid"] in recs and r["artist_mbid"] in artists,
            "Crédito masivo con entidades existentes",
        )
    for r in read(csv / "grabacion_lanzamiento_masivo.csv"):
        check(
            r["recording_mbid"] in recs and r["release_mbid"] in releases,
            "Enlace grabación-edición con entidades existentes",
        )
    labels = {r["label_mbid"] for r in read(csv / "sellos_masivos.csv")}
    for r in read(csv / "lanzamiento_sello_masivo.csv"):
        check(
            r["release_mbid"] in releases
            and (not r["label_mbid"] or r["label_mbid"] in labels),
            "Edición y sello con entidades existentes",
        )
    for r in read(csv / "relaciones_musicales_masivas.csv"):
        sets = {"artista": artists, "grabacion": recs, "obra": works}
        check(
            r["sujeto_mbid"] in sets[r["sujeto_tipo"]]
            and r["objeto_mbid"] in sets[r["objeto_tipo"]],
            "Relación tipada con sujeto y objeto exportados",
        )
    return recs


def cargar_evidencia_identidad():
    art = {r["columnas"][0]: r["columnas"][1] for r in load_json("artist_candidatos")}
    credit = defaultdict(set)
    for r in load_json("artist_credit_name_candidatos"):
        credit[r["columnas"][0]].add(art[r["columnas"][2]])
    # Candidate credit IDs include rejected/ambiguous recordings too. For those, source scan
    # decisions are retained; acceptance validation exhaustively recomputes accepted IDs.
    records = {
        r["columnas"][0]: r["columnas"] for r in load_json("recording_candidatos")
    }
    rel = {r["columnas"][0]: r["columnas"] for r in load_json("release_candidatos")}
    medium = {
        r["columnas"][0]: r["columnas"][1] for r in load_json("medium_candidatos")
    }
    albums = defaultdict(set)
    for r in load_json("track_candidatos"):
        albums[r["columnas"][2]].add(normalizar(rel[medium[r["columnas"][3]]][2]))
    return credit, records, albums


def recalcular_candidatos(songs, records, credit, albums):
    # Recalcular elegibilidad desde las tablas fuente y las cadenas originales.
    expected = defaultdict(set)
    songkeys = defaultdict(list)
    for s in songs:
        songkeys[
            (s["artist_mbid"], normalizar(s["title"]), normalizar(s["release"]))
        ].append(s)
    for c in records.values():
        for mid in credit[c[3]]:
            for album in albums[c[0]]:
                for s in songkeys.get((mid, normalizar(c[2]), album), []):
                    if c[4] and abs(float(s["duration"]) - int(c[4]) / 1000) <= 3:
                        expected[s["track_id"]].add(c[1])
    return expected


def validar_decisiones(bytid, expected, records, credit, albums, check):
    decisions = load_json("correspondencias")
    for d in decisions:
        s = bytid[d["track_id"]]
        check(
            expected[d["track_id"]] == set(d["candidatos_elegibles"]),
            "Candidatos recalculados desde tablas fuente",
        )
        check(
            s["recording_mbid_dump"] == d["recording_mbid"],
            "Decisión exportada coincide con evidencia",
        )
        if d["estado"] != "aceptada":
            check(not d["recording_mbid"], "Ambigüedad/ausencia no origina identidad")
            continue
        c = records[d["recording_id"]]
        check(
            normalizar(s["title"]) == normalizar(c[2])
            and s["artist_mbid"] in credit[c[3]]
            and abs(float(s["duration"]) - int(c[4]) / 1000) <= 3
            and normalizar(s["release"]) in albums[c[0]],
            "Cuatro criterios de identidad verificados",
        )
        check(
            d["candidatos_elegibles"] == [c[1]],
            "Unicidad de candidato en extracción completa",
        )
    return decisions


def validar_artistas_y_grupos(csv, songs, check):
    # Cada hecho aceptado debe tener un enlace único. Las etiquetas no prueban identidad.
    mappings = defaultdict(set)
    for r in read(csv / "wikidata_correspondencias.csv"):
        if r["artista_qid"]:
            mappings[r["artist_mbid"]].add(r["artista_qid"])
    check(
        all(
            mappings[r["artist_mbid"]] == {r["artista_qid"]}
            for r in read(csv / "wikidata_hechos.csv")
        ),
        "Hechos Wikidata solo para identificaciones únicas",
    )
    catalog = {r["artist_mbid"] for r in read(csv / "artistas.csv")}
    check(
        all(
            r["artist_mbid"] in catalog
            for r in read(csv / "creditos_grupo_lanzamiento.csv")
        ),
        "Todos los artistas acreditados en grupos tienen entidad en el catálogo",
    )
    gids = {r["grupo_lanzamiento_mbid"] for r in read(csv / "grupos_lanzamientos.csv")}
    check(
        all(
            not s["grupo_lanzamiento_mbid"] or s["grupo_lanzamiento_mbid"] in gids
            for s in songs
        ),
        "Grupos de lanzamientos con entidad exportada",
    )
    check(
        all(s["enriquecida"] == str(bool(s["fuentes_enriquecimiento"])) for s in songs),
        "Bandera de enriquecimiento consistente",
    )


def validar_acousticbrainz(csv, bytid, recs, check):
    ab = {r["recording_mbid"]: r for r in read(csv / "acousticbrainz_masivo.csv")}
    ac = read(csv / "acousticbrainz_correspondencias_masivas.csv")
    abmeta = json.loads((ROOT / "docs/ampliacion_acousticbrainz.json").read_text())
    conflicts = set(abmeta["mbid_con_conflicto_analisis_cero"])
    missing = set(abmeta["mbid_sin_analisis_cero"])
    check(
        len(ac) == 100000 and len({r["track_id"] for r in ac}) == 100000,
        "Un estado AcousticBrainz por canción",
    )
    check(
        set(ab) <= recs,
        "Descriptores AcousticBrainz solo para grabaciones reconciliadas",
    )
    check(
        all(
            r["submission_offset"] == "0" and int(r["analisis_disponibles"]) >= 1
            for r in ab.values()
        ),
        "Un mismo análisis predeterminado por grabación",
    )
    for row in ac:
        s = bytid[row["track_id"]]
        mid = s["recording_mbid_dump"]
        expected_state = (
            "disponible"
            if mid in ab
            else "conflicto_analisis_cero"
            if mid in conflicts
            else "sin_analisis_cero"
            if mid in missing
            else "sin_datos_en_volcado"
            if mid
            else "sin_grabacion_reconciliada"
        )
        check(
            row["recording_mbid"] == mid
            and row["estado"] == s["estado_acousticbrainz_dump"] == expected_state,
            "Estado AcousticBrainz y MBID consistentes",
        )
        check(
            ("acousticbrainz_dump" in s["fuentes_enriquecimiento"].split("|"))
            == (mid in ab),
            "Cobertura AcousticBrainz requiere valores publicados",
        )


def main():
    checks = []

    def check(condition, text):
        assert condition, text
        checks.append(text)

    csv = ROOT / "output/csv"
    songs = read(csv / "canciones.csv")
    bytid = {s["track_id"]: s for s in songs}
    original = read(ROOT / "grupo_2.csv")
    check(len(songs) == len(bytid) == 100000, "100000 canciones sin duplicados")
    check(
        all(all(s[k] == o[k] for k in o) for s, o in zip(songs, original)),
        "Campos originales y orden intactos",
    )
    recs = validar_entidades(csv, check)
    credit, records, albums = cargar_evidencia_identidad()
    expected = recalcular_candidatos(songs, records, credit, albums)
    decisions = validar_decisiones(bytid, expected, records, credit, albums, check)
    validar_artistas_y_grupos(csv, songs, check)
    validar_acousticbrainz(csv, bytid, recs, check)
    summary = {
        "estado": "correcto",
        "comprobaciones": len(checks),
        "canciones": len(songs),
        "identidades_aceptadas_verificadas": sum(
            d["estado"] == "aceptada" for d in decisions
        ),
        "criterios": "titulo, MBID artista acreditado, album, diferencia duracion <=3 s y candidato unico",
        "limitacion": "Verifica consistencia con la fuente y reglas; no estima precision contra un conjunto de verdad independiente.",
    }
    (ROOT / "docs/validacion_ampliacion.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
