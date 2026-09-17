"""Descarga del núcleo relacional oficial; verifica SHA-256 publicado y conserva procedencia."""

import hashlib
import json
from datetime import datetime, timezone

import requests

from diagnostico import ROOT


def main():
    date = "20260916-002105"
    folder = ROOT / "data/raw/musicbrainz_completo" / date
    folder.mkdir(parents=True, exist_ok=True)
    base = "https://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/" + date + "/"
    checks = folder / "SHA256SUMS"
    if not checks.exists():
        r = requests.get(base + "SHA256SUMS", timeout=(10, 40))
        r.raise_for_status()
        checks.write_bytes(r.content)
    hashes = {
        line.split()[-1].lstrip("*"): line.split()[0]
        for line in checks.read_text().splitlines()
        if line.strip()
    }
    name = "mbdump.tar.bz2"
    path = folder / name
    temp = folder / (name + ".part")
    if path.exists():
        assert (
            hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == hashes[name]
        )
        print("Volcado completo verificado")
        return
    with requests.get(base + name, stream=True, timeout=(10, 60)) as r:
        r.raise_for_status()
        expected = int(r.headers.get("Content-Length", 0))
        total = 0
        with temp.open("wb") as f:
            for chunk in r.iter_content(4 * 1024**2):
                f.write(chunk)
                total += len(chunk)
                if total % (100 * 1024**2) == 0:
                    print(
                        f"{total / 1024**3:.2f} GiB / {expected / 1024**3:.2f} GiB",
                        flush=True,
                    )
    if expected:
        assert total == expected
    actual = hashlib.file_digest(temp.open("rb"), "sha256").hexdigest()
    assert actual == hashes[name]
    temp.replace(path)
    meta = {
        "fuente_id": "musicbrainz_completo",
        "url": base + name,
        "archivo": name,
        "sha256": actual,
        "bytes": total,
        "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_snapshot": date,
    }
    (folder / (name + ".json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
