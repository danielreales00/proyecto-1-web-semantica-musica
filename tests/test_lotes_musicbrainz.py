"""Los lotes no deben aceptar datos truncados ni mezclar identidades."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from musicbrainz import evaluar, precargar


class LotesTest(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "track_id": "one",
                "artist_mbid": "artist-1",
                "title": "Song",
                "release": "Album",
                "duration": "200",
            },
            {
                "track_id": "two",
                "artist_mbid": "artist-1",
                "title": "Other",
                "release": "Album",
                "duration": "220",
            },
        ]

    def already(self, client, request):
        return "/artist/" in request[0]

    def test_no_acepta_lote_truncado(self):
        client = Mock()
        client.get.return_value = {
            "status": 200,
            "data": {"count": 101, "recordings": []},
        }
        with (
            patch("musicbrainz.disponible", side_effect=self.already),
            patch("musicbrainz.guardar_derivada") as save,
        ):
            precargar(client, self.rows)
            save.assert_not_called()

    def test_no_convierte_error_en_busqueda_vacia(self):
        client = Mock()
        client.get.return_value = {"status": 503, "data": {}}
        with (
            patch("musicbrainz.disponible", side_effect=self.already),
            patch("musicbrainz.guardar_derivada") as save,
        ):
            precargar(client, self.rows)
            save.assert_not_called()

    def test_mismo_artista_distintas_canciones(self):
        records = [
            {
                "id": "r1",
                "title": "Song",
                "length": 200000,
                "artist-credit": [{"artist": {"id": "artist-1"}}],
                "releases": [{"title": "Album"}],
            },
            {
                "id": "r2",
                "title": "Other",
                "length": 220000,
                "artist-credit": [{"artist": {"id": "artist-1"}}],
                "releases": [{"title": "Album"}],
            },
        ]
        client = Mock()
        client.get.return_value = {
            "status": 200,
            "data": {"count": 2, "recordings": records},
        }
        with (
            patch("musicbrainz.disponible", side_effect=self.already),
            patch("musicbrainz.guardar_derivada") as save,
        ):
            precargar(client, self.rows)
            for row, call, expected in zip(
                self.rows, save.call_args_list, ["r1", "r2"]
            ):
                self.assertEqual(
                    evaluar(row, call.args[3]["recordings"])[:2], ("aceptada", expected)
                )


if __name__ == "__main__":
    unittest.main()
