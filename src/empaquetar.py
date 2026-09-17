"""Crea un único ZIP de entrega y verifica cada archivo contra su SHA-256."""

import hashlib
import json
import zipfile

from archivos_entrega import entregables
from diagnostico import ROOT


def main():
    files = entregables(ROOT)
    manifest = {
        str(p.relative_to(ROOT)): {
            "bytes": p.stat().st_size,
            "sha256": hashlib.file_digest(p.open("rb"), "sha256").hexdigest(),
        }
        for p in files
    }
    path = ROOT / "manifiesto_archivos.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    archive = ROOT / "output/entrega_final_latex.zip"
    temporary = archive.with_suffix(".zip.tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as z:
        for p in files + [path]:
            z.write(p, arcname="entrega_etapa_1/" + str(p.relative_to(ROOT)))
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        for name, entry in manifest.items():
            assert (
                hashlib.sha256(z.read("entrega_etapa_1/" + name)).hexdigest()
                == entry["sha256"]
            ), name
    temporary.replace(archive)
    print(
        f"Paquete verificado: {archive.stat().st_size / 1024**2:.1f} MiB, {len(files) + 1} archivos."
    )


if __name__ == "__main__":
    main()
