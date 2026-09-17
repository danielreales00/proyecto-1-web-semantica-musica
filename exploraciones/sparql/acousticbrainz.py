"""Consulta real sobre el volcado acústico; validación independiente con los CSV."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from pyoxigraph import Literal, Store

from ejecutar import OUT, ROOT, STORE_PATH, node, numeric, q, rows


def main():
    meta = json.loads((ROOT / "docs/ampliacion_acousticbrainz.json").read_text())
    records = list(rows("acousticbrainz_masivo"))
    songs = list(rows("canciones"))
    store = Store(str(STORE_PATH))

    def triples():
        for s in songs:
            if s["recording_mbid_dump"]:
                yield q(
                    node("cancion/" + s["track_id"]),
                    "grabacionDelVolcado",
                    node("grabacion/" + s["recording_mbid_dump"]),
                )
        for r in records:
            analysis = node("analisis/acousticbrainz2022/" + r["recording_mbid"] + "/0")
            yield q(
                node("grabacion/" + r["recording_mbid"]),
                "analisisAcousticBrainz",
                analysis,
            )
            yield q(analysis, "fuente", node("acousticbrainz_dump"))
            yield q(analysis, "submissionOffset", numeric("0"))
            for key in meta["campos_caracteristicas"]:
                if r[key]:
                    yield q(
                        analysis,
                        key,
                        Literal(r[key])
                        if key in ("key_key", "key_scale")
                        else numeric(r[key]),
                    )

    store.bulk_extend(triples())
    store.flush()
    path = Path(__file__).parent / "consultas_acousticbrainz/08_tonalidades_volcado.rq"
    answers = store.query(path.read_text())
    names = [v.value for v in answers.variables]
    result = [{name: row[name].value for name in names} for row in answers]
    index = {r["recording_mbid"]: r for r in records}
    counts = Counter(
        (
            index[s["recording_mbid_dump"]]["key_key"],
            index[s["recording_mbid_dump"]]["key_scale"],
        )
        for s in songs
        if s["recording_mbid_dump"] in index
        and index[s["recording_mbid_dump"]]["key_key"]
        and index[s["recording_mbid_dump"]]["key_scale"]
    )
    expected = sorted(counts.items(), key=lambda item: (-item[1], *item[0]))[:10]
    assert [(r["tonalidad"], r["escala"], int(r["canciones"])) for r in result] == [
        (k[0], k[1], v) for k, v in expected
    ]
    covered = sum(s["recording_mbid_dump"] in index for s in songs)
    assert covered == meta["canciones_con_datos"]
    check = list(
        store.query(
            "PREFIX mus: <https://example.org/musica/> SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {?c mus:grabacionDelVolcado/mus:analisisAcousticBrainz ?a}"
        )
    )
    assert int(check[0]["n"].value) == covered
    (OUT / (path.stem + ".json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    summary = {
        "triples_tras_ampliacion_acustica": len(store),
        "consultas_ejecutadas": 1,
        "resultados_verificados_con_csv": True,
        "canciones_con_datos": covered,
        "canciones_con_tonalidad_y_escala": sum(counts.values()),
        "fuentes_sha256": {
            name: hashlib.sha256(
                (ROOT / "output/csv" / (name + ".csv")).read_bytes()
            ).hexdigest()
            for name in ["canciones", "acousticbrainz_masivo"]
        },
    }
    (OUT / "resumen_acousticbrainz.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"resultados": result, **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
