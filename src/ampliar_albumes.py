"""Reconciliación de grupos de lanzamientos: título exacto normalizado + MBID de artista.
La extracción recorre el archivo completo y guarda TODOS los candidatos relacionados
con la entrada, incluidos los ambiguos. La reproducción usa ese subconjunto verificable.
"""

import argparse
import csv
import hashlib
import json
import tarfile
from collections import Counter, defaultdict

from diagnostico import ROOT, escribir_csv, normalizar

FOLDER = ROOT / "data/raw/musicbrainz_dump/20260912-001001"
SUBSET = FOLDER / "release-group_candidatos.jsonl"
META = FOLDER / "release-group_extraccion.json"


def read(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def keys_for(d):
    title = normalizar(d.get("title", ""))
    return {
        (c["artist"]["id"], title)
        for c in d.get("artist-credit", [])
        if isinstance(c, dict) and c.get("artist", {}).get("id") and title
    }


def estado(ids):
    return "unica" if len(ids) == 1 else "ambigua" if ids else "sin_coincidencia"


def extract(keys):
    archive = FOLDER / "release-group.tar.xz"
    source = json.loads(archive.with_suffix(".xz.json").read_text())
    assert sha(archive) == source["sha256"]
    total = retained = 0
    tmp = SUBSET.with_suffix(".tmp")
    with tarfile.open(archive, mode="r|xz") as tar, tmp.open("wb") as dest:
        for member in tar:
            if member.name != "mbdump/release-group":
                continue
            for line_no, line in enumerate(tar.extractfile(member), 1):
                d = json.loads(line)
                total += 1
                if keys_for(d) & keys:
                    row = {"linea": line_no, "data": d}
                    dest.write(
                        (
                            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                            + "\n"
                        ).encode()
                    )
                    retained += 1
                if total % 100000 == 0:
                    print(
                        f"Grupos examinados: {total:,}; candidatos: {retained:,}",
                        flush=True,
                    )
    assert total > 0
    tmp.replace(SUBSET)
    meta = {
        **source,
        "miembro": "mbdump/release-group",
        "grupos_examinados": total,
        "grupos_candidatos": retained,
        "sha256_subconjunto": sha(SUBSET),
        "sha256_entrada": sha(ROOT / "grupo_2.csv"),
        "regla_filtro": "titulo_normalizado_exacto_y_artist_mbid_en_creditos",
        "recorrido_completo": True,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return meta


def construir_tablas_grupos(accepted, groups, meta):
    albums = []
    genres = []
    credits = []
    rels = []
    for gid in sorted(accepted):
        env = groups[gid]
        d = env["data"]
        ev = {
            "fuente_id": "musicbrainz_dump",
            "url_evidencia": meta["url"],
            "archivo_sha256": meta["sha256"],
            "miembro": meta["miembro"],
            "linea_archivo": env["linea"],
            "fecha_snapshot": meta["fecha_snapshot"],
        }
        albums.append(
            {
                "grupo_lanzamiento_mbid": gid,
                "titulo": d["title"],
                "tipo_primario": d.get("primary-type") or "",
                "tipos_secundarios": "|".join(d.get("secondary-types", [])),
                "fecha_primer_lanzamiento": d.get("first-release-date") or "",
                "desambiguacion": d.get("disambiguation") or "",
                **ev,
            }
        )
        for g in d.get("genres", []):
            genres.append(
                {
                    "grupo_lanzamiento_mbid": gid,
                    "genero_mbid": g["id"],
                    "genero": g["name"],
                    "votos": g.get("count", ""),
                    **ev,
                }
            )
        for i, c in enumerate(d.get("artist-credit", []), 1):
            if isinstance(c, dict):
                credits.append(
                    {
                        "grupo_lanzamiento_mbid": gid,
                        "artist_mbid": c["artist"]["id"],
                        "nombre": c["artist"]["name"],
                        "nombre_acreditado": c.get("name", ""),
                        "orden": i,
                        "union": c.get("joinphrase", ""),
                        **ev,
                    }
                )
        for rel in d.get("relations", []):
            typ = rel.get("target-type", "")
            obj = rel.get(typ, {})
            if not isinstance(obj, dict):
                continue
            oid = obj.get("id", obj.get("resource", ""))
            if not oid:
                continue
            rels.append(
                {
                    "grupo_lanzamiento_mbid": gid,
                    "relacion": rel["type"],
                    "direccion": rel.get("direction", ""),
                    "objeto_tipo": typ,
                    "objeto_id": oid,
                    "objeto_nombre": obj.get(
                        "name", obj.get("title", obj.get("resource", ""))
                    ),
                    "atributos": "|".join(rel.get("attributes", [])),
                    **ev,
                }
            )
    return albums, genres, credits, rels


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--extraer", action="store_true", help="Recorrer nuevamente el archivo completo"
    )
    a = p.parse_args()
    songs = read(ROOT / "output/ampliacion/canciones.csv")
    keys = {(s["artist_mbid"], normalizar(s["release"])) for s in songs}
    meta = (
        extract(keys)
        if a.extraer or not META.exists()
        else json.loads(META.read_text())
    )
    assert (
        meta["recorrido_completo"]
        and meta["sha256_entrada"] == sha(ROOT / "grupo_2.csv")
        and meta["sha256_subconjunto"] == sha(SUBSET)
    )
    groups = {}
    bykey = defaultdict(set)
    for line in SUBSET.open(encoding="utf-8"):
        env = json.loads(line)
        d = env["data"]
        gid = d["id"]
        assert gid not in groups
        groups[gid] = env
        for key in keys_for(d) & keys:
            bykey[key].add(gid)
    assert len(groups) == meta["grupos_candidatos"]
    accepted = {next(iter(v)) for v in bykey.values() if len(v) == 1}
    out = ROOT / "output/ampliacion"
    matches = []
    candidates = []
    new = []
    for s in songs:
        ids = sorted(bykey[(s["artist_mbid"], normalizar(s["release"]))])
        state = estado(ids)
        gid = ids[0] if state == "unica" else ""
        row = {
            "track_id": s["track_id"],
            "artist_mbid": s["artist_mbid"],
            "release_original": s["release"],
            "grupo_lanzamiento_mbid": gid,
            "estado": state,
            "candidatos": len(ids),
            "metodo": "titulo_album_exacto_normalizado_y_mbid_artista_creditado_unico",
            "fuente_id": "musicbrainz_dump",
            "archivo_sha256": meta["sha256"],
            "subconjunto_sha256": meta["sha256_subconjunto"],
        }
        matches.append(row)
        for candidate in ids:
            candidates.append(
                {
                    "track_id": s["track_id"],
                    "grupo_lanzamiento_mbid": candidate,
                    "estado": state,
                    "linea_archivo": groups[candidate]["linea"],
                    "archivo_sha256": meta["sha256"],
                }
            )
        sources = [
            x
            for x in s["fuentes_enriquecimiento"].split("|")
            if x and x != "musicbrainz_grupo_lanzamiento"
        ]
        if gid:
            sources.append("musicbrainz_grupo_lanzamiento")
        new.append(
            {
                **s,
                "fuentes_enriquecimiento": "|".join(sources),
                "enriquecida": bool(sources),
                "grupo_lanzamiento_mbid": gid,
                "estado_grupo_lanzamiento": state,
            }
        )
    albums, genres, credits, rels = construir_tablas_grupos(accepted, groups, meta)
    escribir_csv(out / "canciones.csv", new)
    for file, rows in [
        ("grupo_lanzamiento_correspondencias", matches),
        ("grupo_lanzamiento_candidatos", candidates),
        ("grupos_lanzamientos", albums),
        ("grupo_lanzamiento_genero", genres),
        ("creditos_grupo_lanzamiento", credits),
        ("relaciones_grupo_lanzamiento", rels),
    ]:
        escribir_csv(out / (file + ".csv"), rows)
    dates = {
        r["grupo_lanzamiento_mbid"] for r in albums if r["fecha_primer_lanzamiento"]
    }
    genreids = {r["grupo_lanzamiento_mbid"] for r in genres}
    summary = {
        "canciones_evaluadas": len(songs),
        "pares_artista_album": len(keys),
        "estados": dict(Counter(r["estado"] for r in matches)),
        "grupos_examinados": meta["grupos_examinados"],
        "grupos_candidatos": len(groups),
        "grupos_aceptados": len(accepted),
        "grupos_con_genero": len(genreids),
        "canciones_con_genero_del_grupo": sum(
            s["grupo_lanzamiento_mbid"] in genreids for s in new
        ),
        "canciones_con_fecha_del_grupo": sum(
            s["grupo_lanzamiento_mbid"] in dates for s in new
        ),
        "relaciones_genero": len(genres),
        "creditos": len(credits),
        "relaciones": len(rels),
        "tipos_primarios": dict(Counter(r["tipo_primario"] for r in albums)),
        "canciones_enriquecidas_total": sum(r["enriquecida"] for r in new),
        "archivo_fuente_sha256": meta["sha256"],
        "subconjunto_sha256": meta["sha256_subconjunto"],
        "fecha_snapshot": meta["fecha_snapshot"],
        "regla": "Titulo normalizado exacto y MBID del artista suministrado presente en los creditos; grupo unico en el archivo examinado. No identifica grabaciones ni ediciones concretas.",
    }
    (ROOT / "docs/ampliacion_albumes.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
