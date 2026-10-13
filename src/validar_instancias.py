"""Valida el RDF exportado junto con su esquema y guarda los resultados."""

import argparse
import json
from pathlib import Path

from musica.comun.rutas import ROOT
from musica.etapa2.validacion import validar_archivos


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontologia", type=Path, default=ROOT / "ontology.ttl")
    parser.add_argument(
        "--instancias", type=Path, default=ROOT / "output/etapa2/instances.ttl"
    )
    args = parser.parse_args()
    resultado = validar_archivos(args.ontologia, args.instancias)
    args.instancias.with_suffix(".validacion.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
