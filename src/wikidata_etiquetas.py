"""Nombres legibles para entidades objeto; conserva idioma y evidencia de consulta."""

import argparse
import csv
import hashlib
import json
import os

from musica.comun.archivos_csv import escribir_csv
from musica.comun.rutas import ROOT
from musicbrainz import Cliente


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    a = p.parse_args()
    facts = list(csv.DictReader((ROOT / "data/processed/wikidata_hechos.csv").open()))
    ids = sorted(
        {
            f["valor"].rsplit("/", 1)[-1]
            for f in facts
            if f["tipo_valor"] == "uri"
            and f["valor"].startswith("http://www.wikidata.org/entity/Q")
        }
    )
    folder = ROOT / "data/raw/wikidata_etiquetas"
    folder.mkdir(exist_ok=True)
    c = Cliente(a.offline)
    c.session.headers["User-Agent"] = os.environ.get(
        "WIKIDATA_USER_AGENT", "ProyectoEtapa1MISIS/1.1 (academic research)"
    )
    rows = []
    for i in range(0, len(ids), 200):
        batch = ids[i : i + 200]
        q = (
            "PREFIX wd: <http://www.wikidata.org/entity/> SELECT ?entidad ?etiqueta WHERE { VALUES ?entidad { "
            + " ".join("wd:" + x for x in batch)
            + ' } ?entidad <http://www.w3.org/2000/01/rdf-schema#label> ?etiqueta . FILTER(LANG(?etiqueta) IN ("es","en")) }'
        )
        key = hashlib.sha256(q.encode()).hexdigest()
        path = folder / (key + ".json")
        if path.exists():
            env = json.loads(path.read_text())
        else:
            if a.offline:
                raise FileNotFoundError(path)
            env = c.get(
                "https://query.wikidata.org/sparql", {"query": q, "format": "json"}
            )
            if env["status"] != 200 or "results" not in env["data"]:
                raise RuntimeError("Respuesta incompleta de etiquetas")
            env = {**env, "consulta": q, "sha256_consulta": key}
            path.write_text(json.dumps(env, ensure_ascii=False))
        labels = {}
        for b in env["data"]["results"]["bindings"]:
            qid = b["entidad"]["value"].rsplit("/", 1)[-1]
            lang = b["etiqueta"]["xml:lang"]
            value = b["etiqueta"]["value"]
            labels.setdefault(qid, {})[lang] = value
        for qid in batch:
            choices = labels.get(qid, {})
            lang = "es" if choices.get("es") else "en" if choices.get("en") else ""
            rows.append(
                {
                    "entidad_qid": qid,
                    "entidad_uri": "http://www.wikidata.org/entity/" + qid,
                    "etiqueta": choices.get(lang, ""),
                    "idioma": lang,
                    "fuente_id": "wikidata",
                    "consulta_sha256": key,
                    "fecha_consulta": env["fecha_utc"],
                }
            )
        print(f"Etiquetas {min(i + 200, len(ids))}/{len(ids)}", flush=True)
    escribir_csv(ROOT / "data/processed/wikidata_etiquetas.csv", rows)
    print(
        json.dumps(
            {
                "entidades": len(rows),
                "con_etiqueta": sum(bool(r["etiqueta"]) for r in rows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
