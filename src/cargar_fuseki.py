"""Carga esquema e instancias en dos grafos propios y conserva evidencia HTTP."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from configuracion import DATA_URL, GRAFO_INSTANCIAS, GRAFO_ONTOLOGIA, QUERY_URL
from musica.comun.rutas import ROOT
from musica.etapa2.escritura import sha_archivo


def consultar(texto):
    respuesta = requests.post(
        QUERY_URL,
        data={"query": texto},
        headers={"Accept": "application/sparql-results+json"},
        timeout=(10, 1800),
    )
    respuesta.raise_for_status()
    return respuesta.json()


def cargar(ontologia, instancias, evidencia):
    consultar("ASK {}")
    informe = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "query_url": QUERY_URL,
        "data_url": DATA_URL,
        "cargas": [],
    }
    for ruta, grafo in ((ontologia, GRAFO_ONTOLOGIA), (instancias, GRAFO_INSTANCIAS)):
        print(f"Cargando {ruta.name} en {grafo}", flush=True)
        with ruta.open("rb") as archivo:
            respuesta = requests.put(
                DATA_URL,
                params={"graph": grafo},
                data=archivo,
                headers={"Content-Type": "text/turtle"},
                timeout=(10, 1800),
            )
        respuesta.raise_for_status()
        informe["cargas"].append(
            {
                "archivo": ruta.name,
                "grafo": grafo,
                "sha256": sha_archivo(ruta),
                "http": respuesta.status_code,
            }
        )
    informe["triples_por_grafo"] = consultar(
        "SELECT ?grafo (COUNT(*) AS ?triples) WHERE { GRAPH ?grafo { ?s ?p ?o } } GROUP BY ?grafo ORDER BY ?grafo"
    )
    informe["grabaciones"] = consultar(
        "PREFIX mus: <https://example.org/musica/> SELECT (COUNT(DISTINCT ?g) AS ?total) WHERE { ?g a mus:Grabacion }"
    )
    evidencia.parent.mkdir(parents=True, exist_ok=True)
    evidencia.write_text(
        json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return informe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontologia", type=Path, default=ROOT / "ontology.ttl")
    parser.add_argument(
        "--instancias", type=Path, default=ROOT / "output/etapa2/instances.ttl"
    )
    parser.add_argument(
        "--evidencia", type=Path, default=ROOT / "output/etapa2/fuseki_carga.json"
    )
    args = parser.parse_args()
    print(
        json.dumps(
            cargar(args.ontologia, args.instancias, args.evidencia),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
