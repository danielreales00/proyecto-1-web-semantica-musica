"""Piloto DBpedia: enlaces exactos a MusicBrainz, sin depender de Wikidata."""

import argparse
import csv
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import unquote

import requests

from musica.comun.archivos_csv import escribir_csv
from musica.comun.rutas import ROOT

D = "http://dbpedia.org/ontology/"
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PROPS = {
    TYPE: "tipo",
    **{
        D + k: v
        for k, v in {
            "nationality": "nacionalidad",
            "country": "pais",
            "genre": "genero_artista",
            "recordLabel": "sello",
            "foundingDate": "fecha_fundacion",
            "foundingYear": "anio_fundacion",
            "birthDate": "fecha_nacimiento",
            "hometown": "lugar_origen",
        }.items()
    },
}


def normalizar_uri(uri):
    # URI/IRI equivalentes: decodificar Unicode y caracteres no reservados.
    # No decodificar separadores reservados como %2F, pues cambia la identidad.
    def decode(match):
        raw = match.group(0)
        try:
            value = unquote(raw, errors="strict")
        except UnicodeDecodeError:
            return raw
        return (
            value
            if all(ord(c) > 127 or c.isalnum() or c in "-._~" for c in value)
            else raw
        )

    return re.sub(r"(?:%[0-9A-Fa-f]{2})+", decode, uri)


def consultar(ids, offline=False):
    pairs = " ".join(
        f"({json.dumps(mid)} <http://musicbrainz.org/artist/{mid}>)" for mid in ids
    )
    props = " ".join(f"<{p}>" for p in PROPS)
    query = f'''SELECT DISTINCT ?mbid ?recurso ?artista ?propiedad ?valor WHERE {{
 VALUES (?mbid ?musicbrainz) {{ {pairs} }}
 {{ ?recurso <http://www.w3.org/2002/07/owl#sameAs> ?musicbrainz }} UNION
 {{ ?recurso <http://dbpedia.org/ontology/musicBrainzArtistId> ?mbid }}
 OPTIONAL {{ ?recurso <http://dbpedia.org/ontology/wikiPageRedirects> ?destino }}
 BIND(COALESCE(?destino,?recurso) AS ?artista)
 OPTIONAL {{ VALUES ?propiedad {{ {props} }} ?artista ?propiedad ?valor .
 FILTER(?propiedad != <{TYPE}> || STRSTARTS(STR(?valor),"{D}")) }}
}}'''
    key = hashlib.sha256(query.encode()).hexdigest()
    path = ROOT / "data/raw/dbpedia" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text())
    if offline:
        raise FileNotFoundError(path)
    for attempt in range(2):
        r = requests.get(
            "https://dbpedia.org/sparql",
            params={"query": query, "format": "application/sparql-results+json"},
            headers={"User-Agent": "ProyectoEtapa1MISIS/1.0 academic research"},
            timeout=(10, 30),
        )
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", 30)))
            continue
        r.raise_for_status()
        if any(
            k.lower() == "x-sql-state" and v != "00000" for k, v in r.headers.items()
        ):
            raise RuntimeError(f"Resultado parcial DBpedia: {dict(r.headers)}")
        result = {
            "endpoint": "https://dbpedia.org/sparql",
            "consulta": query,
            "sha256_consulta": key,
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "status": r.status_code,
            "data": r.json(),
        }
        path.write_text(json.dumps(result, ensure_ascii=False))
        return result
    raise RuntimeError("DBpedia limitó las consultas; reanudar después.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    songs = list(csv.DictReader((ROOT / "data/processed/piloto_1000.csv").open()))
    ids = sorted({r["artist_mbid"] for r in songs})
    links = defaultdict(set)
    facts = {}
    evidence = {}
    started = time.monotonic()
    for i in range(0, len(ids), 40):
        env = consultar(ids[i : i + 40], args.offline)
        for b in env["data"]["results"]["bindings"]:
            val = {k: v["value"] for k, v in b.items()}
            mid = val["mbid"]
            uri = normalizar_uri(val["artista"])
            links[mid].add(uri)
            evidence[(mid, uri)] = {
                "consulta_sha256": env["sha256_consulta"],
                "fecha_consulta": env["fecha_utc"],
            }
            if "propiedad" not in val:
                continue
            prop = val["propiedad"]
            value = val["valor"]
            facts[(mid, uri, prop, value)] = {
                "artist_mbid": mid,
                "artista_uri": uri,
                "propiedad": prop,
                "relacion": PROPS[prop],
                "valor": value,
                "tipo_valor": b["valor"]["type"],
                "datatype": b["valor"].get("datatype", ""),
                "fuente_id": "dbpedia",
                "metodo": "enlace_exacto_MusicBrainz",
                "recurso_original": val["recurso"],
                "artista_uri_fuente": val["artista"],
                **evidence[(mid, uri)],
            }
        print(
            f"{min(i + 40, len(ids))}/{len(ids)} MBID; {len(links)} encontrados; {len(facts)} hechos",
            flush=True,
        )
    for f in facts.values():
        f["estado_correspondencia"] = (
            "unica" if len(links[f["artist_mbid"]]) == 1 else "ambigua"
        )
    linkrows = [
        {
            "artist_mbid": mid,
            "artista_uri": uri,
            "estado": "unica" if len(uris) == 1 else "ambigua",
            "fuente_id": "dbpedia",
            **evidence[(mid, uri)],
        }
        for mid, uris in sorted(links.items())
        for uri in sorted(uris)
    ]
    escribir_csv(
        ROOT / "data/processed/piloto_dbpedia_correspondencias.csv",
        linkrows,
        [
            "artist_mbid",
            "artista_uri",
            "estado",
            "fuente_id",
            "consulta_sha256",
            "fecha_consulta",
        ],
    )
    escribir_csv(
        ROOT / "data/processed/piloto_dbpedia_hechos.csv",
        list(facts.values()),
        [
            "artist_mbid",
            "artista_uri",
            "propiedad",
            "relacion",
            "valor",
            "tipo_valor",
            "datatype",
            "fuente_id",
            "metodo",
            "recurso_original",
            "artista_uri_fuente",
            "consulta_sha256",
            "fecha_consulta",
            "estado_correspondencia",
        ],
    )
    unique = {mid for mid, uris in links.items() if len(uris) == 1}
    substantive = {
        f["artist_mbid"]
        for f in facts.values()
        if f["estado_correspondencia"] == "unica" and f["propiedad"] != TYPE
    }
    summary = {
        "canciones_piloto": len(songs),
        "mbid_consultados": len(ids),
        "mbid_encontrados": len(links),
        "mbid_ambiguos": sum(len(u) > 1 for u in links.values()),
        "canciones_con_artista_vinculado_unico": sum(
            s["artist_mbid"] in unique for s in songs
        ),
        "canciones_con_propiedades_mas_alla_del_tipo": sum(
            s["artist_mbid"] in substantive for s in songs
        ),
        "hechos": len(facts),
        "artistas_unicos_por_propiedad": {
            PROPS[prop]: len(
                {
                    f["artist_mbid"]
                    for f in facts.values()
                    if f["propiedad"] == prop and f["estado_correspondencia"] == "unica"
                }
            )
            for prop in PROPS
        },
        "segundos_ejecucion": round(time.monotonic() - started, 2),
        "usa_wikidata_para_vincular": False,
    }
    (ROOT / "docs/piloto_dbpedia.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
