"""Vincula características publicadas de AcousticBrainz con las grabaciones aceptadas."""

import csv
import json
from collections import Counter
from decimal import Decimal

from descargar_acousticbrainz_dump import KINDS, sha
from diagnostico import ROOT, escribir_csv
from extraer_acousticbrainz_dump import EXPECTED, OUT


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def leer_analisis_familia(source, info, ids, columns, kind, merged, lines, conflicting):
    keys = set()
    canonical = {}
    scanned = duplicates = 0
    with source.open() as stream:
        for raw in stream:
            scanned += 1
            record = json.loads(raw)
            r = record["valores"]
            mid, offset = r["mbid"], int(r["submission_offset"])
            assert mid in ids and offset >= 0
            assert 2 <= record["linea"] <= EXPECTED + 1
            assert record["archivo_interno"] == info["archivo_interno"]
            assert set(r) == set(info["columnas"])
            if (mid, offset) in keys:
                duplicates += 1
            keys.add((mid, offset))
            if offset == 0:
                fingerprint = tuple(r[k] for k in columns)
                if mid in canonical:
                    if canonical[mid] != fingerprint:
                        conflicting.add(mid)
                    continue
                canonical[mid] = fingerprint
                for k in columns:
                    value = r[k]
                    if value and k not in ("key_key", "key_scale"):
                        assert Decimal(value).is_finite(), (mid, k, value)
                merged.setdefault(mid, {}).update({k: r[k] for k in columns})
                lines.setdefault(mid, {})[kind] = record["linea"]
    assert scanned == info["filas_vinculadas"]
    assert duplicates == info["claves_mbid_offset_repetidas"]
    return keys, duplicates


def comparar_piloto(pilot, merged):
    compared = mismatches = 0
    for row in pilot:
        if row["recording_mbid"] not in merged:
            continue
        values = merged[row["recording_mbid"]]
        for old, new in [
            ("bpm", "bpm"),
            ("tonalidad", "key_key"),
            ("escala", "key_scale"),
            ("danceability", "danceability"),
            ("average_loudness", "average_loudness"),
        ]:
            compared += 1
            if old in ("tonalidad", "escala"):
                mismatches += row[old] != values[new]
            else:
                mismatches += abs(Decimal(row[old]) - Decimal(values[new])) > Decimal(
                    "0.000001"
                )
    return compared, mismatches


