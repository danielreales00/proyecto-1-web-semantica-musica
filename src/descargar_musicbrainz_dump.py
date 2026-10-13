"""Descarga verificable de un archivo oficial de MusicBrainz, sin consultas API."""

import argparse
import hashlib
import json
from datetime import datetime, timezone

import requests

from musica.comun.rutas import ROOT


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entidad", choices=["recording", "artist", "work", "release-group"])
    p.add_argument("--fecha", default="20260912-001001")
    a = p.parse_args()
    folder = ROOT / "data/raw/musicbrainz_dump" / a.fecha
    folder.mkdir(parents=True, exist_ok=True)
    base = (
        "https://ftp.musicbrainz.org/pub/musicbrainz/data/json-dumps/" + a.fecha + "/"
    )
    checks = folder / "SHA256SUMS"
    if not checks.exists():
        r = requests.get(base + "SHA256SUMS", timeout=(10, 30))
        r.raise_for_status()
        checks.write_bytes(r.content)
    hashes = {
        line.split()[-1].lstrip("*"): line.split()[0]
        for line in checks.read_text().splitlines()
        if line.strip()
    }
    name = a.entidad + ".tar.xz"
    target = folder / name
    if target.exists():
        assert (
            hashlib.file_digest(target.open("rb"), "sha256").hexdigest() == hashes[name]
        )
        print("Caché verificada:", name)
        return
    with requests.get(base + name, stream=True, timeout=(10, 45)) as r:
        r.raise_for_status()
        total = 0
        with target.with_suffix(".part").open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
                total += len(chunk)
                if total % (20 * 1024 * 1024) == 0:
                    print(f"{name}: {total / 1024**2:.0f} MiB", flush=True)
    temp = target.with_suffix(".part")
    actual = hashlib.file_digest(temp.open("rb"), "sha256").hexdigest()
    assert actual == hashes[name]
    temp.replace(target)
    meta = {
        "fuente_id": "musicbrainz_dump",
        "url": base + name,
        "archivo": name,
        "sha256": actual,
        "bytes": total,
        "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_snapshot": a.fecha,
    }
    target.with_suffix(".xz.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
