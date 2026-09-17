"""Retira archivos regenerables solo después de verificar la entrega conservada."""

import argparse
import hashlib
import json
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

from archivos_entrega import entregables, firma_entradas, huellas_entradas
from diagnostico import ROOT
from empaquetar import main as empaquetar

GESTIONADOS = [
    "data",
    "docs",
    "src",
    "tests",
    "latex",
    "exploraciones",
    "output",
    "tmp",
    ".ruff_cache",
]


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def candidatos():
    protected = set(entregables(ROOT))
    protected.update(
        [ROOT / "manifiesto_archivos.json", ROOT / "output/entrega_final_latex.zip"]
    )
    files = []
    for name in GESTIONADOS:
        for path in (ROOT / name).rglob("*"):
            if (path.is_file() or path.is_symlink()) and path not in protected:
                files.append(path)
    return sorted(files)


def resumen(files):
    groups = defaultdict(lambda: {"archivos": 0, "bytes": 0})
    for path in files:
        key = path.relative_to(ROOT).parts[0]
        groups[key]["archivos"] += 1
        groups[key]["bytes"] += path.lstat().st_size
    largest = sorted(files, key=lambda p: p.lstat().st_size, reverse=True)[:15]
    return {
        "archivos_a_retirar": len(files),
        "bytes_a_retirar": sum(g["bytes"] for g in groups.values()),
        "por_carpeta": dict(groups),
        "mayores_archivos": [
            {"ruta": p.relative_to(ROOT).as_posix(), "bytes": p.lstat().st_size}
            for p in largest
        ],
    }


def verificar_respaldo():
    verification = json.loads((ROOT / "docs/reproducibilidad_entrega.json").read_text())
    if verification["estado"] != "correcto":
        raise ValueError("Primero debe pasar la verificación completa de la entrega")
    for name, expected in verification["csv_sha256"].items():
        if sha(ROOT / "output/csv" / name) != expected:
            raise ValueError("CSV modificado después de verificar: " + name)
    if firma_entradas(huellas_entradas(ROOT)) != verification["firma_entradas_sha256"]:
        raise ValueError("Entradas modificadas o agregadas después de verificar")
    manifest = json.loads((ROOT / "manifiesto_archivos.json").read_text())
    with zipfile.ZipFile(ROOT / "output/entrega_final_latex.zip") as archive:
        for path in entregables(ROOT):
            name = path.relative_to(ROOT).as_posix()
            expected = manifest[name]["sha256"]
            if sha(path) != expected:
                raise ValueError("Actualizar el paquete antes de limpiar: " + name)
            if (
                hashlib.sha256(archive.read("entrega_etapa_1/" + name)).hexdigest()
                != expected
            ):
                raise ValueError("Archivo no respaldado en el paquete: " + name)


def retirar(files):
    for path in files:
        path.unlink()
    directories = []
    for name in GESTIONADOS:
        folder = ROOT / name
        directories.extend(
            p for p in folder.rglob("*") if p.is_dir() and not p.is_symlink()
        )
        if folder.is_dir():
            directories.append(folder)
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Retirar los archivos indicados después de validar el paquete",
    )
    args = parser.parse_args()
    files = candidatos()
    report = resumen(files)
    if not args.aplicar:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    verificar_respaldo()
    retirar(files)
    report.update(
        {
            "estado": "completado",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "criterio": "Conservar entregables seleccionados y su evidencia, retirar copias e intermedios regenerables.",
            "reproduccion_completa_verificada": True,
        }
    )
    empaquetar()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
