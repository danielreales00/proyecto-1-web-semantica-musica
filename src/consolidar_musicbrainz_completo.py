"""CSV actuales del volcado completo; evidencia separada del piloto API y mapeos históricos."""

import json
from collections import Counter, defaultdict

from ampliar_albumes import read, sha
from extraer_musicbrainz_completo import OUT, load_json
from musica.comun.archivos_csv import escribir_csv
from musica.comun.rutas import ROOT


def index(name):
    return {r["columnas"][0]: r for r in load_json(name)}


def names(name):
    return {k: v["columnas"][1] for k, v in index(name).items()}


def date(c):
    if not c[0]:
        return ""
    year = int(c[0])
    parts = [("-" if year < 0 else "") + str(abs(year)).zfill(4)]
    for s in c[1:]:
        if not s:
            break
        parts.append(str(int(s)).zfill(2))
    return "-".join(parts)


def consolidar_artistas(artists, areas, types, genders, evidence):
    rows_art = []
    for r in artists.values():
        c = r["columnas"]
        area = areas.get(c[11], {}).get("columnas", ["", "", ""])
        rows_art.append(
            {
                "artist_mbid": c[1],
                "nombre": c[2],
                "tipo": types.get(c[10], ""),
                "area_mbid": area[1],
                "area_nombre": area[2],
                "fecha_inicio": date(c[4:7]),
                "fecha_fin": date(c[7:10]),
                "genero_persona": genders.get(c[12], ""),
                "desambiguacion": c[13],
                **evidence("artist", r),
            }
        )
    return rows_art


def consolidar_creditos(recordings, artists, evidence):
    bycredit = defaultdict(list)
    for r in load_json("artist_credit_name"):
        bycredit[r["columnas"][0]].append(r)
    credits = []
    for rec in recordings.values():
        for r in bycredit[rec["columnas"][3]]:
            c = r["columnas"]
            credits.append(
                {
                    "recording_mbid": rec["columnas"][1],
                    "artist_mbid": artists[c[2]]["columnas"][1],
                    "nombre_acreditado": c[3],
                    "orden": int(c[1]) + 1,
                    "union": c[4],
                    **evidence("artist_credit_name", r),
                }
            )
    return credits


def consolidar_pistas(recordings, releases, evidence):
    mediums = index("medium")
    joins = {}
    for r in load_json("track"):
        c = r["columnas"]
        rid = recordings[c[2]]["columnas"][1]
        releaseid = releases[mediums[c[3]]["columnas"][1]]["columnas"][1]
        joins.setdefault(
            (rid, releaseid),
            {
                "recording_mbid": rid,
                "release_mbid": releaseid,
                "track_mbid": c[1],
                "numero_pista": c[5],
                "medio_posicion": mediums[c[3]]["columnas"][2],
                **evidence("track", r),
            },
        )
    return joins


def consolidar_relaciones(recordings, works, artists, evidence):
    links = index("link")
    ltypes = index("link_type")
    attrtypes = index("link_attribute_type")
    attrs = defaultdict(list)
    for r in load_json("link_attribute"):
        c = r["columnas"]
        attrs[c[0]].append(attrtypes[c[1]]["columnas"][5])
    relations = []
    for table, left, right, lname, rname in [
        ("l_recording_work", recordings, works, "grabacion", "obra"),
        ("l_artist_recording", artists, recordings, "artista", "grabacion"),
        ("l_artist_work", artists, works, "artista", "obra"),
    ]:
        for r in load_json(table):
            c = r["columnas"]
            link = links[c[1]]["columnas"]
            typ = ltypes[link[1]]["columnas"]
            relations.append(
                {
                    "relacion_id": table + ":" + c[0],
                    "sujeto_tipo": lname,
                    "sujeto_mbid": left[c[2]]["columnas"][1],
                    "relacion": typ[6],
                    "tipo_relacion_mbid": typ[3],
                    "objeto_tipo": rname,
                    "objeto_mbid": right[c[3]]["columnas"][1],
                    "frase_directa": typ[8],
                    "frase_inversa": typ[9],
                    "atributos": "|".join(sorted(attrs[c[1]])),
                    "fecha_inicio": date(link[2:5]),
                    "fecha_fin": date(link[5:8]),
                    "link_id": c[1],
                    "linea_link": links[c[1]]["linea"],
                    **evidence(table, r),
                }
            )
    return relations


