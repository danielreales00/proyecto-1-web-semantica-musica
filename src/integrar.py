"""Exportación relacional con procedencia y métricas calculadas sobre datos reales."""

import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from descargar import FUENTES
from musica.comun.archivos_csv import escribir_csv
from musica.comun.rutas import ROOT

OUT = ROOT / "output/csv"


def leer(p):
    return list(csv.DictReader(Path(p).open(encoding="utf-8", newline="")))


def guardar(name, rows, fields):
    escribir_csv(OUT / name, rows, fields)


def integrar_canciones(base, genres, acoustic, mb, mba, ab):
    gmap = defaultdict(list)
    for g in genres:
        gmap[g["track_id"]].append(g)
    acids = {r["track_id"] for r in acoustic}
    mbmap = {r["track_id"]: r for r in mb}
    mbartists = {
        r["artist_mbid_suministrado"]: r for r in mba if r["status_http"] == "200"
    }
    abids = {x["track_id"] for x in ab if x["status"] == 200 and not x.get("sin_datos")}
    songs = []
    artist_names = defaultdict(set)
    for r in base:
        tid = r["track_id"]
        mid = r["artist_mbid"]
        sources = []
        artist_names[mid].add(r["artist_name"])
        if tid in acids:
            sources.append("jmir")
        if tid in gmap:
            sources.append("tagtraum")
        if mid in mbartists:
            sources.append("musicbrainz_artista")
        matched = mbmap.get(tid, {})
        if matched.get("recording_mbid"):
            sources.append("musicbrainz_grabacion")
        if tid in abids:
            sources.append("acousticbrainz")
        songs.append(
            {
                **r,
                "fuente_base": "grupo_2",
                "fuentes_enriquecimiento": "|".join(sources),
                "enriquecida": bool(sources),
                "genero_mayoritario": next(
                    (x["genero"] for x in gmap[tid] if x["papel"] == "mayoritario"), ""
                ),
                "genero_minoritario": next(
                    (x["genero"] for x in gmap[tid] if x["papel"] == "minoritario"), ""
                ),
                "tiene_descriptores_jmir": tid in acids,
                "recording_mbid": matched.get("recording_mbid", ""),
                "estado_musicbrainz_grabacion": matched.get("estado", "no_consultada"),
                "estado_detalle_musicbrainz": matched.get(
                    "estado_detalle", "no_consultada"
                ),
                "estado_acousticbrainz": matched.get(
                    "estado_acousticbrainz", "no_consultada"
                ),
            }
        )
    return songs, artist_names, mbartists


def agregar_relaciones_grabacion(d, rid, evidence, works, relations):
    for rel in d.get("relations", []):
        target = rel.get("target-type", "")
        obj = rel.get(target, {})
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        relations.append(
            {
                "sujeto_tipo": "grabacion",
                "sujeto_id": rid,
                "relacion": rel["type"],
                "direccion": rel.get("direction", ""),
                "objeto_tipo": target,
                "objeto_id": obj["id"],
                "objeto_nombre": obj.get("name", obj.get("title", "")),
                "atributos": "|".join(rel.get("attributes", [])),
                **evidence,
            }
        )
        if target == "work":
            works[obj["id"]] = {
                "work_mbid": obj["id"],
                "titulo": obj.get("title", ""),
                "tipo": obj.get("type", ""),
                "idioma": obj.get("language", ""),
                **evidence,
            }
            for wr in obj.get("relations", []):
                wt = wr.get("target-type", "")
                wo = wr.get(wt, {})
                if isinstance(wo, dict) and wo.get("id"):
                    relations.append(
                        {
                            "sujeto_tipo": "obra",
                            "sujeto_id": obj["id"],
                            "relacion": wr["type"],
                            "direccion": wr.get("direction", ""),
                            "objeto_tipo": wt,
                            "objeto_id": wo["id"],
                            "objeto_nombre": wo.get("name", wo.get("title", "")),
                            "atributos": "|".join(wr.get("attributes", [])),
                            **evidence,
                        }
                    )


