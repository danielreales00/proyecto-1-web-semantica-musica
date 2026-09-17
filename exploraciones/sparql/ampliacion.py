"""Añade la expansión semántica al grafo experimental y verifica consultas contra CSV."""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from pyoxigraph import Literal, NamedNode, Quad, Store

sys.path.insert(0, str(Path(__file__).parent))
from ejecutar import OUT, STORE_PATH, TYPE, node, q, rows

ROOT = Path(__file__).resolve().parents[2]
LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


def triples_canciones():
    for s in rows("canciones"):
        song = node("cancion/" + s["track_id"])
        artist = node("artista/" + s["artist_mbid"])
        yield q(song, "artistaSuministrado", artist)
        if s["recording_mbid_dump"]:
            yield q(
                song,
                "grabacionDelVolcado",
                node("grabacion/" + s["recording_mbid_dump"]),
            )
        if s["grupo_lanzamiento_mbid"]:
            yield q(
                song,
                "grupoDelLanzamiento",
                node("grupo/" + s["grupo_lanzamiento_mbid"]),
            )


def triples_wikidata():
    for r in rows("wikidata_correspondencias"):
        if r["estado"] == "unica":
            yield q(
                node("artista/" + r["artist_mbid"]),
                "entidadWikidata",
                NamedNode("http://www.wikidata.org/entity/" + r["artista_qid"]),
            )
    for r in rows("wikidata_hechos"):
        obj = (
            NamedNode(r["valor"])
            if r["tipo_valor"] == "uri"
            else Literal(r["valor"], datatype=NamedNode(r["datatype"]))
            if r["datatype"]
            else Literal(r["valor"])
        )
        yield Quad(
            NamedNode("http://www.wikidata.org/entity/" + r["artista_qid"]),
            NamedNode("http://www.wikidata.org/prop/direct/" + r["propiedad"]),
            obj,
        )
    for r in rows("wikidata_entidades"):
        if r["etiqueta"]:
            yield Quad(
                NamedNode(r["entidad_uri"]),
                LABEL,
                Literal(r["etiqueta"], language=r["idioma"]),
            )


def triples_entidades_musicbrainz():
    for r in rows("artistas_masivos"):
        s = node("artista/" + r["artist_mbid"])
        yield q(s, "nombre", Literal(r["nombre"]))
        yield Quad(s, TYPE, node("Artista"))
    for r in rows("grabaciones_masivas"):
        s = node("grabacion/" + r["recording_mbid"])
        yield Quad(s, TYPE, node("Grabacion"))
        yield q(s, "tituloVolcado", Literal(r["titulo"]))
    for r in rows("obras_masivas"):
        s = node("obra/" + r["work_mbid"])
        yield Quad(s, TYPE, node("ObraMusical"))
        yield q(s, "titulo", Literal(r["titulo"]))


def triples_relaciones_musicales():
    for r in rows("relaciones_musicales_masivas"):
        if (
            r["sujeto_tipo"] == "grabacion"
            and r["objeto_tipo"] == "obra"
            and r["relacion"] == "performance"
        ):
            yield q(
                node("grabacion/" + r["sujeto_mbid"]),
                "interpretaObra",
                node("obra/" + r["objeto_mbid"]),
            )
        elif (
            r["sujeto_tipo"] == "artista"
            and r["objeto_tipo"] == "obra"
            and r["relacion"] == "composer"
        ):
            yield q(
                node("obra/" + r["objeto_mbid"]),
                "compositor",
                node("artista/" + r["sujeto_mbid"]),
            )


def triples_grupos_lanzamientos():
    for r in rows("grupos_lanzamientos"):
        s = node("grupo/" + r["grupo_lanzamiento_mbid"])
        yield q(s, "titulo", Literal(r["titulo"]))
        yield q(s, "tipoPrimario", Literal(r["tipo_primario"]))
    for r in rows("grupo_lanzamiento_genero"):
        yield q(
            node("grupo/" + r["grupo_lanzamiento_mbid"]),
            "generoGrupo",
            Literal(r["genero"]),
        )


def triples():
    yield from triples_canciones()
    yield from triples_wikidata()
    yield from triples_entidades_musicbrainz()
    yield from triples_relaciones_musicales()
    yield from triples_grupos_lanzamientos()