def consolidar_eventos(releases, areas, evidence):
    events = []
    for table, offset in [("release_country", 2), ("release_unknown_country", 1)]:
        for r in load_json(table):
            c = r["columnas"]
            area = areas[c[1]]["columnas"] if offset == 2 else ["", "", ""]
            events.append(
                {
                    "release_mbid": releases[c[0]]["columnas"][1],
                    "pais_area_mbid": area[1],
                    "pais_nombre": area[2],
                    "fecha": date(c[offset : offset + 3]),
                    **evidence(table, r),
                }
            )
    return events


def actualizar_canciones(decisions, rows_art):
    dmap = {r["track_id"]: r for r in decisions}
    songs = read(ROOT / "output/ampliacion/canciones.csv")
    new = []
    for s in songs:
        d = dmap[s["track_id"]]
        sources = [
            x
            for x in s["fuentes_enriquecimiento"].split("|")
            if x
            and x
            not in [
                "musicbrainz_grabacion_historica",
                "musicbrainz_grabacion_completo",
                "musicbrainz_artista_completo",
            ]
        ]
        if d["recording_mbid"]:
            sources.append("musicbrainz_grabacion_completo")
        # El nombre o identificador por sí solos no cuentan como nuevo enriquecimiento.
        new.append(
            {
                **s,
                "fuentes_enriquecimiento": "|".join(sources),
                "enriquecida": bool(sources),
                "recording_mbid_dump": d["recording_mbid"],
                "estado_musicbrainz_dump": d["estado"],
            }
        )
    aindex = {r["artist_mbid"]: r for r in rows_art}
    richartists = {
        m
        for m, r in aindex.items()
        if any(
            r[k]
            for k in [
                "area_mbid",
                "fecha_inicio",
                "fecha_fin",
                "genero_persona",
                "desambiguacion",
            ]
        )
    }
    for s in new:
        if s["artist_mbid"] in richartists:
            s["fuentes_enriquecimiento"] = "|".join(
                filter(
                    None, [s["fuentes_enriquecimiento"], "musicbrainz_artista_completo"]
                )
            )
            s["enriquecida"] = True
    return new, richartists


def indexar_obras_relacionadas(relations):
    byrecwork = defaultdict(set)
    for r in relations:
        if r["sujeto_tipo"] == "grabacion" and r["objeto_tipo"] == "obra":
            byrecwork[r["sujeto_mbid"]].add(r["objeto_mbid"])
    composers = {
        r["objeto_mbid"]
        for r in relations
        if r["sujeto_tipo"] == "artista"
        and r["objeto_tipo"] == "obra"
        and r["relacion"] in ["composer", "writer"]
    }
    return byrecwork, composers