def integrar_detalles_grabaciones(details):
    recordings = {}
    releases = {}
    works = {}
    rec_release = set()
    relations = []
    credits = []
    isrcs = []
    for envelope in details:
        if envelope["status"] != 200:
            continue
        d = envelope["data"]
        rid = d["id"]
        url = envelope["url"]
        evidence = {
            "fuente_id": "musicbrainz",
            "url_evidencia": url,
            "fecha_consulta": envelope["fecha_utc"],
        }
        recordings[rid] = {
            "recording_mbid": rid,
            "titulo": d["title"],
            "duracion_ms": d.get("length", ""),
            "fecha_primer_lanzamiento": d.get("first-release-date", ""),
            "lista_lanzamientos_completa": "no_verificada",
            "estado_detalle": "recuperado",
            **evidence,
        }
        for code in d.get("isrcs", []):
            isrcs.append({"recording_mbid": rid, "isrc": code, **evidence})
        for pos, credit in enumerate(d.get("artist-credit", []), 1):
            if not isinstance(credit, dict):
                continue
            a = credit["artist"]
            credits.append(
                {
                    "recording_mbid": rid,
                    "artist_mbid": a["id"],
                    "nombre": a["name"],
                    "nombre_acreditado": credit.get("name", ""),
                    "orden": pos,
                    "union": credit.get("joinphrase", ""),
                    **evidence,
                }
            )
        for rel in d.get("releases", []):
            reid = rel["id"]
            releases[reid] = {
                "release_mbid": reid,
                "titulo": rel.get("title", ""),
                "fecha": rel.get("date", ""),
                "pais": rel.get("country", ""),
                "estado": rel.get("status", ""),
                "codigo_barras": rel.get("barcode", ""),
                **evidence,
            }
            rec_release.add((rid, reid))
        agregar_relaciones_grabacion(d, rid, evidence, works, relations)
    return recordings, releases, works, rec_release, relations, credits, isrcs


def completar_obras_referenciadas(relations, works):
    for rel in relations:
        if rel["objeto_tipo"] == "work" and rel["objeto_id"] not in works:
            works[rel["objeto_id"]] = {
                "work_mbid": rel["objeto_id"],
                "titulo": rel["objeto_nombre"],
                "tipo": "",
                "idioma": "",
                "fuente_id": rel["fuente_id"],
                "url_evidencia": rel["url_evidencia"],
                "fecha_consulta": rel["fecha_consulta"],
            }


def completar_grabaciones_sin_detalle(recordings):
    # Las correspondencias aceptadas requieren una entidad incluso si su detalle falta.
    # Se toma el título y duración del candidato original, nunca se inventan metadatos.
    partial = json.loads(
        (ROOT / "output/piloto_musicbrainz_parcial/resultados_cache.json").read_text()
    )
    for item in partial:
        rid = item["recording_mbid"]
        if not rid or rid in recordings:
            continue
        env = json.loads(
            (
                ROOT
                / "data/raw/api"
                / f"{hashlib.sha256(item['url_evidencia'].encode()).hexdigest()}.json"
            ).read_text()
        )
        rec = next(r for r in env["data"]["recordings"] if r["id"] == rid)
        recordings[rid] = {
            "recording_mbid": rid,
            "titulo": rec.get("title", ""),
            "duracion_ms": rec.get("length", ""),
            "fecha_primer_lanzamiento": rec.get("first-release-date", ""),
            "lista_lanzamientos_completa": "no_verificada",
            "estado_detalle": "pendiente_consulta",
            "fuente_id": "musicbrainz",
            "url_evidencia": item["url_evidencia"],
            "fecha_consulta": item["fecha_consulta"],
        }


def agregar_artistas_participantes(artist_rows, credits, relations):
    # Completar el catálogo con participantes identificados en créditos o relaciones.
    artist_index = {r["artist_mbid"]: r for r in artist_rows}
    refs = [(c["artist_mbid"], c["nombre"], c["url_evidencia"]) for c in credits]
    refs += [
        (r["objeto_id"], r["objeto_nombre"], r["url_evidencia"])
        for r in relations
        if r["objeto_tipo"] == "artist"
    ]
    for mid, name, url in refs:
        if mid not in artist_index:
            artist_index[mid] = {
                "artist_mbid": mid,
                "nombres_en_dataset": "",
                "nombre_musicbrainz": name,
                "tipo_musicbrainz": "",
                "pais_musicbrainz": "",
                "fuentes": "musicbrainz",
                "estado_credito": "participante_recuperado_en_relacion",
                "url_musicbrainz": url,
            }
    artist_rows = list(artist_index.values())
    return artist_rows


