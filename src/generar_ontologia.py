"""Genera el esquema OWL, valida sus etiquetas y actualiza su catálogo."""

import argparse
import json
from pathlib import Path

from musica.comun.rutas import ROOT
from musica.etapa2.etiquetas import validar_etiquetas
from musica.etapa2.ontologia import catalogo_markdown, construir_ontologia, serializar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=ROOT / "ontology.ttl")
    parser.add_argument(
        "--catalogo", type=Path, default=ROOT / "docs/etapa2/catalogo_ontologia.md"
    )
    argumentos = parser.parse_args()
    grafo = construir_ontologia()
    resultado = validar_etiquetas(grafo)
    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    argumentos.catalogo.parent.mkdir(parents=True, exist_ok=True)
    argumentos.salida.write_text(serializar(grafo), encoding="utf-8")
    argumentos.catalogo.write_text(catalogo_markdown(), encoding="utf-8")
    print(
        json.dumps({"triples": len(grafo), **resultado}, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
