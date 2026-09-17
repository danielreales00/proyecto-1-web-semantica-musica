"""Consolida toda la caché del piloto; no consulta servicios ni declara completitud."""

import json
from collections import Counter

from auditar_cache_musicbrainz import evidencia
from diagnostico import ROOT, normalizar
from musicbrainz import Cliente, exportar, solicitud_artista


def main():
    rows = json.loads(
        (ROOT / "output/piloto_musicbrainz_parcial/resultados_cache.json").read_text()
    )
    client = Cliente(offline=True)
    results = []
    artists = {}
    candidates = []
    details = []
    acoustic = []
    for item in rows:
        row = item["cancion"]
        tid = row["track_id"]
        mid = row["artist_mbid"]
        try:
            a = client.get(*solicitud_artista(mid))
        except FileNotFoundError:
            a = None
        ad = a["data"] if a and a["status"] == 200 else {}
        if a:
            evidencia(a)
            artists[mid] = {
                "artist_mbid_suministrado": mid,
                "artist_mbid_actual": ad.get("id", ""),
                "nombre": ad.get("name", ""),
                "tipo": ad.get("type", ""),
                "pais": ad.get("country", ""),
                "area": (ad.get("area") or {}).get("name", ""),
                "inicio": ad.get("life-span", {}).get("begin", ""),
                "fin": ad.get("life-span", {}).get("end", ""),
                "generos": "|".join(g["name"] for g in ad.get("genres", [])),
                "fuente_id": "musicbrainz",
                "url_evidencia": a["url"],
                "fecha_consulta": a["fecha_utc"],
                "status_http": a["status"],
                "tipo_consulta": "busqueda_lote"
                if a.get("datos_derivados_de_lote")
                else "consulta_individual",
                "etiquetas": "|".join(t["name"] for t in ad.get("tags", [])),
            }
        names = {normalizar(ad.get("name", ""))} | {
            normalizar(x["name"]) for x in ad.get("aliases", [])
        }
        result = {
            "track_id": tid,
            "artist_mbid_suministrado": mid,
            "nombre_artista_validado": normalizar(row["artist_name"]) in names,
            "estado": item["estado"],
            "recording_mbid": item["recording_mbid"],
            "candidatos": len(item.get("candidatos", [])),
            "fuente_id": "musicbrainz",
            "metodo": "titulo_exacto+mbid_artista+album_exacto+duracion_3s+candidato_unico",
            "url_evidencia": item.get("url_evidencia", ""),
            "fecha_consulta": item.get("fecha_consulta", ""),
            "estado_detalle": item["detalle"],
            "estado_acousticbrainz": item["acousticbrainz"],
        }
        results.append(result)
        for c in item.get("candidatos", []):
            candidates.append(
                {"track_id": tid, **c, "url_evidencia": item["url_evidencia"]}
            )
        if "detalle_evidencia" in item:
            details.append({"track_id": tid, **item["detalle_evidencia"]})
        if "acousticbrainz_evidencia" in item:
            acoustic.append(
                {
                    "track_id": tid,
                    "recording_mbid": item["recording_mbid"],
                    **item["acousticbrainz_evidencia"],
                }
            )
    exportar(results, artists, candidates, details, acoustic)
    summary = {
        "alcance": "piloto parcial consolidado desde caché",
        "canciones_objetivo": len(rows),
        "canciones_con_estado": len(results),
        "completo": False,
        "estados": dict(Counter(r["estado"] for r in results)),
        "detalles_recuperados": len(details),
        "detalles_pendientes": sum(
            r["estado_detalle"] == "pendiente_consulta" for r in results
        ),
        "artistas_con_respuesta": len(artists),
        "acousticbrainz": dict(
            Counter(
                r["estado_acousticbrainz"] for r in results if r["estado"] == "aceptada"
            )
        ),
    }
    (ROOT / "docs/consolidacion_piloto.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
