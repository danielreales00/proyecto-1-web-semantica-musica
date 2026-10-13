"""Integra Wikidata para todo el conjunto, con métricas separadas de cobertura y profundidad."""

import csv
import hashlib
import json
from collections import Counter, defaultdict

from musica.comun.archivos_csv import escribir_csv
from musica.comun.rutas import ROOT
from wikidata import PROPIEDADES, consultar


def read(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def recuperar_evidencia_consultas(ids):
    query_by_mid = {}
    for i in range(0, len(ids), 100):
        env = consultar(ids[i : i + 100], offline=True)
        assert (
            hashlib.sha256(env["consulta"].encode()).hexdigest()
            == env["sha256_consulta"]
        )
        for mid in ids[i : i + 100]:
            query_by_mid[mid] = (env["sha256_consulta"], env["fecha_utc"])
    return query_by_mid


def aceptar_hechos(facts, links, labels):
    factset = set()
    linkmap = defaultdict(set)
    byartist = defaultdict(list)
    for r in links:
        linkmap[r["artist_mbid"]].add(r["artista_qid"])
    unique = {mid for mid, qs in linkmap.items() if len(qs) == 1}
    accepted = []
    for f in facts:
        if f["artist_mbid"] not in unique:
            continue
        assert f["estado_correspondencia"] == "unica"
        key = tuple(f[k] for k in ["artist_mbid", "artista_qid", "propiedad", "valor"])
        assert key not in factset
        factset.add(key)
        label = labels.get(f["valor"], {})
        f = {
            **f,
            "etiqueta_valor": label.get("etiqueta", ""),
            "idioma_etiqueta": label.get("idioma", ""),
            "consulta_etiqueta_sha256": label.get("consulta_sha256", ""),
        }
        accepted.append(f)
        byartist[f["artist_mbid"]].append(f)
    return accepted, byartist, linkmap, unique, factset


def verificar_hechos_originales(accepted, factset):
    # Verificación exhaustiva de cada valor contra la respuesta SPARQL cruda, una lectura por consulta.
    observed = set()
    for key in sorted({f["consulta_sha256"] for f in accepted}):
        env = json.loads((ROOT / "data/raw/wikidata" / f"{key}.json").read_text())
        for b in env["data"]["results"]["bindings"]:
            if "valor" in b:
                observed.add(
                    (
                        b["mbid"]["value"],
                        b["artista"]["value"].rsplit("/", 1)[-1],
                        b["propiedad"]["value"].rsplit("/", 1)[-1],
                        b["valor"]["value"],
                    )
                )
    assert factset <= observed


def main():
    songs = read(ROOT / "output/csv/canciones.csv")
    facts = read(ROOT / "data/processed/wikidata_hechos.csv")
    links = read(ROOT / "data/processed/wikidata_correspondencias.csv")
    labelpath = ROOT / "data/processed/wikidata_etiquetas.csv"
    labels = (
        {r["entidad_uri"]: r for r in read(labelpath)} if labelpath.exists() else {}
    )
    ids = sorted({r["artist_mbid"] for r in songs})
    query_by_mid = recuperar_evidencia_consultas(ids)
    accepted, byartist, linkmap, unique, factset = aceptar_hechos(facts, links, labels)
    verificar_hechos_originales(accepted, factset)
    out = ROOT / "output/ampliacion"
    out.mkdir(parents=True, exist_ok=True)
    linkrows = []
    new = []
    for r in songs:
        mid = r["artist_mbid"]
        values = byartist[mid]
        props = sorted({f["propiedad"] for f in values})
        non_type = [f for f in values if f["propiedad"] != "P31"]
        qids = sorted(linkmap.get(mid, set()))
        state = "unica" if len(qids) == 1 else "ambigua" if qids else "sin_coincidencia"
        srcs = (
            r["fuentes_enriquecimiento"].split("|")
            if r["fuentes_enriquecimiento"]
            else []
        )
        if non_type and "wikidata_artista" not in srcs:
            srcs.append("wikidata_artista")
        new.append(
            {
                **r,
                "fuentes_enriquecimiento": "|".join(srcs),
                "enriquecida": bool(srcs),
                "artista_qid": qids[0] if state == "unica" else "",
                "estado_wikidata": state,
                "propiedades_artista_wikidata": "|".join(props),
                "hechos_artista_wikidata": len(values),
                "hechos_artista_wikidata_sin_tipo": len(non_type),
            }
        )
    for mid in ids:
        qids = sorted(linkmap.get(mid, set()))
        state = "unica" if len(qids) == 1 else "ambigua" if qids else "sin_coincidencia"
        key, date = query_by_mid[mid]
        for qid in qids or [""]:
            linkrows.append(
                {
                    "artist_mbid": mid,
                    "artista_qid": qid,
                    "estado": state,
                    "metodo": "artist_mbid_exacto_P434",
                    "fuente_id": "wikidata",
                    "consulta_sha256": key,
                    "fecha_consulta": date,
                }
            )
    escribir_csv(out / "canciones.csv", new)
    escribir_csv(out / "wikidata_hechos.csv", accepted)
    escribir_csv(out / "wikidata_correspondencias.csv", linkrows)
    if labels:
        escribir_csv(out / "wikidata_entidades.csv", list(labels.values()))
    byprop = {
        p: {
            "artistas": len(
                {f["artist_mbid"] for f in accepted if f["propiedad"] == p}
            ),
            "canciones": sum(
                any(f["propiedad"] == p for f in byartist[s["artist_mbid"]])
                for s in songs
            ),
            "hechos": sum(f["propiedad"] == p for f in accepted),
        }
        for p in PROPIEDADES
    }
    depth = Counter(
        len(
            {
                f["propiedad"]
                for f in byartist[s["artist_mbid"]]
                if f["propiedad"] != "P31"
            }
        )
        for s in songs
    )
    before = sum(
        r["fuentes_enriquecimiento"].find("musicbrainz_artista") >= 0 for r in songs
    )
    substantive = {
        m for m, fs in byartist.items() if any(f["propiedad"] != "P31" for f in fs)
    }
    summary = {
        "canciones": len(songs),
        "artistas_consultados": len(ids),
        "artistas_con_vinculo_unico": len(unique),
        "artistas_ambiguos": sum(len(q) > 1 for q in linkmap.values()),
        "hechos_aceptados": len(accepted),
        "hechos_excluidos_por_ambiguedad": len(facts) - len(accepted),
        "canciones_con_metadatos_artista_antes": before,
        "canciones_con_metadatos_artista_wikidata_sin_tipo": sum(
            r["artist_mbid"] in substantive for r in songs
        ),
        "canciones_con_metadatos_artista_union": sum(
            r["artist_mbid"] in substantive
            or "musicbrainz_artista" in r["fuentes_enriquecimiento"].split("|")
            for r in songs
        ),
        "canciones_enriquecidas_total": sum(r["enriquecida"] for r in new),
        "por_propiedad": byprop,
        "profundidad_numero_propiedades_distintas_sin_tipo": dict(
            sorted(depth.items())
        ),
        "evidencia_verificada": True,
        "etiquetas_recuperadas": sum(bool(r["etiqueta"]) for r in labels.values()),
    }
    (ROOT / "docs/ampliacion_artistas.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
