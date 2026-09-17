"""Filtra el volcado relacional sin instalar el servidor MusicBrainz.
Lee una vez el tar.bz2, guarda tablas auxiliares comprimidas y conserva evidencia
por tabla/línea. La identidad usa los mismos cuatro criterios del piloto.
"""

import argparse
import gzip
import json
import tarfile
import time
from collections import Counter, defaultdict

from ampliar_albumes import read, sha
from diagnostico import ROOT, normalizar

FOLDER = ROOT / "data/raw/musicbrainz_completo/20260916-002105"
ARCHIVE = FOLDER / "mbdump.tar.bz2"
OUT = FOLDER / "subconjunto"
SCRATCH = ROOT / "tmp/musicbrainz_tablas"
NULL = "\\N"


def unescape(s):
    if s == NULL:
        return ""
    if "\\" not in s:
        return s
    mapping = {
        "t": "\t",
        "n": "\n",
        "r": "\r",
        "b": "\b",
        "f": "\f",
        "v": "\v",
        "\\": "\\",
    }
    # PostgreSQL COPY escapes are decoded once, preserving literal backslashes.
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            i += 1
            out.append(mapping.get(s[i], s[i]))
        else:
            out.append(s[i])
        i += 1
    return "".join(out)


def cells(line):
    return [unescape(s) for s in line.decode("utf-8").rstrip("\n").split("\t")]


def saved(name):
    with gzip.open(SCRATCH / (name + ".tsv.gz"), "rb") as f:
        for i, line in enumerate(f, 1):
            yield i, cells(line)


def write_json(name, rows):
    with (OUT / (name + ".jsonl")).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_json(name):
    with (OUT / (name + ".jsonl")).open(encoding="utf-8") as f:
        return [json.loads(s) for s in f]


def raw(i, c):
    return {"linea": i, "columnas": c}


# All ancillary rows are temporary only; final exports include linked entities.
AUX = {
    "artist",
    "artist_credit_name",
    "area",
    "area_iso_3166_1",
    "artist_type",
    "gender",
    "isrc",
    "l_recording_work",
    "l_artist_recording",
    "l_artist_work",
    "link",
    "link_type",
    "link_attribute",
    "link_attribute_type",
    "work",
    "work_type",
    "work_language",
    "language",
    "medium",
    "release_country",
    "release_unknown_country",
    "release_label",
    "label",
    "release_status",
    "release_group",
    "release_group_primary_type",
}


class GrowingFile:
    """Lectura local de la descarga en progreso; nunca interpreta EOF temporal como final."""

    def __init__(self):
        self.file = (
            ARCHIVE if ARCHIVE.exists() else ARCHIVE.with_name(ARCHIVE.name + ".part")
        ).open("rb")

    def read(self, size=-1):
        assert size >= 0
        data = bytearray()
        last = time.monotonic()
        while len(data) < size:
            chunk = self.file.read(size - len(data))
            if chunk:
                data.extend(chunk)
                last = time.monotonic()
                continue
            if ARCHIVE.exists():
                break
            if time.monotonic() - last > 180:
                raise TimeoutError("Descarga sin avance durante tres minutos")
            time.sleep(1)
        return bytes(data)

    def close(self):
        self.file.close()


class CandidatosMusicBrainz:
    """Índices de entrada y evidencia seleccionada durante el recorrido de tablas."""

    def __init__(self, base):
        self.bytid = {r["track_id"]: r for r in base}
        self.mids = {r["artist_mbid"] for r in base}
        self.albumtitles = {normalizar(r["release"]) for r in base}
        self.songkeys = defaultdict(list)
        for row in base:
            self.songkeys[(row["artist_mbid"], normalizar(row["title"]))].append(row)
        self.artists = {}
        self.credits = defaultdict(set)
        self.recs = {}
        self.possible = {}
        self.release_names = {}
        self.releases = {}
        self.media = {}
        self.tracks = []
        self.matches = defaultdict(set)

    def conservar_artista(self, line_number, columns):
        if columns[1] in self.mids:
            self.artists[columns[0]] = columns[1]

    def conservar_credito(self, line_number, columns):
        if columns[2] in self.artists:
            self.credits[columns[0]].add(self.artists[columns[2]])

    def conservar_grabacion(self, line_number, columns):
        if columns[3] not in self.credits or not columns[4]:
            return
        title = normalizar(columns[2])
        candidate = set()
        for mid in self.credits[columns[3]]:
            for song in self.songkeys.get((mid, title), []):
                if abs(int(columns[4]) / 1000 - float(song["duration"])) <= 3:
                    candidate.add(song["track_id"])
        if candidate:
            self.recs[columns[0]] = raw(line_number, columns)
            self.possible[columns[0]] = candidate

    def conservar_lanzamiento(self, line_number, columns):
        if normalizar(columns[2]) in self.albumtitles:
            self.releases[columns[0]] = raw(line_number, columns)
            self.release_names[columns[0]] = normalizar(columns[2])

    def conservar_pista(self, line_number, columns):
        if columns[2] not in self.possible or columns[3] not in self.media:
            return
        releaseid = self.media[columns[3]]
        eligible = {
            tid
            for tid in self.possible[columns[2]]
            if normalizar(self.bytid[tid]["release"]) == self.release_names[releaseid]
        }
        if eligible:
            self.tracks.append(raw(line_number, columns))
            for tid in eligible:
                self.matches[tid].add(columns[2])


