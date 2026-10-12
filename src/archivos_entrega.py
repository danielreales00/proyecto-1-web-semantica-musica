"""Selección explícita de entradas reproducibles y archivos de entrega."""

import hashlib
import json
from pathlib import Path

from musica.comun.rutas import ROOT

BASE = [
    "grupo_2.csv",
    "Proyecto___Etapa_1__MISIS_.pdf",
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    ".gitignore",
]
DOCS_ENTRADA = ["docs/diccionario_datos.md"]


def arbol(root, folder):
    for p in sorted((root / folder).rglob("*")):
        if p.is_symlink():
            raise ValueError(f"Enlace simbólico no esperado en la entrega: {p}")
        if (
            p.is_file()
            and "__pycache__" not in p.parts
            and p.name != ".DS_Store"
            and p.suffix not in (".pyc", ".part", ".tmp")
        ):
            yield p


def entradas(root=ROOT):
    """Archivos suficientes para reconstruir desde una carpeta sin resultados."""
    root = Path(root)
    files = {root / name for name in BASE + DOCS_ENTRADA}
    for folder in [
        "src",
        "tests",
        "latex",
        "exploraciones/sparql",
        ".github/workflows",
        "data/raw/api",
        "data/raw/wikidata",
        "data/raw/wikidata_etiquetas",
        "data/raw/dbpedia",
        "data/processed/api_derivadas",
        "data/processed/estado_servicios",
        "data/raw/musicbrainz_completo/20260916-002105/subconjunto",
        "data/raw/acousticbrainz_dump/20220623/subconjunto",
    ]:
        files.update(arbol(root, folder))
    for name in ["msd-jmir-spectral-all-all-v1.0.arff.gz", "msd_tagtraum_cd2.cls.zip"]:
        files.update([root / "data/raw" / name, root / "data/raw" / (name + ".json")])
    folder = root / "data/raw/musicbrainz_dump/20260912-001001"
    files.update(
        folder / name
        for name in [
            "release-group_candidatos.jsonl",
            "release-group_extraccion.json",
            "release-group.tar.xz.json",
            "SHA256SUMS",
        ]
    )
    folder = root / "data/raw/musicbrainz_completo/20260916-002105"
    files.update(folder / name for name in ["mbdump.tar.bz2.json", "SHA256SUMS"])
    folder = root / "data/raw/acousticbrainz_dump/20220623"
    files.add(folder / "sha256sums")
    files.update(folder.glob("*.tar.zst.json"))
    missing = [str(p.relative_to(root)) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("Entradas ausentes: " + ", ".join(sorted(missing)))
    return sorted(files)


def huellas_entradas(root=ROOT):
    root = Path(root)
    result = {}
    for path in entradas(root):
        with path.open("rb") as stream:
            result[path.relative_to(root).as_posix()] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
    return result


def firma_entradas(huellas):
    return hashlib.sha256(
        json.dumps(huellas, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
