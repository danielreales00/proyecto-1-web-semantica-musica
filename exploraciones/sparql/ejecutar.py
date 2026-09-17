"""Grafo experimental y consultas SPARQL reales, independientes de la entrega etapa 1."""

import argparse
import csv
import hashlib
import json
import os
import time
from collections import defaultdict
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from pyoxigraph import Literal, NamedNode, Quad, Store

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sparql"
STORE_PATH = Path(os.environ.get("PROYECTO_SPARQL_STORE", str(OUT / "almacen")))
NS = "https://example.org/musica/"
TYPE = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
DECIMAL = NamedNode("http://www.w3.org/2001/XMLSchema#decimal")


def node(name):
    return NamedNode(NS + name)


def rows(name):
    with (ROOT / "output/csv" / f"{name}.csv").open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def numeric(value):
    return Literal(value, datatype=DECIMAL)


def q(s, p, o):
    return Quad(s, node(p), o)


def triples_canciones():
    for r in rows("canciones"):
        s = node("cancion/" + r["track_id"])
        yield Quad(s, TYPE, node("RegistroCancion"))
        for p, col in [
            ("trackId", "track_id"),
            ("titulo", "title"),
            ("creditoOriginal", "artist_name"),
        ]:
            yield q(s, p, Literal(r[col]))
        if r["recording_mbid"]:
            yield q(
                s, "grabacionReconciliada", node("grabacion/" + r["recording_mbid"])
            )


def triples_descriptores():
    for source, file in [
        ("jmir", "descriptores_acusticos"),
        ("acousticbrainz", "acousticbrainz"),
    ]:
        count = 0
        for r in rows(file):
            s = node("cancion/" + r["track_id"])
            fields = (
                [k for k in r if "_Overall_" in k]
                if source == "jmir"
                else [
                    "bpm",
                    "tonalidad",
                    "escala",
                    "fuerza_tonalidad",
                    "danceability",
                    "average_loudness",
                ]
            )
            for field in fields:
                if r[field] == "":
                    continue
                obs = node("observacion/" + source + "/" + r["track_id"] + "/" + field)
                yield q(s, "observacionAcustica", obs)
                yield q(obs, "descriptor", Literal(field))
                yield q(
                    obs,
                    "valor",
                    Literal(r[field])
                    if field in ["tonalidad", "escala"]
                    else numeric(r[field]),
                )
                yield q(obs, "fuente", node(source))
            count += 1
            if count % 20000 == 0:
                print(f"{source}: {count} canciones cargadas", flush=True)


def triples_grabaciones():
    for r in rows("grabaciones"):
        s = node("grabacion/" + r["recording_mbid"])
        yield Quad(s, TYPE, node("Grabacion"))
        yield q(s, "titulo", Literal(r["titulo"]))
    for r in rows("grabacion_lanzamiento"):
        yield q(
            node("grabacion/" + r["recording_mbid"]),
            "apareceEn",
            node("lanzamiento/" + r["release_mbid"]),
        )


def triples():
    yield from triples_canciones()
    yield from triples_descriptores()
    yield from triples_grabaciones()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo-consultar", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = STORE_PATH
    if not args.solo_consultar and path.exists():
        raise FileExistsError("Almacén existente: usar --solo-consultar")
    store = Store(str(path))
    started = time.monotonic()
    if not args.solo_consultar:
        store.bulk_extend(triples())
        store.flush()
        print(
            f"Carga terminada: {len(store):,} triples, {time.monotonic() - started:.1f} s",
            flush=True,
        )
    results = {}
    for query in sorted((ROOT / "exploraciones/sparql/consultas").glob("*.rq")):
        start = time.monotonic()
        answer = store.query(query.read_text())
        variables = [v.value for v in answer.variables]
        data = [
            {
                name: (solution[name].value if solution[name] is not None else None)
                for name in variables
            }
            for solution in answer
        ]
        results[query.stem] = data
        (OUT / (query.stem + ".json")).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            query.stem,
            len(data),
            "filas",
            round(time.monotonic() - start, 2),
            "s",
            json.dumps(data[:3], ensure_ascii=False),
            flush=True,
        )
    # Contrastar SPARQL con lecturas independientes de los CSV.
    original = next(
        r
        for r in rows("descriptores_acusticos")
        if r["track_id"] == "TRMMMCJ128F930BFF8"
    )
    first = results["01_descriptores_cancion"]
    assert len(first) == 16
    assert all(Decimal(r["valor"]) == Decimal(original[r["descriptor"]]) for r in first)
    counts = defaultdict(int)
    for r in rows("descriptores_acusticos"):
        for k, v in r.items():
            if "_Overall_" in k and v != "":
                counts[k] += 1
    assert {
        r["descriptor"]: int(r["cantidad"])
        for r in results["02_cobertura_descriptores"]
    } == dict(counts)
    fast = [r for r in rows("acousticbrainz") if r["bpm"] and Decimal(r["bpm"]) > 120]
    expected = sorted(fast, key=lambda r: (-Decimal(r["bpm"]), r["track_id"]))[:20]
    assert [
        (r["trackId"], Decimal(r["bpm"])) for r in results["03_tempo_mayor_120"]
    ] == [(r["track_id"], Decimal(r["bpm"])) for r in expected]
    rels = defaultdict(set)
    for r in rows("grabacion_lanzamiento"):
        rels[r["recording_mbid"]].add(r["release_mbid"])
    assert {
        r["grabacion"].rsplit("/", 1)[-1]: int(r["cantidad"])
        for r in results["04_varios_lanzamientos"]
    } == {k: len(v) for k, v in rels.items() if len(v) > 1}
    files = [
        "canciones",
        "descriptores_acusticos",
        "acousticbrainz",
        "grabaciones",
        "grabacion_lanzamiento",
    ]
    summary = {
        "motor": "pyoxigraph",
        "version": version("pyoxigraph"),
        "triples": len(store),
        "consultas_ejecutadas": len(results),
        "resultados_verificados_con_csv": True,
        "canciones_bpm_mayor_120": len(fast),
        "fuentes_sha256": {
            f: hashlib.sha256(
                (ROOT / "output/csv" / f"{f}.csv").read_bytes()
            ).hexdigest()
            for f in files
        },
        "segundos": round(time.monotonic() - started, 2),
    }
    (OUT / "resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
