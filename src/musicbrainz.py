"""Piloto complementario MusicBrainz/AcousticBrainz, con evidencia por consulta.
No convierte un MBID de artista en identidad de grabación ni acepta empates.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

from musica.comun.archivos_csv import escribir_csv
from musica.comun.normalizacion import normalizar
from musica.comun.rutas import ROOT


def espera_reintento(value, attempt):
    if value:
        try:
            return max(2 ** (attempt + 1), float(value))
        except ValueError:
            try:
                return max(
                    2 ** (attempt + 1),
                    (
                        parsedate_to_datetime(value) - datetime.now(timezone.utc)
                    ).total_seconds(),
                )
            except (ValueError, TypeError):
                pass
    return 2 ** (attempt + 1)


class ServicioPausado(RuntimeError):
    """Interrumpe el piloto sin convertir un fallo del servicio en ausencia de datos."""


class Cliente:
    def __init__(self, offline=False):
        self.last_by_host = {}
        self.intervals = {}
        self.offline = offline
        self.session = requests.Session()
        self.session.headers["User-Agent"] = os.environ.get(
            "MUSICBRAINZ_USER_AGENT",
            "ProyectoEtapa1MISIS/1.0 (academic research; local reproducible pilot)",
        )
        self.cache = ROOT / "data/raw/api"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.derived = ROOT / "data/processed/api_derivadas"
        self.derived.mkdir(parents=True, exist_ok=True)
        self.state_dir = ROOT / "data/processed/estado_servicios"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def pausa(self, host, url, status, retry_after=None, body="", headers=None):
        # Fallar pronto: no saltar a otra canción ni volver a consultar en otro reinicio.
        delay = max(300, espera_reintento(retry_after, 0))
        state = {
            "host": host,
            "url": url,
            "status": status,
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "no_consultar_antes_epoch": time.time() + delay,
            "retry_after": retry_after,
            "respuesta": body[:2000],
            "headers": headers or {},
        }
        path = self.state_dir / f"{host}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        tmp.replace(path)
        with (self.state_dir / "errores.jsonl").open("a") as log:
            log.write(json.dumps(state, ensure_ascii=False) + "\n")
        raise ServicioPausado(
            f"{host}: HTTP {status}; ejecución detenida. Esperar al menos {delay:.0f} s antes de reanudar manualmente. Caché conservada."
        )

    def get(self, url, params=None):
        request = requests.Request("GET", url, params=params).prepare()
        key = hashlib.sha256(request.url.encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
        derived = self.derived / path.name
        if derived.exists():
            return json.loads(derived.read_text())
        if self.offline:
            raise FileNotFoundError(f"Consulta sin caché: {request.url}")
        host = urlsplit(request.url).netloc
        state_path = self.state_dir / f"{host}.json"
        if state_path.exists():
            remaining = (
                json.loads(state_path.read_text())["no_consultar_antes_epoch"]
                - time.time()
            )
            if remaining > 0:
                raise ServicioPausado(
                    f"{host}: pausa vigente; faltan {remaining:.0f} s. No se envió la consulta."
                )
        interval = self.intervals.get(host, 2.0)
        time.sleep(
            max(0, interval - (time.monotonic() - self.last_by_host.get(host, 0)))
        )
        self.last_by_host[host] = time.monotonic()
        try:
            r = self.session.get(request.url, timeout=(10, 25))
            if r.status_code in (429, 500, 502, 503, 504):
                self.pausa(
                    host,
                    request.url,
                    r.status_code,
                    r.headers.get("Retry-After"),
                    r.text,
                    dict(r.headers),
                )
            try:
                data = r.json()
            except ValueError:
                data = {"respuesta_no_json": r.text[:300]}
            result = {
                "url": request.url,
                "fecha_utc": datetime.now(timezone.utc).isoformat(),
                "status": r.status_code,
                "headers": dict(r.headers),
                "data": data,
            }
            if r.status_code in (200, 404):
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(result, ensure_ascii=False))
                tmp.replace(path)
            return result
        except requests.RequestException as e:
            self.pausa(host, request.url, 0, body=f"{type(e).__name__}: {e}")


def solicitud_artista(mbid):
    return f"https://musicbrainz.org/ws/2/artist/{mbid}", {
        "fmt": "json",
        "inc": "aliases+genres+url-rels",
    }


def solicitud_grabacion(row):
    query = f'arid:{row["artist_mbid"]} AND recording:"{escapar(row["title"])}"'
    return "https://musicbrainz.org/ws/2/recording", {
        "query": query,
        "fmt": "json",
        "limit": 100,
    }


def clave_solicitud(url, params):
    url = requests.Request("GET", url, params=params).prepare().url
    return hashlib.sha256(url.encode()).hexdigest(), url


def disponible(client, request):
    key, _ = clave_solicitud(*request)
    return (client.cache / f"{key}.json").exists() or (
        client.derived / f"{key}.json"
    ).exists()


def guardar_derivada(client, request, envelope, data):
    key, logical = clave_solicitud(*request)
    # La URL de evidencia sigue siendo la consulta realmente ejecutada.
    derived = {
        **envelope,
        "data": data,
        "datos_derivados_de_lote": True,
        "solicitud_logica_no_ejecutada": logical,
    }
    path = client.derived / f"{key}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(derived, ensure_ascii=False))
    tmp.replace(path)


def precargar_artistas(client, selected):
    ids = sorted(
        {
            r["artist_mbid"]
            for r in selected
            if not disponible(client, solicitud_artista(r["artist_mbid"]))
        }
    )
    for i in range(0, len(ids), 40):
        batch = ids[i : i + 40]
        env = client.get(
            "https://musicbrainz.org/ws/2/artist",
            {"query": "arid:(" + " OR ".join(batch) + ")", "fmt": "json", "limit": 100},
        )
        if env["status"] == 200 and env["data"].get("count", 0) <= 100:
            for artist in env["data"].get("artists", []):
                if artist["id"] in batch:
                    guardar_derivada(
                        client, solicitud_artista(artist["id"]), env, artist
                    )
        # Un identificador ausente puede estar fusionado: después se consulta individualmente.
        print(f"Precarga de artistas: {min(i + 40, len(ids))}/{len(ids)}", flush=True)


def buscar_lote_grabaciones(client, batch):
    if len(batch) == 1:
        return  # La consulta individual se ejecutará en el bucle principal.
    query = " OR ".join("(" + solicitud_grabacion(r)[1]["query"] + ")" for r in batch)
    env = client.get(
        "https://musicbrainz.org/ws/2/recording",
        {"query": query, "fmt": "json", "limit": 100},
    )
    if env["status"] != 200:
        return
    if env["data"].get("count", 0) > 100:
        middle = len(batch) // 2
        buscar_lote_grabaciones(client, batch[:middle])
        buscar_lote_grabaciones(client, batch[middle:])
        return
    # La consulta completa no está truncada. Todos los candidatos de cada cláusula
    # están en su unión. Filtramos por MBID; evaluar exige además título exacto.
    records = env["data"].get("recordings", [])
    for row in batch:
        subset = [
            rec
            for rec in records
            if row["artist_mbid"]
            in {
                c.get("artist", {}).get("id")
                for c in rec.get("artist-credit", [])
                if isinstance(c, dict)
            }
        ]
        guardar_derivada(
            client,
            solicitud_grabacion(row),
            env,
            {
                "count": len(subset),
                "recordings": subset,
                "total_consulta_lote": env["data"].get("count", 0),
            },
        )


def precargar(client, selected):
    precargar_artistas(client, selected)
    pending = [r for r in selected if not disponible(client, solicitud_grabacion(r))]

    for i in range(0, len(pending), 10):
        buscar_lote_grabaciones(client, pending[i : i + 10])
        print(
            f"Precarga de búsquedas: {min(i + 10, len(pending))}/{len(pending)}",
            flush=True,
        )


def precargar_acustica(client, selected):
    accepted = set()
    for row in selected:
        response = client.get(*solicitud_grabacion(row))
        if response["status"] != 200 or response["data"].get("count", 0) > 100:
            continue
        status, chosen, _ = evaluar(row, response["data"].get("recordings", []))
        if status == "aceptada":
            accepted.add(chosen)
    ids = sorted(
        mid
        for mid in accepted
        if not disponible(
            client, (f"https://acousticbrainz.org/api/v1/{mid}/low-level", None)
        )
    )
    for i in range(0, len(ids), 25):
        batch = ids[i : i + 25]
        env = client.get(
            "https://acousticbrainz.org/api/v1/low-level",
            {"recording_ids": ";".join(batch)},
        )
        if env["status"] != 200:
            continue
        for mid in batch:
            normalized = env["data"].get("mbid_mapping", {}).get(mid, mid)
            data = env["data"].get(normalized, {}).get("0")
            # Ausencia en un lote HTTP 200 no es un HTTP 404: conservar ambos conceptos.
            result = {**env, "sin_datos": data is None}
            guardar_derivada(
                client,
                (f"https://acousticbrainz.org/api/v1/{mid}/low-level", None),
                result,
                data or {},
            )
        print(
            f"Precarga AcousticBrainz: {min(i + 25, len(ids))}/{len(ids)} grabaciones",
            flush=True,
        )


def estado_acustico(env):
    return "sin_datos_en_lote_200" if env.get("sin_datos") else str(env["status"])


def escapar(s):
    return re.sub(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)', r"\\\1", s)


def evaluar(row, records):
    candidatos = []
    for rec in records:
        title = normalizar(rec.get("title", ""))
        artist_ids = {
            a.get("artist", {}).get("id")
            for a in rec.get("artist-credit", [])
            if isinstance(a, dict)
        }
        delta = (
            abs(rec["length"] / 1000 - float(row["duration"]))
            if rec.get("length")
            else None
        )
        album = any(
            normalizar(r.get("title", "")) == normalizar(row["release"])
            for r in rec.get("releases", [])
        )
        exact = title == normalizar(row["title"])
        artist = row["artist_mbid"] in artist_ids
        # Exigimos duración cercana Y álbum exacto: identidad de grabación conservadora.
        eligible = exact and artist and delta is not None and delta <= 3 and album
        score = round(
            0.45 * SequenceMatcher(None, title, normalizar(row["title"])).ratio()
            + 0.25 * artist
            + 0.15 * album
            + 0.15 * (delta is not None and delta <= 3),
            4,
        )
        candidatos.append(
            {
                "recording_mbid": rec["id"],
                "titulo": rec.get("title", ""),
                "titulo_exacto": exact,
                "artista_mbid_presente": artist,
                "album_exacto": album,
                "diferencia_duracion_s": round(delta, 3) if delta is not None else "",
                "elegible": eligible,
                "puntaje": score,
            }
        )
    candidatos.sort(key=lambda x: (-x["puntaje"], x["recording_mbid"]))
    accepted = {c["recording_mbid"] for c in candidatos if c["elegible"]}
    return (
        (
            "aceptada"
            if len(accepted) == 1
            else "ambigua"
            if len(accepted) > 1
            else "sin_coincidencia_conservadora"
        ),
        (next(iter(accepted)) if len(accepted) == 1 else ""),
        candidatos,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, default=1000)
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    started = time.monotonic()
    rows = list(csv.DictReader((ROOT / "data/processed/piloto_1000.csv").open()))
    # Selección uniforme determinista dentro del piloto ya estratificado.
    import random

    selected = random.Random(20260917).sample(rows, min(args.limite, len(rows)))
    client = Cliente(args.offline)
    results = []
    artists = {}
    candidates = []
    details = []
    acoustic = []
    precargar(client, selected)
    precargar_acustica(client, selected)

    def guardar(completo=False):
        exportar(results, artists, candidates, details, acoustic)
        resumen = {
            "canciones_objetivo": len(selected),
            "canciones_procesadas": len(results),
            "completo": completo,
            "estados": dict(Counter(r["estado"] for r in results)),
            "artistas_consultados": len(artists),
            "detalles_grabacion": len(details),
            "estados_detalles": dict(Counter(str(r["status"]) for r in details)),
            "estados_acousticbrainz": dict(
                Counter(estado_acustico(r) for r in acoustic)
            ),
            "segundos_ejecucion": round(time.monotonic() - started, 2),
            "actualizado_utc": datetime.now(timezone.utc).isoformat(),
        }
        path = ROOT / "docs/piloto_musicbrainz.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n")
        tmp.replace(path)

    for i, row in enumerate(selected, 1):
        mbid = row["artist_mbid"]
        a = client.get(*solicitud_artista(mbid))
        ad = a["data"] if a["status"] == 200 else {}
        names = {normalizar(ad.get("name", ""))} | {
            normalizar(x["name"]) for x in ad.get("aliases", [])
        }
        name_ok = normalizar(row["artist_name"]) in names
        artists[mbid] = {
            "artist_mbid_suministrado": mbid,
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
        response = client.get(*solicitud_grabacion(row))
        status, chosen, cands = evaluar(row, response["data"].get("recordings", []))
        if response["status"] != 200:
            status = "error_consulta"
        elif response["data"].get("count", 0) > 100:
            status = "candidatos_truncados"
            chosen = ""
        for c in cands:
            candidates.append(
                {"track_id": row["track_id"], **c, "url_evidencia": response["url"]}
            )
        result = {
            "track_id": row["track_id"],
            "artist_mbid_suministrado": mbid,
            "nombre_artista_validado": name_ok,
            "estado": status,
            "recording_mbid": chosen,
            "candidatos": len(cands),
            "fuente_id": "musicbrainz",
            "metodo": "titulo_exacto+mbid_artista+album_exacto+duracion_3s+candidato_unico",
            "url_evidencia": response["url"],
            "fecha_consulta": response["fecha_utc"],
        }
        results.append(result)
        if chosen:
            detail = client.get(
                f"https://musicbrainz.org/ws/2/recording/{chosen}",
                {
                    "fmt": "json",
                    "inc": "artists+releases+isrcs+genres+work-rels+artist-rels+work-level-rels",
                },
            )
            details.append({"track_id": row["track_id"], **detail})
            ac = client.get(f"https://acousticbrainz.org/api/v1/{chosen}/low-level")
            acoustic.append(
                {"track_id": row["track_id"], "recording_mbid": chosen, **ac}
            )
        print(
            f"{i}/{len(selected)} {row['track_id']}: {status}; artista validado={name_ok}",
            flush=True,
        )
        if i % 10 == 0:
            guardar()
    guardar(completo=True)


def exportar(results, artists, candidates, details, acoustic):
    escribir_csv(ROOT / "data/processed/musicbrainz_correspondencias.csv", results)
    escribir_csv(
        ROOT / "data/processed/musicbrainz_artistas.csv", list(artists.values())
    )
    escribir_csv(
        ROOT / "data/processed/musicbrainz_candidatos.csv",
        candidates,
        [
            "track_id",
            "recording_mbid",
            "titulo",
            "titulo_exacto",
            "artista_mbid_presente",
            "album_exacto",
            "diferencia_duracion_s",
            "elegible",
            "puntaje",
            "url_evidencia",
        ],
    )
    (ROOT / "data/processed/musicbrainz_detalles.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2)
    )
    (ROOT / "data/processed/acousticbrainz.json").write_text(
        json.dumps(acoustic, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    try:
        main()
    except ServicioPausado as exc:
        print(f"Piloto pausado: {exc}", flush=True)
        raise SystemExit(75)
    except KeyboardInterrupt:
        print(
            "Piloto interrumpido. Respuestas recuperadas conservadas en caché.",
            flush=True,
        )
        raise SystemExit(130)
