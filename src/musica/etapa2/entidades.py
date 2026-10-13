"""Entidades musicales y decisiones de reconciliación conservadoras."""

from collections import defaultdict

from rdflib.namespace import XSD

from musica.etapa2.escritura import huella
from musica.etapa2.vocabulario import MUS


class Modelo:
    def __init__(self, entradas):
        self.d = entradas
        self.e = entradas.e
        self.locales = {}
        self.seleccion = {}
        self.por_mbid = defaultdict(list)
        self.conflictos = []

    def canciones(self):
        for f in self.d.filas("canciones"):
            track = f["track_id"]
            if track in self.locales:
                raise ValueError(f"track_id repetido: {track}")
            r = self.e.entidad("Grabacion", track, f["title"])
            self.locales[track] = r
            self.e.dato(r, "identificador", track)
            self.e.dato(r, "titulo", f["title"])
            self.e.dato(r, "lanzamientoSuministrado", f["release"])
            self.e.dato(r, "duracionSuministradaSegundos", f["duration"], XSD.decimal)
            self.d.respaldar(r, "canciones", f)
            if f["artist_mbid"]:
                artista = self.e.entidad("Artista", f["artist_mbid"], f["artist_name"])
                self.e.triple(r, MUS.artistaSuministrado, artista)

    def correspondencias(self):
        for tabla in (
            "grabaciones_correspondencias_masivas",
            "musicbrainz_correspondencias",
        ):
            for f in self.d.filas(tabla):
                track, mbid = f["track_id"], f["recording_mbid"]
                local = self.locales[track]
                c = self.e.entidad(
                    "Correspondencia",
                    huella([tabla, track, str(self.d.capturas[tabla])]),
                    f"Correspondencia de {track} ({tabla})",
                    "es",
                    True,
                )
                self.e.triple(local, MUS.tieneCorrespondencia, c)
                self.e.dato(c, "estadoCorrespondencia", f["estado"])
                self.e.dato(c, "metodoCorrespondencia", f["metodo"])
                self.e.dato(c, "candidatoMBID", mbid)
                self.d.respaldar(c, tabla, f)
                if f["estado"] == "aceptada":
                    self.seleccionar(track, mbid, tabla)
        for track, mbid in sorted(self.seleccion.items()):
            self.por_mbid[mbid].append(self.locales[track])
            self.e.dato(self.locales[track], "mbid", mbid)

    def seleccionar(self, track, mbid, tabla):
        if not mbid:
            raise ValueError(f"Correspondencia aceptada sin MBID: {track}")
        previo = self.seleccion.get(track)
        if previo and previo != mbid:
            self.conflictos.append(
                {
                    "track_id": track,
                    "mbid_seleccionado": previo,
                    "mbid_piloto": mbid,
                    "tabla": tabla,
                }
            )
        else:
            self.seleccion[track] = mbid

    def registros(self, mbid):
        return self.por_mbid.get(mbid, [])

    def entidades(self):
        tablas = (
            ("artistas_masivos", "Artista", "artist_mbid", "nombre"),
            ("artistas", "Artista", "artist_mbid", "nombre_musicbrainz"),
            ("obras_masivas", "ObraMusical", "work_mbid", "titulo"),
            ("obras", "ObraMusical", "work_mbid", "titulo"),
            (
                "grupos_lanzamientos",
                "GrupoLanzamientos",
                "grupo_lanzamiento_mbid",
                "titulo",
            ),
            ("lanzamientos_masivos", "Lanzamiento", "release_mbid", "titulo"),
            ("lanzamientos", "Lanzamiento", "release_mbid", "titulo"),
            ("sellos_masivos", "SelloDiscografico", "label_mbid", "nombre"),
        )
        for tabla, tipo, columna, nombre in tablas:
            for f in self.d.filas(tabla):
                r = self.e.entidad(tipo, f[columna], f[nombre])
                self.e.dato(r, "mbid", f[columna])
                self.d.respaldar(r, tabla, f)
                self.clasificar(r, tipo, f)
                if nombre == "titulo":
                    self.e.dato(r, "titulo", f[nombre])
                if tipo == "Lanzamiento" and f.get("grupo_lanzamiento_mbid"):
                    grupo = self.e.entidad(
                        "GrupoLanzamientos", f["grupo_lanzamiento_mbid"]
                    )
                    self.e.triple(r, MUS.perteneceAGrupo, grupo)
        self.metadatos_grabaciones()

    def clasificar(self, recurso, tipo, fila):
        if tipo == "Artista":
            clase = {
                "Person": "Persona",
                "Group": "Agrupacion",
                "Orchestra": "Agrupacion",
                "Choir": "Agrupacion",
            }.get(fila.get("tipo") or fila.get("tipo_musicbrainz"))
        elif tipo == "GrupoLanzamientos":
            clase = {"Album": "Album", "Single": "Sencillo", "EP": "EP"}.get(
                fila.get("tipo_primario")
            )
        else:
            clase = None
        if clase:
            self.e.tipar(recurso, clase)

    def metadatos_grabaciones(self):
        for tabla in ("grabaciones_masivas", "grabaciones"):
            for f in self.d.filas(tabla):
                recursos = self.registros(f["recording_mbid"])
                if not recursos:
                    self.d.omitidas[tabla] += 1
                for r in recursos:
                    if f["titulo"].strip():
                        self.e.label(r, f["titulo"], "und")
                    self.e.dato(r, "titulo", f["titulo"])
                    self.d.respaldar(r, tabla, f)
        for tabla in ("isrc_masivos", "isrc"):
            for f in self.d.filas(tabla):
                for r in self.registros(f["recording_mbid"]):
                    self.e.dato(r, "isrc", f["isrc"])
                    self.d.respaldar(r, tabla, f)
