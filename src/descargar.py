"""Descargas verificables y atómicas de fuentes públicas."""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

import requests

from diagnostico import ROOT

FUENTES = {
    "tagtraum": {
        "url": "https://www.tagtraum.com/genres/msd_tagtraum_cd2.cls.zip",
        "archivo": "msd_tagtraum_cd2.cls.zip",
        "documentacion": "https://www.tagtraum.com/msd_genre_datasets.html",
        "licencia": "Solo investigación no comercial",
    },
    "jmir": {
        "url": "https://www.ifs.tuwien.ac.at/mir/msd/downloads/msd-jmir-spectral-all-all-v1.0.arff.gz",
        "archivo": "msd-jmir-spectral-all-all-v1.0.arff.gz",
        "documentacion": "https://www.ifs.tuwien.ac.at/mir/msd/download.html",
        "licencia": "CC BY-NC-SA 2.0 (publicación ISMIR 2012)",
    },
}


def descargar(nombre):
    source = FUENTES[nombre]
    target = ROOT / "data/raw" / source["archivo"]
    manifest = target.with_suffix(target.suffix + ".json")
    if target.exists() and manifest.exists():
        m = json.loads(manifest.read_text())
        if hashlib.file_digest(target.open("rb"), "sha256").hexdigest() != m["sha256"]:
            raise ValueError(f"Hash incorrecto: {target}")
        print(f"{nombre}: caché verificada", flush=True)
        return
    for attempt in range(3):
        try:
            with requests.get(source["url"], stream=True, timeout=(20, 60)) as r:
                r.raise_for_status()
                with target.with_suffix(target.suffix + ".part").open("wb") as out:
                    for chunk in r.iter_content(1024 * 1024):
                        out.write(chunk)
                final_url = r.url
            target.with_suffix(target.suffix + ".part").replace(target)
            metadata = {
                **source,
                "fuente_id": nombre,
                "url_final": final_url,
                "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
                "bytes": target.stat().st_size,
                "sha256": hashlib.file_digest(target.open("rb"), "sha256").hexdigest(),
            }
            manifest.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
            )
            print(f"{nombre}: {metadata['bytes']:,} bytes descargados", flush=True)
            return
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2**attempt)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("fuentes", nargs="*", default=list(FUENTES))
    a = p.parse_args()
    for name in a.fuentes:
        descargar(name)