def main():
    meta = json.loads((OUT / "extraccion.json").read_text())
    manifest = json.loads((OUT / "manifiesto.json").read_text())
    assert (
        meta["recorrido_completo"]
        and sha(ROOT / "grupo_2.csv") == meta["sha256_entrada"]
    )
    for name, info in manifest.items():
        assert sha(OUT / name) == info["sha256"]
    ev = {
        "fuente_id": "musicbrainz_completo",
        "url_evidencia": meta["url"],
        "archivo_sha256": meta["sha256"],
        "fecha_snapshot": meta["fecha_snapshot"],
    }

    def evidence(table, row):
        return {**ev, "tabla_fuente": table, "linea_fuente": row["linea"]}

    artists = index("artist")
    recordings = index("recording")
    releases = index("release")
    works = index("work")
    areas = index("area")
    types = names("artist_type")
    genders = names("gender")
    wtypes = names("work_type")
    rstatus = names("release_status")
    rgroups = index("release_group")
    rows_art = consolidar_artistas(artists, areas, types, genders, evidence)
    rows_rec = [
        {
            "recording_mbid": c[1],
            "titulo": c[2],
            "duracion_ms": c[4],
            "desambiguacion": c[5],
            "es_video": c[8],
            "estado_detalle": "recuperado_volcado",
            "alcance_lanzamientos": "ediciones_con_titulo_compatible_en_dataset",
            **evidence("recording", r),
        }
        for r in recordings.values()
        for c in [r["columnas"]]
    ]
    rows_release = [
        {
            "release_mbid": c[1],
            "titulo": c[2],
            "estado": rstatus.get(c[5], ""),
            "codigo_barras": c[9],
            "grupo_lanzamiento_mbid": rgroups[c[4]]["columnas"][1],
            **evidence("release", r),
        }
        for r in releases.values()
        for c in [r["columnas"]]
    ]
    rows_work = [
        {
            "work_mbid": c[1],
            "titulo": c[2],
            "tipo": wtypes.get(c[3], ""),
            "desambiguacion": c[4],
            **evidence("work", r),
        }
        for r in works.values()
        for c in [r["columnas"]]
    ]
    credits = consolidar_creditos(recordings, artists, evidence)
    joins = consolidar_pistas(recordings, releases, evidence)
    isrc = [
        {
            "recording_mbid": recordings[c[1]]["columnas"][1],
            "isrc": c[2],
            **evidence("isrc", r),
        }
        for r in load_json("isrc")
        for c in [r["columnas"]]
    ]
    relations = consolidar_relaciones(recordings, works, artists, evidence)
    events = consolidar_eventos(releases, areas, evidence)
    labels = index("label")
    labelrows = [
        {"label_mbid": c[1], "nombre": c[2], **evidence("label", r)}
        for r in labels.values()
        for c in [r["columnas"]]
    ]
    releaselabels = [
        {
            "release_mbid": releases[c[1]]["columnas"][1],
            "label_mbid": labels[c[2]]["columnas"][1] if c[2] else "",
            "numero_catalogo": c[3],
            **evidence("release_label", r),
        }
        for r in load_json("release_label")
        for c in [r["columnas"]]
    ]
    decisions = load_json("correspondencias")
    new, richartists = actualizar_canciones(decisions, rows_art)
    out = ROOT / "output/ampliacion"
    escribir_csv(out / "canciones.csv", new)
    matches = [
        {
            **d,
            "candidatos_elegibles": "|".join(d["candidatos_elegibles"]),
            "metodo": "titulo_exacto+mbid_artista+album_exacto+duracion_3s+unico_en_volcado",
            **ev,
        }
        for d in decisions
    ]
    for name, data in [
        ("artistas_masivos", rows_art),
        ("grabaciones_masivas", rows_rec),
        ("lanzamientos_masivos", rows_release),
        ("obras_masivas", rows_work),
        ("creditos_grabaciones_masivos", credits),
        ("grabacion_lanzamiento_masivo", list(joins.values())),
        ("isrc_masivos", isrc),
        ("relaciones_musicales_masivas", relations),
        ("eventos_lanzamientos_masivos", events),
        ("grabaciones_correspondencias_masivas", matches),
        ("sellos_masivos", labelrows),
        ("lanzamiento_sello_masivo", releaselabels),
    ]:
        escribir_csv(out / (name + ".csv"), data)
    byrecwork, composers = indexar_obras_relacionadas(relations)
    summary = {
        "canciones_evaluadas": len(new),
        "estados": dict(Counter(d["estado"] for d in decisions)),
        "grabaciones": len(rows_rec),
        "obras": len(rows_work),
        "lanzamientos": len(rows_release),
        "creditos": len(credits),
        "sellos": len(labelrows),
        "relaciones_lanzamiento_sello": len(releaselabels),
        "relaciones": len(relations),
        "relaciones_por_tipo": dict(Counter(r["relacion"] for r in relations)),
        "isrc": len(isrc),
        "artistas": len(rows_art),
        "canciones_con_metadatos_artista": sum(
            s["artist_mbid"] in richartists for s in new
        ),
        "canciones_con_obra": sum(
            bool(byrecwork[s["recording_mbid_dump"]]) for s in new
        ),
        "canciones_con_compositor_o_autor": sum(
            bool(byrecwork[s["recording_mbid_dump"]] & composers) for s in new
        ),
        "canciones_enriquecidas": sum(s["enriquecida"] for s in new),
        "coincidencias_mismo_mbid_piloto": sum(
            bool(s["recording_mbid"])
            and s["recording_mbid"] == s["recording_mbid_dump"]
            for s in new
        ),
        "conflictos_mbid_piloto": sum(
            bool(s["recording_mbid"])
            and bool(s["recording_mbid_dump"])
            and s["recording_mbid"] != s["recording_mbid_dump"]
            for s in new
        ),
        "fecha_snapshot": meta["fecha_snapshot"],
    }
    (ROOT / "docs/ampliacion_musicbrainz_completo.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
