"""Descarga los tres volcados oficiales de características; verifica sus SHA-256."""

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone

import requests

from diagnostico import ROOT

BASE = "https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-lowlevel-features-20220623/"
FOLDER = ROOT / "data/raw/acousticbrainz_dump/20220623"
KINDS = ("lowlevel", "rhythm", "tonal")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    checks = FOLDER / "sha256sums"
    if not checks.exists():
        response = requests.get(BASE + "sha256sums", timeout=(15, 60))
        response.raise_for_status()
        checks.write_bytes(response.content)
    hashes = {
        line.split()[-1].lstrip("*"): line.split()[0]
        for line in checks.read_text().splitlines()
        if line.strip()
    }
    for kind in KINDS:
        name = f"acousticbrainz-lowlevel-features-20220623-{kind}.tar.zst"
        path = FOLDER / name
        if path.exists():
            if sha(path) != hashes[name]:
                raise ValueError(f"SHA-256 incorrecto: {name}")
            print(f"Verificado: {name}", flush=True)
            continue
        temp = path.with_name(path.name + ".part")
        start = time.monotonic()
        total = 0
        next_log = 128 * 1024**2
        with requests.get(BASE + name, stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            expected = int(response.headers.get("Content-Length", 0))
            if shutil.disk_usage(FOLDER).free < expected + 2 * 1024**3:
                raise OSError("Espacio insuficiente: se reservan 2 GiB adicionales.")
            with temp.open("wb") as stream:
                for block in response.iter_content(4 * 1024**2):
                    stream.write(block)
                    total += len(block)
                    if total >= next_log:
                        print(
                            f"{kind}: {total / 1024**2:.0f}/{expected / 1024**2:.0f} MiB; "
                            f"{total / 1024**2 / (time.monotonic() - start):.1f} MiB/s",
                            flush=True,
                        )
                        next_log += 128 * 1024**2
        if expected and total != expected:
            raise ValueError(f"Descarga incompleta: {name}")
        actual = sha(temp)
        if actual != hashes[name]:
            raise ValueError(f"SHA-256 incorrecto: {name}")
        temp.replace(path)
        meta = {
            "fuente_id": "acousticbrainz_dump",
            "url": BASE + name,
            "archivo": name,
            "sha256": actual,
            "bytes": total,
            "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
            "fecha_snapshot": "20220623",
            "familia": kind,
            "alcance": "Todas las entregas, subconjunto oficial de características; no JSON completo.",
        }
        path.with_name(name + ".json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
        )
        print(f"{kind}: descarga completa y SHA-256 oficial verificado.", flush=True)


if __name__ == "__main__":
    main()
