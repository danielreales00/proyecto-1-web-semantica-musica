"""Reconstruye resultados parciales y valida evidencia sin acceder a la red."""

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from unittest.mock import patch

from diagnostico import ROOT
from musicbrainz import Cliente, evaluar, solicitud_grabacion


def evidencia(env):
    key = hashlib.sha256(env["url"].encode()).hexdigest()
    raw = json.loads((ROOT / "data/raw/api" / f"{key}.json").read_text())
    assert raw["url"] == env["url"] and raw["status"] == env["status"]
    return raw


def auditar_detalles(client, item, chosen, candidates):
    if chosen:
        assert {r["recording_mbid"] for r in candidates if r["elegible"]} == {chosen}
        for label, url, params in [
            (
                "detalle",
                f"https://musicbrainz.org/ws/2/recording/{chosen}",
                {
                    "fmt": "json",
                    "inc": "artists+releases+isrcs+genres+work-rels+artist-rels+work-level-rels",
                },
            ),
            (
                "acousticbrainz",
                f"https://acousticbrainz.org/api/v1/{chosen}/low-level",
                None,
            ),
        ]:
            try:
                result = client.get(url, params)
            except FileNotFoundError:
                item[label] = "pendiente_consulta"
                continue
            source = evidencia(result)
            item[label] = (
                "sin_datos_en_lote_200"
                if result.get("sin_datos")
                else str(result["status"])
            )
            item[label + "_evidencia"] = result
            if result["status"] == 200:
                if label == "detalle":
                    assert result["data"]["id"] == chosen
                elif result.get("datos_derivados_de_lote"):
                    normalized = (
                        source["data"].get("mbid_mapping", {}).get(chosen, chosen)
                    )
                    original = source["data"].get(normalized, {}).get("0")
                    assert (original is None) == bool(result.get("sin_datos"))
                    assert result["data"] == (original or {})
                else:
                    assert result["data"] == source["data"]


def main():
    client = Cliente(offline=True)
    rows = list(csv.DictReader((ROOT / "data/processed/piloto_1000.csv").open()))
    base = {
        r["track_id"]: r
        for r in csv.DictReader((ROOT / "grupo_2.csv").open(encoding="utf-8-sig"))
    }
    assert len(rows) == len({r["track_id"] for r in rows}) == 1000
    output = []
    for row in rows:
        assert all(row[k] == v for k, v in base[row["track_id"]].items())
        item = {
            "cancion": row,
            "estado": "pendiente_consulta",
            "recording_mbid": "",
            "detalle": "no_aplica",
            "acousticbrainz": "no_aplica",
        }
        try:
            env = client.get(*solicitud_grabacion(row))
        except FileNotFoundError:
            output.append(item)
            continue
        raw = evidencia(env)
        if env["status"] != 200:
            item["estado"] = "error_consulta"
            output.append(item)
            continue
        assert raw["data"].get("count", 0) <= 100 or not env.get(
            "datos_derivados_de_lote"
        )
        records = env["data"].get("recordings", [])
        source_records = {r["id"]: r for r in raw["data"].get("recordings", [])}
        assert all(r == source_records[r["id"]] for r in records)
        if env["data"].get("count", 0) > 100:
            status, chosen, candidates = "candidatos_truncados", "", []
        else:
            status, chosen, candidates = evaluar(row, records)
        item.update(
            estado=status,
            recording_mbid=chosen,
            candidatos=candidates,
            url_evidencia=env["url"],
            fecha_consulta=env["fecha_utc"],
        )
        auditar_detalles(client, item, chosen, candidates)
        output.append(item)
    accepted = [r for r in output if r["estado"] == "aceptada"]
    summary = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "modo": "solo_cache_sin_red",
        "piloto_completo": False,
        "canciones": len(rows),
        "estados": dict(Counter(r["estado"] for r in output)),
        "detalles_entre_aceptadas": dict(Counter(r["detalle"] for r in accepted)),
        "acousticbrainz_entre_aceptadas": dict(
            Counter(r["acousticbrainz"] for r in accepted)
        ),
        "integridad_campos_originales": True,
        "evidencia_raw_verificada": True,
    }
    folder = ROOT / "output/piloto_musicbrainz_parcial"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "resultados_cache.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    (ROOT / "docs/auditoria_cache_musicbrainz.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    with patch(
        "requests.sessions.Session.request",
        side_effect=AssertionError("Auditoría sin acceso a red"),
    ):
        main()
