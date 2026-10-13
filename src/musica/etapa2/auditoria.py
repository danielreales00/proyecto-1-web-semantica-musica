"""Respuestas esperadas calculadas directamente desde CSV, sin ejecutar SPARQL.

No importa el generador RDF. Reproduce las claves públicas de identidad,
pero evalúa las condiciones musicales mediante conjuntos y agrupaciones.
"""

import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from urllib.parse import quote

BASE = "https://example.org/musica/"


def recurso(clase, *clave):
    return BASE + clase + "/" + "/".join(quote(str(c), safe="") for c in clave)


def sha(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def digest(valor):
    return hashlib.sha256(
        json.dumps(valor, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


class OraculoCSV:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        self.huellas = {}
        self.mbid_por_track = {}
        for tabla in (
            "grabaciones_correspondencias_masivas",
            "musicbrainz_correspondencias",
        ):
            for f in self.filas(tabla):
                if f["estado"] == "aceptada":
                    self.mbid_por_track.setdefault(f["track_id"], f["recording_mbid"])
        self.tracks_por_mbid = defaultdict(set)
        for track, mbid in self.mbid_por_track.items():
            self.tracks_por_mbid[mbid].add(track)
        self.creditos = defaultdict(set)
        self.artistas_por_mbid = defaultdict(set)
        for tabla in ("creditos_grabaciones_masivos", "creditos_grabacion"):
            captura = self.captura(tabla)
            for f in self.filas(tabla):
                mbid = f["recording_mbid"]
                self.artistas_por_mbid[mbid].add(f["artist_mbid"])
                self.creditos[mbid, captura].add(
                    (f["artist_mbid"], str(int(f["orden"])), f["nombre_acreditado"])
                )

    def filas(self, tabla):
        ruta = self.carpeta / (tabla + ".csv")
        self.huellas.setdefault(ruta.name, sha(ruta))
        with ruta.open(newline="", encoding="utf-8-sig") as archivo:
            yield from csv.DictReader(archivo)

    def captura(self, tabla):
        ruta = self.carpeta / (tabla + ".csv")
        return recurso("CapturaFuente", sha(ruta))

    def analisis(self):
        for tabla in ("acousticbrainz_masivo", "acousticbrainz"):
            captura = self.captura(tabla)
            for f in self.filas(tabla):
                if not f["bpm"]:
                    continue
                clave = [
                    f["recording_mbid"],
                    f.get("submission_offset"),
                    f.get("fecha_consulta"),
                ]
                identificador = recurso(
                    "AnalisisAcustico", digest([tabla, captura, clave])
                )
                yield f, identificador, Decimal(f["bpm"])

    def pregunta1(self):
        rock = {
            f["track_id"]
            for f in self.filas("cancion_genero")
            if f["genero"] == "Rock" and f["papel"] == "mayoritario"
        }
        return {
            (recurso("Grabacion", track), a, bpm)
            for f, a, bpm in self.analisis()
            if bpm > 120
            for track in self.tracks_por_mbid[f["recording_mbid"]] & rock
        }

    def pregunta2(self):
        return {
            (
                recurso("Grabacion", track),
                captura,
                recurso("Artista", a),
                posicion,
                nombre,
            )
            for (mbid, captura), creditos in self.creditos.items()
            if len({c[0] for c in creditos}) >= 2
            for track in self.tracks_por_mbid[mbid]
            for a, posicion, nombre in creditos
        }

    def relaciones_obras(self):
        obras, compositores = defaultdict(set), defaultdict(set)
        for f in self.filas("relaciones_musicales_masivas"):
            if (f["sujeto_tipo"], f["relacion"], f["objeto_tipo"]) == (
                "grabacion",
                "performance",
                "obra",
            ):
                if self.tracks_por_mbid[f["sujeto_mbid"]]:
                    obras[f["objeto_mbid"]].add(f["sujeto_mbid"])
            if (f["sujeto_tipo"], f["relacion"], f["objeto_tipo"]) == (
                "artista",
                "composer",
                "obra",
            ):
                compositores[f["objeto_mbid"]].add(f["sujeto_mbid"])
        for f in self.filas("relaciones_musicbrainz"):
            if (f["sujeto_tipo"], f["relacion"], f["direccion"], f["objeto_tipo"]) == (
                "grabacion",
                "performance",
                "forward",
                "work",
            ):
                if self.tracks_por_mbid[f["sujeto_id"]]:
                    obras[f["objeto_id"]].add(f["sujeto_id"])
            if (f["sujeto_tipo"], f["relacion"], f["direccion"], f["objeto_tipo"]) == (
                "obra",
                "composer",
                "backward",
                "artist",
            ):
                compositores[f["sujeto_id"]].add(f["objeto_id"])
        return obras, compositores

    def pregunta3(self):
        obras, compositores = self.relaciones_obras()
        resultado = set()
        for obra, grabaciones in obras.items():
            artistas = set().union(*(self.artistas_por_mbid[g] for g in grabaciones))
            if len(grabaciones) < 2 or len(artistas) < 2:
                continue
            for g in grabaciones:
                for a in self.artistas_por_mbid[g] or {""}:
                    for c in compositores[obra] or {""}:
                        resultado.add(
                            (
                                recurso("ObraMusical", obra),
                                g,
                                recurso("Artista", a) if a else "",
                                recurso("Artista", c) if c else "",
                            )
                        )
        return resultado

    def pregunta4(self):
        ediciones = defaultdict(set)
        grupos = defaultdict(set)
        for tabla in ("grabacion_lanzamiento_masivo", "grabacion_lanzamiento"):
            for f in self.filas(tabla):
                ediciones[f["recording_mbid"]].add(f["release_mbid"])
        for f in self.filas("lanzamientos_masivos"):
            if f["grupo_lanzamiento_mbid"]:
                grupos[f["release_mbid"]].add(f["grupo_lanzamiento_mbid"])
        return {
            (
                recurso("Grabacion", t),
                recurso("Lanzamiento", r),
                recurso("GrupoLanzamientos", g) if g else "",
            )
            for mbid, releases in ediciones.items()
            if len(releases) >= 2
            for t in self.tracks_por_mbid[mbid]
            for r in releases
            for g in grupos[r] or {""}
        }

    def pregunta5(self):
        titulos, sellos, catalogos = (
            defaultdict(set),
            defaultdict(set),
            defaultdict(set),
        )
        for tabla in ("lanzamientos_masivos", "lanzamientos"):
            for f in self.filas(tabla):
                if f["titulo"]:
                    titulos[f["release_mbid"]].add(f["titulo"])
        for f in self.filas("lanzamiento_sello_masivo"):
            if f["label_mbid"]:
                sellos[f["label_mbid"]].add(f["release_mbid"])
                if f["numero_catalogo"]:
                    catalogos[f["label_mbid"], f["release_mbid"]].add(
                        f["numero_catalogo"]
                    )
        return {
            (recurso("SelloDiscografico", s), recurso("Lanzamiento", r), titulo, c)
            for s, releases in sellos.items()
            if len(releases) >= 2
            for r in releases
            for titulo in titulos[r] or {""}
            for c in catalogos[s, r] or {""}
        }

    def pregunta6(self):
        personas, agrupaciones = set(), set()
        for tabla in ("artistas_masivos", "artistas"):
            for f in self.filas(tabla):
                tipo = f.get("tipo") or f.get("tipo_musicbrainz")
                if tipo == "Person":
                    personas.add(f["artist_mbid"])
                if tipo in {"Group", "Choir", "Orchestra"}:
                    agrupaciones.add(f["artist_mbid"])
        resultado = set()
        for (mbid, captura), creditos in self.creditos.items():
            artistas = {c[0] for c in creditos}
            for p in artistas & personas:
                for g in artistas & agrupaciones:
                    for t in self.tracks_por_mbid[mbid]:
                        if p != g:
                            resultado.add(
                                (
                                    recurso("Grabacion", t),
                                    captura,
                                    recurso("Artista", p),
                                    recurso("Artista", g),
                                )
                            )
        return resultado

    def pregunta7(self):
        return {
            (a, recurso("Grabacion", t), bpm, recurso("Fuente", f["fuente_id"]))
            for f, a, bpm in self.analisis()
            if bpm > 120
            and (f.get("key_key") or f.get("tonalidad")) == "C"
            and (f.get("key_scale") or f.get("escala")) == "major"
            for t in self.tracks_por_mbid[f["recording_mbid"]]
        }

    def pregunta8(self):
        miembros = defaultdict(lambda: [set(), set(), set()])
        for f in self.filas("cancion_genero"):
            miembros[recurso("GeneroMusical", "tagtraum", f["genero"])][0].add(
                f["track_id"]
            )
        for f in self.filas("grupo_lanzamiento_genero"):
            miembros[
                recurso("GeneroMusical", "musicbrainz", f["genero_mbid"] or f["genero"])
            ][2].add(f["grupo_lanzamiento_mbid"])
        for f in self.filas("wikidata_hechos"):
            if (
                f["propiedad"] == "P136"
                and f["estado_correspondencia"] == "unica"
                and f["tipo_valor"] == "uri"
            ):
                miembros[
                    recurso("GeneroMusical", "wikidata", f["valor"].rsplit("/", 1)[-1])
                ][1].add(f["artist_mbid"])
        return {
            (g, *(str(len(c)) for c in categorias))
            for g, categorias in miembros.items()
        }
