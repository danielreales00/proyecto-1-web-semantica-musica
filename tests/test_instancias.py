"""Casos que distinguen evidencia, identidad local y relaciones musicales."""

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from musica.etapa2.entidades import Modelo
from musica.etapa2.entradas import Entradas
from musica.etapa2.escritura import Escritor, uri
from musica.etapa2.instancias import generar_instancias
from musica.etapa2.mediciones import acousticbrainz, generos
from musica.etapa2.ontologia import construir_ontologia, serializar
from musica.etapa2.relaciones import creditos, publicaciones
from musica.etapa2.validacion import validar_archivos
from musica.etapa2.vocabulario import MUS


def guardar(carpeta, nombre, filas):
    with (carpeta / (nombre + ".csv")).open(
        "w", newline="", encoding="utf-8"
    ) as archivo:
        columnas = list(dict.fromkeys(k for f in filas for k in f)) or ["vacio"]
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


class InstanciasTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.archivo = io.StringIO()
        self.e = Escritor(self.archivo)

    def modelo(self, tablas):
        for nombre, filas in tablas.items():
            guardar(self.carpeta, nombre, filas)
        return Modelo(Entradas(self.carpeta, self.e))

    def grafo(self):
        self.e.cerrar_etiquetas()
        return Graph().parse(data=self.archivo.getvalue(), format="turtle")

    def test_reconciliacion_ambigua_no_proyecta_y_conflicto_no_mezcla(self):
        m = self.modelo(
            {
                "grabaciones_correspondencias_masivas": [
                    {
                        "track_id": "a",
                        "recording_mbid": "r1",
                        "estado": "aceptada",
                        "metodo": "exacto",
                    },
                    {
                        "track_id": "b",
                        "recording_mbid": "r2",
                        "estado": "ambigua",
                        "metodo": "exacto",
                    },
                ],
                "musicbrainz_correspondencias": [
                    {
                        "track_id": "a",
                        "recording_mbid": "r3",
                        "estado": "aceptada",
                        "metodo": "piloto",
                    }
                ],
            }
        )
        m.locales = {t: self.e.entidad("Grabacion", t) for t in ("a", "b")}
        m.correspondencias()
        self.assertEqual(m.seleccion, {"a": "r1"})
        self.assertEqual(len(m.conflictos), 1)
        self.assertEqual(m.registros("r2"), [])
        self.assertEqual(m.registros("r3"), [])
        self.assertFalse(list(self.grafo().triples((None, OWL.sameAs, None))))

    def test_analisis_compartido_y_capturas_separadas(self):
        m = self.modelo(
            {
                "acousticbrainz_masivo": [
                    {
                        "recording_mbid": "r1",
                        "submission_offset": "0",
                        "bpm": "130.25",
                        "key_key": "C",
                        "key_scale": "major",
                        "fuente_id": "acousticbrainz_dump",
                    }
                ],
                "acousticbrainz": [
                    {
                        "recording_mbid": "r1",
                        "bpm": "90",
                        "tonalidad": "D",
                        "escala": "minor",
                        "fecha_consulta": "2026-01-01",
                        "fuente_id": "acousticbrainz",
                    }
                ],
            }
        )
        m.por_mbid["r1"] = [self.e.entidad("Grabacion", t) for t in ("a", "b")]
        acousticbrainz(m)
        g = self.grafo()
        analisis = set(g.subjects(RDF.type, MUS.AnalisisAcustico))
        self.assertEqual(len(analisis), 2)
        for r in m.por_mbid["r1"]:
            self.assertEqual(set(g.objects(r, MUS.tieneAnalisis)), analisis)
        for a in analisis:
            self.assertEqual(len(list(g.objects(a, MUS.tempoBPM))), 1)

    def test_creditos_de_grupo_no_se_asignan_a_grabaciones(self):
        m = self.modelo(
            {
                "creditos_grabaciones_masivos": [],
                "creditos_grabacion": [],
                "creditos_grupo_lanzamiento": [
                    {
                        "grupo_lanzamiento_mbid": "g1",
                        "artist_mbid": "a1",
                        "nombre": "Artista",
                        "nombre_acreditado": "Artista",
                        "orden": "2",
                        "union": " & ",
                    }
                ],
            }
        )
        creditos(m)
        g = self.grafo()
        c = g.value(uri("GrupoLanzamientos", "g1"), MUS.tieneCredito)
        self.assertEqual(
            g.value(c, MUS.acreditaEntidad), uri("GrupoLanzamientos", "g1")
        )
        self.assertEqual(int(g.value(c, MUS.posicionCredito)), 2)
        self.assertFalse(list(g.subjects(RDF.type, MUS.Grabacion)))

    def test_catalogo_pertenece_al_par_edicion_sello(self):
        m = self.modelo(
            {
                "grabacion_lanzamiento_masivo": [],
                "grabacion_lanzamiento": [],
                "lanzamiento_sello_masivo": [
                    {"release_mbid": "r1", "label_mbid": "s1", "numero_catalogo": "A"},
                    {"release_mbid": "r1", "label_mbid": "s2", "numero_catalogo": "B"},
                    {"release_mbid": "r1", "label_mbid": "", "numero_catalogo": "C"},
                ],
            }
        )
        publicaciones(m)
        g = self.grafo()
        edicion = uri("Lanzamiento", "r1")
        self.assertEqual(len(list(g.objects(edicion, MUS.tienePublicacion))), 3)
        self.assertEqual(len(list(g.objects(edicion, MUS.publicadoPor))), 2)
        self.assertFalse(list(g.objects(edicion, MUS.numeroCatalogo)))
        for p in g.objects(edicion, MUS.tienePublicacion):
            if str(g.value(p, MUS.numeroCatalogo)) == "A":
                self.assertEqual(
                    g.value(p, MUS.selloPublicacion), uri("SelloDiscografico", "s1")
                )

    def test_generos_de_vocabularios_distintos_no_se_fusionan(self):
        m = self.modelo(
            {
                "cancion_genero": [
                    {"track_id": "t1", "genero": "Rock", "papel": "mayoritario"}
                ],
                "grupo_lanzamiento_genero": [
                    {
                        "grupo_lanzamiento_mbid": "g1",
                        "genero_mbid": "g-rock",
                        "genero": "Rock",
                        "votos": "3",
                    }
                ],
                "wikidata_hechos": [],
            }
        )
        m.locales["t1"] = self.e.entidad("Grabacion", "t1")
        generos(m)
        g = self.grafo()
        self.assertEqual(len(set(g.subjects(RDF.type, MUS.GeneroMusical))), 2)
        self.assertEqual(
            len(list(g.objects(m.locales["t1"], MUS.tieneAsignacionGenero))), 1
        )

    def test_valida_exportacion_con_motor_independiente(self):
        self.e.entidad("Grabacion", "t1", "Título desconocido")
        self.grafo()
        ontologia, instancias = (
            self.carpeta / "ontology.ttl",
            self.carpeta / "instances.ttl",
        )
        ontologia.write_text(serializar(construir_ontologia()), encoding="utf-8")
        instancias.write_text(self.archivo.getvalue(), encoding="utf-8")
        resultado = validar_archivos(
            ontologia, instancias, progreso=lambda *a, **k: None
        )
        self.assertEqual(resultado["etiquetas_por_idioma"]["und"], 1)
        with instancias.open("a") as archivo:
            archivo.write(f"<{MUS}huerfana> <{MUS}compuso> <{MUS}obraSinEtiqueta> .\n")
        with self.assertRaisesRegex(ValueError, "recursos_sin_etiqueta"):
            validar_archivos(ontologia, instancias, progreso=lambda *a, **k: None)

    def test_numeros_invalidos_y_etiquetas_de_respaldo(self):
        r = self.e.entidad("Artista", "a1")
        a = self.e.entidad("AnalisisAcustico", "x")
        with self.assertRaises(ValueError):
            self.e.dato(a, "tempoBPM", "NaN", XSD.decimal)
        g = self.grafo()
        self.assertEqual(g.value(r, RDFS.label), Literal("Artista a1", lang="es"))

    def test_generacion_reproducible_y_fallo_conserva_salida(self):
        tablas = (
            "canciones grabaciones_correspondencias_masivas musicbrainz_correspondencias "
            "artistas_masivos artistas obras_masivas obras grupos_lanzamientos "
            "lanzamientos_masivos lanzamientos sellos_masivos grabaciones_masivas grabaciones "
            "isrc_masivos isrc creditos_grabaciones_masivos creditos_grabacion "
            "creditos_grupo_lanzamiento grabacion_lanzamiento_masivo grabacion_lanzamiento "
            "lanzamiento_sello_masivo relaciones_musicales_masivas relaciones_musicbrainz "
            "cancion_genero grupo_lanzamiento_genero wikidata_hechos descriptores_acusticos "
            "acousticbrainz_masivo acousticbrainz"
        ).split()
        for tabla in tablas:
            guardar(self.carpeta, tabla, [])
        guardar(
            self.carpeta,
            "canciones",
            [
                {
                    "track_id": "t1",
                    "title": "Tema",
                    "release": "Álbum",
                    "duration": "123.456",
                    "artist_mbid": "a1",
                    "artist_name": "Artista",
                }
            ],
        )
        salida = self.carpeta / "instances.ttl"
        primero = generar_instancias(
            self.carpeta, salida, progreso=lambda *a, **k: None
        )
        contenido = salida.read_bytes()
        segundo = generar_instancias(
            self.carpeta, salida, progreso=lambda *a, **k: None
        )
        self.assertEqual(primero["sha256_instances"], segundo["sha256_instances"])
        (self.carpeta / "canciones.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            generar_instancias(self.carpeta, salida, progreso=lambda *a, **k: None)
        self.assertEqual(salida.read_bytes(), contenido)

    def test_cadena_publicacion_declarada(self):
        g = construir_ontologia()
        cadena = g.value(MUS.publicadoPor, OWL.propertyChainAxiom)
        self.assertEqual(
            list(g.items(cadena)), [MUS.tienePublicacion, MUS.selloPublicacion]
        )


if __name__ == "__main__":
    unittest.main()