def main():
    meta = json.loads((OUT / "extraccion.json").read_text())
    dest = ROOT / "output/ampliacion"
    assert sha(ROOT / "grupo_2.csv") == meta["sha256_entrada"]
    assert sha(dest / "grabaciones_masivas.csv") == meta["sha256_grabaciones_objetivo"]
    ids = {r["recording_mbid"] for r in read(dest / "grabaciones_masivas.csv")}
    merged, counts, lines, features = {}, {}, {}, []
    conflicting = set()
    duplicate_counts = {}
    expected_keys = None
    for kind in KINDS:
        info = meta["fuentes"][kind]
        source = OUT / info["subconjunto_archivo"]
        assert info["recorrido_completo"] and info["filas_recorridas"] == EXPECTED
        assert sha(source) == info["subconjunto_sha256"]
        columns = info["columnas"][2:]
        assert not set(columns) & set(features)
        features.extend(columns)
        keys, duplicates = leer_analisis_familia(
            source, info, ids, columns, kind, merged, lines, conflicting
        )
        duplicate_counts[kind] = duplicates
        if expected_keys is not None:
            assert keys == expected_keys, (
                "Los tres archivos deben describir las mismas entregas."
            )
        else:
            expected_keys = keys
            counts = Counter(mid for mid, _ in keys)
    missing_zero = {mid for mid in counts if (mid, 0) not in expected_keys}
    for mid in conflicting | missing_zero:
        merged.pop(mid, None)
    records = []
    for mid, values in sorted(merged.items()):
        assert set(values) == set(features)
        row = {
            "recording_mbid": mid,
            "submission_offset": 0,
            "analisis_disponibles": counts[mid],
            **values,
            "fuente_id": "acousticbrainz_dump",
            "fecha_snapshot": "20220623",
            "metodo": "MBID_exacto+submission_offset_0_sin_promediar",
        }
        for kind in KINDS:
            info = meta["fuentes"][kind]
            row.update(
                {
                    f"url_{kind}": info["url"],
                    f"archivo_interno_{kind}": info["archivo_interno"],
                    f"sha256_{kind}": info["sha256"],
                    f"linea_{kind}": lines[mid][kind],
                }
            )
        records.append(row)
    songs = read(dest / "canciones.csv")
    decisions, states = [], Counter()
    evidence_sha = sha(OUT / "extraccion.json")
    for song in songs:
        mid = song["recording_mbid_dump"]
        state = (
            "disponible"
            if mid in merged
            else "conflicto_analisis_cero"
            if mid in conflicting
            else "sin_analisis_cero"
            if mid in missing_zero
            else "sin_datos_en_volcado"
            if mid
            else "sin_grabacion_reconciliada"
        )
        sources = [
            v
            for v in song["fuentes_enriquecimiento"].split("|")
            if v and v != "acousticbrainz_dump"
        ]
        if state == "disponible":
            sources.append("acousticbrainz_dump")
        song.update(
            estado_acousticbrainz_dump=state,
            fuentes_enriquecimiento="|".join(sources),
            enriquecida=bool(sources),
        )
        decisions.append(
            {
                "track_id": song["track_id"],
                "recording_mbid": mid,
                "estado": state,
                "submission_offset": 0 if state == "disponible" else "",
                "analisis_disponibles": counts.get(mid, 0),
                "fuente_id": "acousticbrainz_dump",
                "fecha_snapshot": "20220623",
                "evidencia_extraccion_sha256": evidence_sha,
            }
        )
        states[state] += 1
    pilot = read(ROOT / "output/csv/acousticbrainz.csv")
    compared, mismatches = comparar_piloto(pilot, merged)
    escribir_csv(dest / "acousticbrainz_masivo.csv", records)
    escribir_csv(dest / "acousticbrainz_correspondencias_masivas.csv", decisions)
    escribir_csv(dest / "canciones.csv", songs)
    pilot_ids = {r["track_id"] for r in pilot}
    covered = {r["track_id"] for r in decisions if r["estado"] == "disponible"}
    summary = {
        "fecha_snapshot": "20220623",
        "canciones_evaluadas": len(songs),
        "grabaciones_objetivo": len(ids),
        "grabaciones_con_datos": len(records),
        "analisis_vinculados": len(expected_keys),
        "campos_caracteristicas": features,
        "filas_con_clave_repetida_por_familia": duplicate_counts,
        "mbid_con_conflicto_analisis_cero": sorted(conflicting),
        "mbid_sin_analisis_cero": sorted(missing_zero),
        "numero_caracteristicas": len(features),
        "estados": dict(states),
        "canciones_con_datos": len(covered),
        "canciones_piloto_con_datos": len(pilot_ids),
        "canciones_adicionales_al_piloto": len(covered - pilot_ids),
        "canciones_piloto_sin_datos_en_volcado": len(pilot_ids - covered),
        "comparaciones_valores_piloto": compared,
        "discrepancias_valores_piloto": mismatches,
        "canciones_bpm_mayor_120": sum(
            s["recording_mbid_dump"] in merged
            and Decimal(merged[s["recording_mbid_dump"]]["bpm"]) > 120
            for s in songs
        ),
        "valores_no_vacios_grabaciones": sum(
            bool(v) for r in merged.values() for v in r.values()
        ),
        "bytes_comprimidos": sum(i["bytes"] for i in meta["fuentes"].values()),
        "filas_por_archivo": EXPECTED,
        "sha256_oficiales_verificados": True,
        "politica_analisis": "submission_offset=0, sin promediar ni combinar offsets",
        "limitaciones": [
            "Snapshot 2022; MBID exacto, sin resolver redirecciones posteriores.",
            "No se conoce la duración ni calidad del audio desde estos CSV compactos.",
            "Selección reproducible de un análisis, no certificación de calidad acústica.",
            "14 características seleccionadas oficialmente; no todos los campos JSON.",
        ],
    }
    (ROOT / "docs/ampliacion_acousticbrainz.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