def integrar_acousticbrainz(ab):
    abrows = []
    for env in ab:
        if env["status"] != 200 or env.get("sin_datos"):
            continue
        d = env["data"]
        rh = d.get("rhythm", {})
        to = d.get("tonal", {})
        lo = d.get("lowlevel", {})
        abrows.append(
            {
                "track_id": env["track_id"],
                "recording_mbid": env["recording_mbid"],
                "bpm": rh.get("bpm", ""),
                "tonalidad": to.get("key_key", ""),
                "escala": to.get("key_scale", ""),
                "fuerza_tonalidad": to.get("key_strength", ""),
                "danceability": rh.get("danceability", ""),
                "average_loudness": lo.get("average_loudness", ""),
                "fuente_id": "acousticbrainz",
                "metodo": "recording_mbid_reconciliado",
                "url_evidencia": env["url"],
                "fecha_consulta": env["fecha_utc"],
            }
        )
    return abrows


def main():
    base = leer(ROOT / "data/processed/base_normalizada.csv")
    genres = leer(OUT / "cancion_genero.csv")
    acoustic = leer(OUT / "descriptores_acusticos.csv")
    mb = leer(ROOT / "data/processed/musicbrainz_correspondencias.csv")
    mba = leer(ROOT / "data/processed/musicbrainz_artistas.csv")
    details = json.loads(
        (ROOT / "data/processed/musicbrainz_detalles.json").read_text()
    )
    ab = json.loads((ROOT / "data/processed/acousticbrainz.json").read_text())
    songs, artist_names, mbartists = integrar_canciones(
        base, genres, acoustic, mb, mba, ab
    )
    escribir_csv(OUT / "canciones.csv", songs)
    artist_rows = []
    for mid, names in sorted(artist_names.items()):
        a = mbartists.get(mid, {})
        artist_rows.append(
            {
                "artist_mbid": mid,
                "nombres_en_dataset": "|".join(sorted(names)),
                "nombre_musicbrainz": a.get("nombre", ""),
                "tipo_musicbrainz": a.get("tipo", ""),
                "pais_musicbrainz": a.get("pais", ""),
                "fuentes": "grupo_2" + ("|musicbrainz" if a else ""),
                "estado_credito": "referencia_suministrada_no_valida_credito_completo",
                "url_musicbrainz": a.get("url_evidencia", ""),
            }
        )
    escribir_csv(OUT / "artistas.csv", artist_rows)
    for f in [
        "musicbrainz_correspondencias.csv",
        "musicbrainz_artistas.csv",
        "musicbrainz_candidatos.csv",
    ]:
        shutil.copyfile(ROOT / "data/processed" / f, OUT / f)
    recordings, releases, works, rec_release, relations, credits, isrcs = (
        integrar_detalles_grabaciones(details)
    )
    completar_obras_referenciadas(relations, works)
    completar_grabaciones_sin_detalle(recordings)
    artist_rows = agregar_artistas_participantes(artist_rows, credits, relations)
    escribir_csv(OUT / "artistas.csv", artist_rows)
    abrows = integrar_acousticbrainz(ab)
    ev = ["fuente_id", "url_evidencia", "fecha_consulta"]
    guardar(
        "grabaciones.csv",
        list(recordings.values()),
        [
            "recording_mbid",
            "titulo",
            "duracion_ms",
            "fecha_primer_lanzamiento",
            "lista_lanzamientos_completa",
            "estado_detalle",
        ]
        + ev,
    )
    guardar(
        "lanzamientos.csv",
        list(releases.values()),
        ["release_mbid", "titulo", "fecha", "pais", "estado", "codigo_barras"] + ev,
    )
    guardar(
        "obras.csv",
        list(works.values()),
        ["work_mbid", "titulo", "tipo", "idioma"] + ev,
    )
    guardar(
        "grabacion_lanzamiento.csv",
        [
            {
                "recording_mbid": r,
                "release_mbid": release_mbid,
                "fuente_id": "musicbrainz",
                "url_evidencia": recordings[r]["url_evidencia"],
            }
            for r, release_mbid in sorted(rec_release)
        ],
        ["recording_mbid", "release_mbid", "fuente_id", "url_evidencia"],
    )
    guardar(
        "creditos_grabacion.csv",
        credits,
        [
            "recording_mbid",
            "artist_mbid",
            "nombre",
            "nombre_acreditado",
            "orden",
            "union",
        ]
        + ev,
    )
    guardar(
        "relaciones_musicbrainz.csv",
        relations,
        [
            "sujeto_tipo",
            "sujeto_id",
            "relacion",
            "direccion",
            "objeto_tipo",
            "objeto_id",
            "objeto_nombre",
            "atributos",
        ]
        + ev,
    )
    guardar("isrc.csv", isrcs, ["recording_mbid", "isrc"] + ev)
    guardar(
        "acousticbrainz.csv",
        abrows,
        [
            "track_id",
            "recording_mbid",
            "bpm",
            "tonalidad",
            "escala",
            "fuerza_tonalidad",
            "danceability",
            "average_loudness",
            "fuente_id",
            "metodo",
            "url_evidencia",
            "fecha_consulta",
        ],
    )
    sources = [
        {
            "fuente_id": "grupo_2",
            "url": "",
            "documentacion": "Proyecto___Etapa_1__MISIS_.pdf",
            "archivo": "grupo_2.csv",
            "sha256": hashlib.file_digest(
                (ROOT / "grupo_2.csv").open("rb"), "sha256"
            ).hexdigest(),
            "licencia": "Dataset suministrado por el curso",
            "fecha_descarga_utc": "",
        }
    ]
    for sid, source in FUENTES.items():
        manifest = json.loads(
            (ROOT / "data/raw" / (source["archivo"] + ".json")).read_text()
        )
        sources.append({k: manifest.get(k, "") for k in sources[0]})
    for sid, url, license_ in [
        (
            "musicbrainz",
            "https://musicbrainz.org/doc/MusicBrainz_API",
            "CC0 datos básicos; CC BY-NC-SA 3.0 datos suplementarios",
        ),
        ("acousticbrainz", "https://acousticbrainz.org/", "CC0"),
    ]:
        sources.append(
            {
                "fuente_id": sid,
                "url": url,
                "documentacion": url,
                "archivo": "data/raw/api/",
                "sha256": "ver manifiesto_archivos.json",
                "licencia": license_,
                "fecha_descarga_utc": "por respuesta en cache",
            }
        )
    escribir_csv(OUT / "fuentes.csv", sources)
    counts = Counter()
    for s in songs:
        for src in s["fuentes_enriquecimiento"].split("|"):
            if src:
                counts[src] += 1
    summary = {
        "canciones_originales": len(base),
        "canciones_conservadas": len(songs),
        "canciones_enriquecidas": sum(s["enriquecida"] for s in songs),
        "canciones_sin_enriquecer": sum(not s["enriquecida"] for s in songs),
        "cobertura_por_fuente": dict(counts),
        "artistas_referenciados": len(artist_rows),
        "generos_distintos_tagtraum": len({g["genero"] for g in genres}),
        "relaciones_genero": len(genres),
        "submuestra_api": len(mb),
        "estados_reconciliacion": dict(Counter(x["estado"] for x in mb)),
        "nombres_artista_validados_submuestra": sum(
            x["nombre_artista_validado"] == "True" for x in mb
        ),
        "grabaciones_musicbrainz": len(recordings),
        "lanzamientos_musicbrainz": len(releases),
        "obras_musicbrainz": len(works),
        "relaciones_musicbrainz": len(relations),
        "acousticbrainz_registros": len(abrows),
        "acousticbrainz_estados": dict(
            Counter(
                "sin_datos_en_lote_200" if x.get("sin_datos") else str(x["status"])
                for x in ab
            )
        ),
    }
    summary["grabaciones_con_detalle"] = sum(
        r["estado_detalle"] == "recuperado" for r in recordings.values()
    )
    summary["grabaciones_detalle_pendiente"] = sum(
        r["estado_detalle"] == "pendiente_consulta" for r in recordings.values()
    )
    (ROOT / "docs/resultados.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