def recorrer_tabla(tar, member, candidates):
    name = member.name.removeprefix("mbdump/")
    handlers = {
        "artist": candidates.conservar_artista,
        "artist_credit_name": candidates.conservar_credito,
        "recording": candidates.conservar_grabacion,
        "release": candidates.conservar_lanzamiento,
        "track": candidates.conservar_pista,
    }
    handler = handlers.get(name)
    print("Leyendo", name, f"({member.size / 1024**2:.0f} MiB)", flush=True)
    if name == "track":
        # medium precede a release. Su copia temporal se filtra al llegar a track.
        candidates.media = {
            c[0]: c[1] for _, c in saved("medium") if c[1] in candidates.releases
        }
        print("Medios relacionados:", len(candidates.media), flush=True)
    sink = (
        gzip.open(SCRATCH / (name + ".tsv.gz"), "wb", compresslevel=1)
        if name in AUX
        else None
    )
    count = 0
    for line_number, line in enumerate(tar.extractfile(member), 1):
        count += 1
        if count % 1000000 == 0:
            print(name, format(count, ","), "filas examinadas", flush=True)
        if sink:
            sink.write(line)
        if handler is not None:
            handler(line_number, cells(line))
    if sink:
        sink.close()
    print("Terminada", name, format(count, ","), "filas", flush=True)
    return count


def abrir_fuente(growing):
    if growing:
        checksum = next(
            line.split()[0]
            for line in (FOLDER / "SHA256SUMS").read_text().splitlines()
            if line.split()[-1].lstrip("*") == "mbdump.tar.bz2"
        )
        return {"sha256": checksum}, GrowingFile()
    source = json.loads((FOLDER / "mbdump.tar.bz2.json").read_text())
    assert sha(ARCHIVE) == source["sha256"]
    return source, None


def verificar_descarga_finalizada(reader):
    reader.close()
    for _ in range(60):
        if (FOLDER / "mbdump.tar.bz2.json").exists():
            break
        time.sleep(1)
    source = json.loads((FOLDER / "mbdump.tar.bz2.json").read_text())
    assert sha(ARCHIVE) == source["sha256"]
    return source


def guardar_candidatos(candidates, base, source, stats):
    accepted = {next(iter(rs)) for rs in candidates.matches.values() if len(rs) == 1}
    write_json("recording_candidatos", candidates.recs.values())
    write_json("track_candidatos", candidates.tracks)
    related_releases = {candidates.media[t["columnas"][3]] for t in candidates.tracks}
    write_json(
        "release_candidatos",
        [r for rid, r in candidates.releases.items() if rid in related_releases],
    )
    related_media = {t["columnas"][3] for t in candidates.tracks}
    write_json(
        "medium_candidatos",
        [raw(i, c) for i, c in saved("medium") if c[0] in related_media],
    )
    # Preserve all decisions, including ambiguity, before selecting related details.
    decisions = []
    for s in base:
        ids = sorted(candidates.matches[s["track_id"]])
        state = (
            "aceptada"
            if len(ids) == 1
            else "ambigua"
            if ids
            else "sin_coincidencia_conservadora"
        )
        decisions.append(
            {
                "track_id": s["track_id"],
                "estado": state,
                "recording_id": ids[0] if len(ids) == 1 else "",
                "recording_mbid": candidates.recs[ids[0]]["columnas"][1]
                if len(ids) == 1
                else "",
                "candidatos_elegibles": [
                    candidates.recs[r]["columnas"][1] for r in ids
                ],
            }
        )
    write_json("correspondencias", decisions)
    meta = {
        **source,
        "sha256_entrada": sha(ROOT / "grupo_2.csv"),
        "tablas_examinadas": stats,
        "recordings_candidatos_titulo_artista_duracion": len(candidates.recs),
        "grabaciones_aceptadas": len(accepted),
        "estados": dict(Counter(r["estado"] for r in decisions)),
        "recorrido_completo": True,
    }
    (OUT / "extraccion.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


def scan(growing=False):
    source, reader = abrir_fuente(growing)
    base = read(ROOT / "grupo_2.csv")
    candidates = CandidatosMusicBrainz(base)
    stats = {}
    OUT.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tarfile.open(
        None if growing else ARCHIVE, fileobj=reader, mode="r|bz2", bufsize=1024 * 1024
    ) as tar:
        for member in tar:
            name = member.name.removeprefix("mbdump/")
            if not member.isfile():
                continue
            if name not in AUX | {"recording", "release", "track"}:
                continue
            stats[name] = recorrer_tabla(tar, member, candidates)
    if growing:
        source = verificar_descarga_finalizada(reader)
    guardar_candidatos(candidates, base, source, stats)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mientras-descarga", action="store_true")
    a = p.parse_args()
    scan(a.mientras_descarga)
