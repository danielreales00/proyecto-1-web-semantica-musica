"""Empaqueta la entrega reproducible, incluidos los CSV e instancias completos."""

import json
import zipfile

from musica.comun.rutas import ROOT
from musica.etapa2.escritura import sha_archivo


def archivos_entrega():
    fijos = [
        "README.md",
        "README_ETAPA_2.md",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-owl.txt",
        "pyproject.toml",
        "compose.yaml",
        "ontology.ttl",
        "latex/informe_etapa2.tex",
        "output/pdf/informe_etapa2.pdf",
    ]
    archivos = [ROOT / nombre for nombre in fijos]
    for carpeta in (
        "src",
        "tests",
        "docker/fuseki",
        "docs/etapa2",
        "consultas/etapa2",
        "output/csv",
        "output/etapa2",
    ):
        archivos.extend(
            p
            for p in (ROOT / carpeta).rglob("*")
            if p.is_file()
            and "__pycache__" not in p.parts
            and not p.name.endswith((".pyc", ".tmp", ".ttl.gz"))
        )
    for archivo in archivos:
        if not archivo.is_file():
            raise FileNotFoundError(archivo)
    return sorted(set(archivos))


def main():
    archivos = archivos_entrega()
    manifiesto = {
        str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha_archivo(p)}
        for p in archivos
    }
    salida = ROOT / "output/entrega_etapa2.zip"
    temporal = salida.with_suffix(".zip.tmp")
    with zipfile.ZipFile(
        temporal,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as paquete:
        for archivo in archivos:
            paquete.write(archivo, archivo.relative_to(ROOT))
        paquete.writestr(
            "MANIFIESTO_ETAPA2.json",
            json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n",
        )
    with zipfile.ZipFile(temporal) as paquete:
        error = paquete.testzip()
        if error:
            raise ValueError(f"Archivo corrupto: {error}")
    temporal.replace(salida)
    print(
        json.dumps(
            {
                "archivo": str(salida),
                "archivos": len(archivos),
                "bytes": salida.stat().st_size,
                "sha256": sha_archivo(salida),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
