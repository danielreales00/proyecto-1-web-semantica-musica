"""Genera las instancias musicales a partir de los CSV de la primera entrega."""

import argparse

from musica.comun.rutas import ROOT
from musica.etapa2.instancias import generar_instancias


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", default=ROOT / "output/csv")
    parser.add_argument("--salida", default=ROOT / "output/etapa2/instances.ttl")
    args = parser.parse_args()
    resumen = generar_instancias(args.entrada, args.salida)
    print(
        f"Generadas {resumen['referencias_locales']} referencias locales y {resumen['recursos']} recursos etiquetados."
    )


if __name__ == "__main__":
    main()
