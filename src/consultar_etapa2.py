"""Ejecuta las ocho preguntas de competencia y guarda JSON, CSV y métricas."""

import csv
import json
from datetime import datetime, timezone
from time import perf_counter

import requests

from configuracion import QUERY_URL
from musica.comun.rutas import ROOT
from musica.etapa2.escritura import sha_archivo


def main():
    salida = ROOT / "output/etapa2/consultas"
    salida.mkdir(parents=True, exist_ok=True)
    resumen = {
        "endpoint": QUERY_URL,
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "inferencia": "ninguna; triples explícitos",
        "consultas": [],
    }
    for ruta in sorted((ROOT / "consultas/etapa2").glob("*.rq")):
        inicio = perf_counter()
        respuesta = requests.post(
            QUERY_URL,
            data={"query": ruta.read_text()},
            headers={"Accept": "application/sparql-results+json"},
            timeout=(10, 600),
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        (salida / (ruta.stem + ".json")).write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
        )
        variables = datos["head"]["vars"]
        filas = datos["results"]["bindings"]
        with (salida / (ruta.stem + ".csv")).open(
            "w", newline="", encoding="utf-8"
        ) as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=variables)
            escritor.writeheader()
            escritor.writerows(
                {v: fila.get(v, {}).get("value", "") for v in variables}
                for fila in filas
            )
        resultado = {
            "consulta": ruta.name,
            "sha256": sha_archivo(ruta),
            "filas": len(filas),
            "segundos": round(perf_counter() - inicio, 3),
            "http": respuesta.status_code,
        }
        resumen["consultas"].append(resultado)
        print(resultado, flush=True)
    (salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
