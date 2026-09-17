"""Recorre los CSV completos sin descomprimirlos en disco; conserva evidencia vinculada."""

import csv
import json
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone

from descargar_acousticbrainz_dump import FOLDER, KINDS, sha
from diagnostico import ROOT

OUT = FOLDER / "subconjunto"
EXPECTED = 29_460_584


class FiltroAcousticBrainz:
    """Acumula cobertura y evidencia de una familia de descriptores."""

    def __init__(self, kind, ids):
        self.kind = kind
        self.ids = ids
        self.count = 0
        self.kept = 0
        self.duplicate_keys = 0
        self.seen = set()
        self.members = []
        self.header = []

    def recorrer_csv(self, source, member_name, dest):
        self.members.append(member_name)
        self.header = next(
            csv.reader([source.readline().decode("utf-8").rstrip("\r\n")])
        )
        if self.header[:2] != ["mbid", "submission_offset"]:
            raise ValueError(f"Identificadores inesperados: {self.header}")
        # UUID y offset iniciales sin comillas en el formato oficial.
        # Solo se parsean por completo las filas que pertenecen al proyecto.
        for lineno, raw in enumerate(source, 2):
            self.count += 1
            mid = raw[:36].decode("ascii")
            if mid in self.ids:
                values = next(csv.reader([raw.decode("utf-8").rstrip("\r\n")]))
                if len(values) != len(self.header) or values[0] != mid:
                    raise ValueError(f"Fila incompatible en {member_name}:{lineno}")
                row = dict(zip(self.header, values))
                key = (mid, int(row["submission_offset"]))
                if key in self.seen:
                    self.duplicate_keys += 1
                self.seen.add(key)
                dest.write(
                    json.dumps(
                        {
                            "archivo_interno": member_name,
                            "linea": lineno,
                            "valores": row,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                self.kept += 1
            if self.count % 5_000_000 == 0:
                print(
                    f"{self.kind}: {self.count:,} filas; {self.kept:,} vinculadas",
                    flush=True,
                )


def recorrer_archivo(stdout, dest, selected):
    with tarfile.open(fileobj=stdout, mode="r|") as tar:
        for member in tar:
            if not member.isfile():
                continue
            if member.name.rsplit("/", 1)[-1] == "COPYING":
                (OUT / (selected.kind + "_COPYING")).write_bytes(
                    tar.extractfile(member).read()
                )
                continue
            if not member.name.endswith(".csv"):
                raise ValueError(f"Miembro inesperado: {member.name}")
            selected.recorrer_csv(tar.extractfile(member), member.name, dest)


def extraer_familia(kind, ids):
    name = f"acousticbrainz-lowlevel-features-20220623-{kind}.tar.zst"
    archive = FOLDER / name
    meta = json.loads(archive.with_name(name + ".json").read_text())
    if sha(archive) != meta["sha256"]:
        raise ValueError(f"SHA-256 incorrecto: {name}")
    target = OUT / (kind + ".jsonl")
    temp = target.with_suffix(".part")
    process = subprocess.Popen(["zstd", "-dc", str(archive)], stdout=subprocess.PIPE)
    selected = FiltroAcousticBrainz(kind, ids)
    try:
        with temp.open("w") as dest:
            recorrer_archivo(process.stdout, dest, selected)
        # Consumir cualquier relleno que reste antes de comprobar el proceso.
        while process.stdout.read(1024**2):
            pass
        if process.wait() != 0:
            raise RuntimeError(f"Descompresión fallida: {archive}")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
    if selected.count != EXPECTED or len(selected.members) != 1:
        raise ValueError(
            f"Recorrido incompleto: {selected.count} filas; {len(selected.members)} miembros"
        )
    temp.replace(target)
    result = {
        **meta,
        "filas_recorridas": selected.count,
        "filas_vinculadas": selected.kept,
        "archivo_interno": selected.members[0],
        "columnas": selected.header,
        "subconjunto_archivo": target.name,
        "subconjunto_sha256": sha(target),
        "grabaciones_vinculadas": len({k[0] for k in selected.seen}),
        "claves_mbid_offset_repetidas": selected.duplicate_keys,
        "grabaciones_con_offset_cero": sum(k[1] == 0 for k in selected.seen),
        "recorrido_completo": True,
    }
    print(
        f"{kind}: recorrido completo, {selected.kept:,} entregas vinculadas.",
        flush=True,
    )
    return result


def verificar_archivos():
    if not shutil.which("zstd"):
        raise RuntimeError("La extracción completa requiere el ejecutable zstd.")
    for kind in KINDS:
        archive = FOLDER / f"acousticbrainz-lowlevel-features-20220623-{kind}.tar.zst"
        if (
            not archive.exists()
            or not archive.with_name(archive.name + ".json").exists()
        ):
            raise FileNotFoundError(
                "Primero debe terminar descargar_acousticbrainz_dump.py para las tres familias."
            )


def main():
    verificar_archivos()
    inputs = ROOT / "output/csv/grabaciones_masivas.csv"
    with inputs.open(newline="") as stream:
        ids = {r["recording_mbid"] for r in csv.DictReader(stream)}
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for kind in KINDS:
        manifest[kind] = extraer_familia(kind, ids)
    summary = {
        "fecha_extraccion_utc": datetime.now(timezone.utc).isoformat(),
        "sha256_entrada": sha(ROOT / "grupo_2.csv"),
        "grabaciones_objetivo": len(ids),
        "sha256_grabaciones_objetivo": sha(inputs),
        "metodo_vinculo": "MBID exacto de grabación aceptada en el volcado MusicBrainz",
        "fuentes": manifest,
    }
    (OUT / "extraccion.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
