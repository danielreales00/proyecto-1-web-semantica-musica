"""Casos adversos de identidad: títulos homónimos, versiones y empates."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from diagnostico import normalizar
from musicbrainz import evaluar


class ReconciliacionTest(unittest.TestCase):
    def setUp(self):
        self.row = {
            "title": "Song",
            "artist_mbid": "artist-1",
            "release": "Album",
            "duration": "200",
        }
        self.rec = {
            "id": "recording-1",
            "title": "Song",
            "length": 200000,
            "artist-credit": [{"artist": {"id": "artist-1"}}],
            "releases": [{"title": "Album"}],
        }

    def test_coincidencia_completa(self):
        self.assertEqual(evaluar(self.row, [self.rec])[:2], ("aceptada", "recording-1"))

    def test_homonimo_otro_artista(self):
        rec = {**self.rec, "artist-credit": [{"artist": {"id": "artist-2"}}]}
        self.assertEqual(evaluar(self.row, [rec])[1], "")

    def test_version_en_vivo_no_se_fusiona(self):
        self.assertEqual(
            evaluar(self.row, [{**self.rec, "title": "Song (live)"}])[1], ""
        )

    def test_empate_no_se_resuelve_por_orden(self):
        a = evaluar(self.row, [self.rec, {**self.rec, "id": "recording-2"}])
        self.assertEqual(a[:2], ("ambigua", ""))

    def test_duracion_desconocida_no_es_cero(self):
        self.assertEqual(evaluar(self.row, [{**self.rec, "length": None}])[1], "")

    def test_duracion_diferente(self):
        self.assertEqual(evaluar(self.row, [{**self.rec, "length": 220000}])[1], "")

    def test_album_distinto(self):
        self.assertEqual(
            evaluar(self.row, [{**self.rec, "releases": [{"title": "Other"}]}])[1], ""
        )

    def test_normalizacion_no_borra_version_ni_acentos(self):
        self.assertEqual(normalizar("  CANCIÓN  (Live) "), "canción (live)")


if __name__ == "__main__":
    unittest.main()
