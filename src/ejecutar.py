"""Reconstruye datos, consultas y documentos desde la evidencia, sin consultar servicios."""

import argparse
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from archivos_entrega import entradas
from diagnostico import ROOT


def preparar_destino(destino):
    if destino is None:
        return ROOT
    target = destino.resolve()
    if target.exists():
        raise FileExistsError("El destino debe ser una carpeta nueva")
    source_files = entradas(ROOT)
    target.mkdir(parents=True)
    for path in source_files:
        dest = target / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Modo predeterminado. HTTP siempre está bloqueado",
    )
    parser.add_argument(
        "--destino", type=Path, help="Carpeta nueva, sin resultados precalculados"
    )
    parser.add_argument(
        "--solo-datos",
        action="store_true",
        help="Reconstruir CSV, sin SPARQL ni PDF",
    )
    args = parser.parse_args()
    target = preparar_destino(args.destino)
    for folder in ["docs", "output/csv", "output/sparql", "data/processed", "tmp"]:
        (target / folder).mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PROYECTO_ROOT": str(target),
        "PYTHONPATH": str(target / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def run(relative, *arguments, extra_env=None):
        print("Ejecutando sin red: " + relative + " " + " ".join(arguments), flush=True)
        subprocess.run(
            [
                sys.executable,
                str(target / "src/ejecutar.py"),
                "--paso",
                str(target / relative),
                *arguments,
            ],
            cwd=target,
            env={**env, **(extra_env or {})},
            check=True,
        )

    steps = [
        ["diagnostico.py"],
        ["descargar.py"],
        ["fuentes_masivas.py", "--piloto"],
        ["fuentes_masivas.py"],
        ["wikidata.py", "--piloto", "--offline"],
        ["dbpedia.py", "--offline"],
        ["comparar_fuentes.py"],
        ["auditar_cache_musicbrainz.py"],
        ["consolidar_piloto.py"],
        ["integrar.py"],
        ["wikidata.py", "--offline"],
        ["wikidata_etiquetas.py", "--offline"],
        ["ampliar_artistas.py"],
        ["ampliar_albumes.py"],
        ["consolidar_musicbrainz_completo.py"],
        ["consolidar_acousticbrainz_dump.py"],
        ["integrar_ampliacion.py"],
        ["validar.py"],
        ["validar_ampliacion.py"],
    ]
    for script, *arguments in steps:
        run("src/" + script, *arguments)
    if not args.solo_datos:
        # Cada reproducción parte de un grafo vacío. Se eliminan sus archivos al terminar.
        with tempfile.TemporaryDirectory(
            prefix="sparql_", dir=target / "tmp"
        ) as folder:
            graph_env = {"PROYECTO_SPARQL_STORE": str(Path(folder) / "almacen")}
            for script in [
                "ejecutar.py",
                "ampliacion.py",
                "acousticbrainz.py",
            ]:
                run("exploraciones/sparql/" + script, extra_env=graph_env)
        run("latex/compilar.py", "--offline")
    print(f"Entrega reconstruida en {target}")


def ejecutar_paso(script, arguments):
    """Ejecuta un módulo con sus argumentos y bloquea HTTP durante todo el paso."""
    sys.argv = [str(script), *arguments]
    sys.path.insert(0, str(script.parent))
    with patch(
        "requests.sessions.Session.request",
        side_effect=RuntimeError("Red deshabilitada en reproducción"),
    ):
        runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--paso":
        ejecutar_paso(Path(sys.argv[2]), sys.argv[3:])
    else:
        main()
