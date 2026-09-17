"""Enriquecimiento de artistas por P434; conserva valores múltiples y ambigüedad."""

import argparse
import csv
import hashlib
import json
import os
import time
from collections import defaultdict

from diagnostico import ROOT, escribir_csv

PROPIEDADES = {
    "P31": "instancia_de",
    "P27": "ciudadania",
    "P495": "pais_origen",
    "P136": "genero_del_artista",
    "P264": "sello_discografico",
    "P571": "fecha_fundacion",
    "P569": "fecha_nacimiento",
    "P740": "lugar_formacion",
}


def consultar(ids, offline=False):
    values = " ".join(json.dumps(i) for i in ids)
    props = " ".join("wdt:" + p for p in PROPIEDADES)
    query = f"SELECT DISTINCT ?mbid ?artista ?propiedad ?valor WHERE {{ VALUES ?mbid {{ {values} }} ?artista wdt:P434 ?mbid . OPTIONAL {{ VALUES ?propiedad {{ {props} }} ?artista ?propiedad ?valor . }} }}"
    key = hashlib.sha256(query.encode()).hexdigest()
    path = ROOT / "data/raw/wikidata" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text())
    if offline:
        raise FileNotFoundError(path)
    # Una consulta por lote; ante errores temporales, detener y conservar caché.
    from musicbrainz import Cliente

    client = Cliente()
    client.session.headers["User-Agent"] = os.environ.get(
        "WIKIDATA_USER_AGENT", "ProyectoEtapa1MISIS/1.1 (academic research)"
    )
    result_http = client.get(
        "https://query.wikidata.org/sparql", {"query": query, "format": "json"}
    )
    if result_http["status"] != 200:
        raise RuntimeError(f"Wikidata HTTP {result_http['status']}")
    data = result_http["data"]
    if "results" not in data or "bindings" not in data["results"]:
        raise RuntimeError("Respuesta SPARQL inválida")
    result = {
        "consulta": query,
        "endpoint": "https://query.wikidata.org/sparql",
        "fecha_utc": result_http["fecha_utc"],
        "sha256_consulta": key,
        "data": data,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False))
    tmp.replace(path)
    time.sleep(2)
    return result


def ejecutar(piloto=False, offline=False):
    base = "piloto_1000.csv" if piloto else "base_normalizada.csv"
    songs = list(csv.DictReader((ROOT / "data/processed" / base).open()))
    ids = sorted({r["artist_mbid"] for r in songs})
    links = defaultdict(set)
    facts = {}
    # Piloto usa lotes propios; el procesamiento completo es independiente y reproducible.
    for i in range(0, len(ids), 100):
        response = consultar(ids[i : i + 100], offline)
        for binding in response["data"]["results"]["bindings"]:
            b = {k: v["value"] for k, v in binding.items()}
            mbid = b["mbid"]
            qid = b["artista"].rsplit("/", 1)[-1]
            links[mbid].add(qid)
            if "propiedad" not in b:
                continue
            prop = b["propiedad"].rsplit("/", 1)[-1]
            value = b["valor"]
            key = (mbid, qid, prop, value)
            facts[key] = {
                "artist_mbid": mbid,
                "artista_qid": qid,
                "propiedad": prop,
                "relacion": PROPIEDADES[prop],
                "valor": value,
                "tipo_valor": binding["valor"]["type"],
                "datatype": binding["valor"].get("datatype", ""),
                "fuente_id": "wikidata",
                "metodo": "artist_mbid_exacto_P434",
                "url_entidad": f"https://www.wikidata.org/wiki/{qid}",
                "consulta_sha256": response["sha256_consulta"],
                "fecha_consulta": response["fecha_utc"],
            }
        print(
            f"Wikidata {min(i + 100, len(ids))}/{len(ids)} MBID; {len(links)} vinculados; {len(facts)} hechos",
            flush=True,
        )
    for f in facts.values():
        f["estado_correspondencia"] = (
            "unica" if len(links[f["artist_mbid"]]) == 1 else "ambigua"
        )
    substantive = {
        f["artist_mbid"]
        for f in facts.values()
        if f["propiedad"] != "P31" and f["estado_correspondencia"] == "unica"
    }
    song_covered = sum(len(links.get(s["artist_mbid"], set())) == 1 for s in songs)
    summary = {
        "mbid_consultados": len(ids),
        "mbid_encontrados": len(links),
        "mbid_ambiguos": sum(len(v) > 1 for v in links.values()),
        "canciones_con_artista_vinculado_unico": song_covered,
        "hechos": len(facts),
        "canciones_con_datos_mas_alla_del_tipo": sum(
            s["artist_mbid"] in substantive for s in songs
        ),
        "alcance": "Propiedades de la entidad del MBID suministrado; no valida el crédito completo ni se propagan géneros del artista a la canción.",
    }
    prefix = "piloto_" if piloto else ""
    (ROOT / "docs" / f"{prefix}wikidata.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    escribir_csv(
        ROOT / "data/processed" / f"{prefix}wikidata_hechos.csv", list(facts.values())
    )
    escribir_csv(
        ROOT / "data/processed" / f"{prefix}wikidata_correspondencias.csv",
        [
            {
                "artist_mbid": mbid,
                "artista_qid": qid,
                "estado": "unica" if len(qids) == 1 else "ambigua",
                "fuente_id": "wikidata",
                "metodo": "artist_mbid_exacto_P434",
            }
            for mbid, qids in sorted(links.items())
            for qid in sorted(qids)
        ],
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--piloto", action="store_true")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    ejecutar(args.piloto, args.offline)