def consultar(store):
    answers = {}
    for path in sorted(
        (ROOT / "exploraciones/sparql/consultas_ampliacion").glob("*.rq")
    ):
        ans = store.query(path.read_text())
        cols = [v.value for v in ans.variables]
        data = [{c: r[c].value if r[c] is not None else "" for c in cols} for r in ans]
        (OUT / (path.stem + ".json")).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        )
        answers[path.stem] = data
        print(
            path.stem, len(data), json.dumps(data[:3], ensure_ascii=False), flush=True
        )
    return answers


def verificar_propiedades_artistas(answers, songs):
    # Contar canciones desde los CSV, sin duplicar caminos hacia una propiedad.
    facts = defaultdict(set)
    for r in rows("wikidata_hechos"):
        facts[r["artist_mbid"]].add(r["propiedad"])
    expected = defaultdict(set)
    for s in songs:
        for p in facts[s["artist_mbid"]]:
            if p != "P31":
                expected[p].add(s["track_id"])
    assert {
        r["propiedad"].rsplit("/", 1)[-1]: int(r["canciones"])
        for r in answers["05_propiedades_artistas"]
    } == {p: len(ids) for p, ids in expected.items()}


def verificar_compositores(answers, songs):
    rw = defaultdict(set)
    wc = defaultdict(set)
    for r in rows("relaciones_musicales_masivas"):
        if (
            r["sujeto_tipo"] == "grabacion"
            and r["objeto_tipo"] == "obra"
            and r["relacion"] == "performance"
        ):
            rw[r["sujeto_mbid"]].add(r["objeto_mbid"])
        if (
            r["sujeto_tipo"] == "artista"
            and r["objeto_tipo"] == "obra"
            and r["relacion"] == "composer"
        ):
            wc[r["objeto_mbid"]].add(r["sujeto_mbid"])
    bycomposer = defaultdict(set)
    for s in songs:
        for work in rw[s["recording_mbid_dump"]]:
            for composer in wc[work]:
                bycomposer[composer].add(s["track_id"])
    names = {r["artist_mbid"]: r["nombre"] for r in rows("artistas_masivos")}
    expected_top = sorted(bycomposer, key=lambda k: (-len(bycomposer[k]), names[k], k))[
        :10
    ]
    assert [
        (r["compositor"].rsplit("/", 1)[-1], int(r["canciones"]))
        for r in answers["06_compositores"]
    ] == [(k, len(bycomposer[k])) for k in expected_top]
    return len(set().union(*bycomposer.values()))


def verificar_generos_albumes(answers, songs):
    genres = defaultdict(set)
    for r in rows("grupo_lanzamiento_genero"):
        genres[r["grupo_lanzamiento_mbid"]].add(r["genero"])
    bygenre = defaultdict(set)
    for s in songs:
        for g in genres[s["grupo_lanzamiento_mbid"]]:
            bygenre[g].add(s["track_id"])
    top = sorted(bygenre, key=lambda g: (-len(bygenre[g]), g))[:10]
    assert [
        (r["genero"], int(r["canciones"])) for r in answers["07_generos_albumes"]
    ] == [(g, len(bygenre[g])) for g in top]


def main():
    store = Store(str(STORE_PATH))
    store.bulk_extend(triples())
    store.flush()
    answers = consultar(store)
    songs = list(rows("canciones"))
    verificar_propiedades_artistas(answers, songs)
    canciones_con_compositor = verificar_compositores(answers, songs)
    verificar_generos_albumes(answers, songs)
    files = [
        "canciones",
        "wikidata_hechos",
        "wikidata_correspondencias",
        "wikidata_entidades",
        "artistas_masivos",
        "grabaciones_masivas",
        "obras_masivas",
        "relaciones_musicales_masivas",
        "grupos_lanzamientos",
        "grupo_lanzamiento_genero",
    ]
    result = {
        "triples_tras_ampliacion": len(store),
        "consultas_ejecutadas": 3,
        "resultados_verificados_con_csv": True,
        "canciones_con_compositor": canciones_con_compositor,
        "fuentes_sha256": {
            f: hashlib.sha256(
                (ROOT / "output/csv" / f"{f}.csv").read_bytes()
            ).hexdigest()
            for f in files
        },
    }
    (OUT / "resumen_ampliacion.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
