"""Casos negativos que verifican el significado de las preguntas SPARQL."""

import unittest
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
PREFIJO = "@prefix mus: <https://example.org/musica/> . @prefix : <urn:test:> . "


class ConsultasTest(unittest.TestCase):
    def consultar(self, numero, datos):
        ruta = next((ROOT / "consultas/etapa2").glob(f"{numero:02d}_*.rq"))
        return list(
            Graph().parse(data=PREFIJO + datos, format="turtle").query(ruta.read_text())
        )

    def test_creditos_no_mezclan_capturas(self):
        datos = """ :g a mus:Grabacion; mus:tieneCredito :c1, :c2 .
        :c1 mus:artistaAcreditado :a; mus:respaldadoPor :s1; mus:posicionCredito 1 .
        :c2 mus:artistaAcreditado :b; mus:respaldadoPor :s2; mus:posicionCredito 2 ."""
        self.assertEqual(self.consultar(2, datos), [])
        self.assertEqual(len(self.consultar(2, datos.replace(":s2", ":s1"))), 2)

    def test_obras_no_cuentan_dos_referencias_del_mismo_mbid(self):
        datos = """ :g1 mus:interpretaObra :obra; mus:mbid "m1"; mus:tieneCredito :c1 .
        :g2 mus:interpretaObra :obra; mus:mbid "m1"; mus:tieneCredito :c2 .
        :c1 mus:artistaAcreditado :a . :c2 mus:artistaAcreditado :b ."""
        self.assertEqual(self.consultar(3, datos), [])
        self.assertEqual(
            len(
                self.consultar(
                    3,
                    datos.replace(
                        ':g2 mus:interpretaObra :obra; mus:mbid "m1"',
                        ':g2 mus:interpretaObra :obra; mus:mbid "m2"',
                    ),
                )
            ),
            2,
        )

    def test_catalogo_no_se_atribuye_a_otro_sello(self):
        datos = """ :r1 mus:publicadoPor :s1, :s2; mus:tienePublicacion :p1, :p2 .
        :r2 mus:publicadoPor :s1 .
        :p1 mus:selloPublicacion :s1; mus:numeroCatalogo "A" .
        :p2 mus:selloPublicacion :s2; mus:numeroCatalogo "B" ."""
        filas = self.consultar(5, datos)
        self.assertEqual(len(filas), 2)
        self.assertFalse(any(str(f.catalogo) == "B" for f in filas))

    def test_tonalidad_y_tempo_deben_pertenecer_al_mismo_analisis(self):
        datos = """ :g mus:tieneAnalisis :a, :b .
        :a a mus:AnalisisAcustico; mus:fuente <https://example.org/musica/Fuente/acousticbrainz>; mus:tonica "C"; mus:modo "major"; mus:tempoBPM 100 .
        :b a mus:AnalisisAcustico; mus:fuente <https://example.org/musica/Fuente/acousticbrainz>; mus:tonica "D"; mus:modo "minor"; mus:tempoBPM 130 ."""
        self.assertEqual(self.consultar(7, datos), [])
        self.assertEqual(
            len(
                self.consultar(7, datos.replace("mus:tempoBPM 100", "mus:tempoBPM 121"))
            ),
            1,
        )

    def test_generos_cuentan_categorias_independientemente(self):
        datos = """ :rock a mus:GeneroMusical . :vacio a mus:GeneroMusical .
        :g a mus:Grabacion; mus:tieneAsignacionGenero :x, :y .
        :x mus:generoAsignado :rock . :y mus:generoAsignado :rock .
        :a a mus:Artista; mus:tieneAsignacionGenero :z . :z mus:generoAsignado :rock ."""
        filas = self.consultar(8, datos)
        rock = next(f for f in filas if str(f.genero) == "urn:test:rock")
        self.assertEqual(tuple(map(int, rock[1:])), (1, 1, 0))
        vacio = next(f for f in filas if str(f.genero) == "urn:test:vacio")
        self.assertEqual(tuple(map(int, vacio[1:])), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
