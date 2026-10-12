"""Reduce las tablas auxiliares a entidades y relaciones conectadas con la entrada."""

import json

from ampliar_albumes import read, sha
from extraer_musicbrainz_completo import OUT, load_json, raw, saved, write_json
from musica.comun.rutas import ROOT


def main():
    decisions = load_json("correspondencias")
    rid = {r["recording_id"] for r in decisions if r["recording_id"]}
    recordings = [
        r for r in load_json("recording_candidatos") if r["columnas"][0] in rid
    ]
    acids = {r["columnas"][3] for r in recordings}
    tracks = [r for r in load_json("track_candidatos") if r["columnas"][2] in rid]
    mediumids = {r["columnas"][3] for r in tracks}
    mediums = [
        r for r in load_json("medium_candidatos") if r["columnas"][0] in mediumids
    ]
    relids = {r["columnas"][1] for r in mediums}
    releases = [
        r for r in load_json("release_candidatos") if r["columnas"][0] in relids
    ]
    write_json("recording", recordings)
    write_json("track", tracks)
    write_json("medium", mediums)
    write_json("release", releases)
    candidate_acids = {r["columnas"][3] for r in load_json("recording_candidatos")}
    candidate_credits = [
        raw(i, c) for i, c in saved("artist_credit_name") if c[0] in candidate_acids
    ]
    write_json("artist_credit_name_candidatos", candidate_credits)
    credits = [r for r in candidate_credits if r["columnas"][0] in acids]
    write_json("artist_credit_name", credits)
    rw = [raw(i, c) for i, c in saved("l_recording_work") if c[2] in rid]
    wid = {r["columnas"][3] for r in rw}
    ar = [raw(i, c) for i, c in saved("l_artist_recording") if c[3] in rid]
    aw = [raw(i, c) for i, c in saved("l_artist_work") if c[3] in wid]
    linkids = {r["columnas"][1] for r in rw + ar + aw}
    for name, rows in [
        ("l_recording_work", rw),
        ("l_artist_recording", ar),
        ("l_artist_work", aw),
    ]:
        write_json(name, rows)
    links = [raw(i, c) for i, c in saved("link") if c[0] in linkids]
    types = {r["columnas"][1] for r in links}
    write_json("link", links)
    write_json("link_type", [raw(i, c) for i, c in saved("link_type") if c[0] in types])
    attrs = [raw(i, c) for i, c in saved("link_attribute") if c[0] in linkids]
    attrids = {r["columnas"][1] for r in attrs}
    write_json("link_attribute", attrs)
    write_json(
        "link_attribute_type",
        [raw(i, c) for i, c in saved("link_attribute_type") if c[0] in attrids],
    )
    artistids = {r["columnas"][2] for r in ar + aw} | {
        r["columnas"][2] for r in credits
    }
    original_mids = {r["artist_mbid"] for r in read(ROOT / "grupo_2.csv")}
    candidate_artistids = {r["columnas"][2] for r in candidate_credits}
    all_artistids = artistids | candidate_artistids
    candidate_artists = [
        raw(i, c)
        for i, c in saved("artist")
        if c[0] in all_artistids or c[1] in original_mids
    ]
    write_json("artist_candidatos", candidate_artists)
    artists = [
        r
        for r in candidate_artists
        if r["columnas"][0] in artistids or r["columnas"][1] in original_mids
    ]
    write_json("artist", artists)
    areas = {
        r["columnas"][k] for r in artists for k in (11, 17, 18) if r["columnas"][k]
    }
    country = [raw(i, c) for i, c in saved("release_country") if c[0] in relids]
    areas |= {r["columnas"][1] for r in country}
    write_json("release_country", country)
    write_json(
        "release_unknown_country",
        [raw(i, c) for i, c in saved("release_unknown_country") if c[0] in relids],
    )
    write_json("area", [raw(i, c) for i, c in saved("area") if c[0] in areas])
    write_json("work", [raw(i, c) for i, c in saved("work") if c[0] in wid])
    write_json(
        "work_language", [raw(i, c) for i, c in saved("work_language") if c[0] in wid]
    )
    write_json("isrc", [raw(i, c) for i, c in saved("isrc") if c[1] in rid])
    labelrows = [raw(i, c) for i, c in saved("release_label") if c[1] in relids]
    labelids = {r["columnas"][2] for r in labelrows if r["columnas"][2]}
    write_json("release_label", labelrows)
    write_json("label", [raw(i, c) for i, c in saved("label") if c[0] in labelids])
    groupids = {r["columnas"][4] for r in releases}
    write_json(
        "release_group",
        [raw(i, c) for i, c in saved("release_group") if c[0] in groupids],
    )
    for name in [
        "artist_type",
        "gender",
        "work_type",
        "language",
        "release_status",
        "release_group_primary_type",
    ]:
        write_json(name, [raw(i, c) for i, c in saved(name)])
    manifest = {
        p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(OUT.glob("*.jsonl"))
    }
    (OUT / "manifiesto.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "grabaciones": len(rid),
                "obras": len(wid),
                "artistas": len(artists),
                "lanzamientos": len(releases),
                "relaciones": len(rw) + len(ar) + len(aw),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
