"""La lectura de COPY debe preservar textos y distinguir ausencia de contenido literal."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ampliar_albumes import estado, keys_for
from extraer_musicbrainz_completo import cells


class VolcadoTest(unittest.TestCase):
    def test_copy_null_escapes_y_unicode(self):
        self.assertEqual(
            cells("42\t\\N\tCanción\\tLive\\n2000\t\\\\N\n".encode()),
            ["42", "", "Canción\tLive\n2000", "\\N"],
        )

    def test_album_no_resuelve_homonimos_solo_por_titulo(self):
        a = {"title": "Same", "artist-credit": [{"artist": {"id": "a"}}]}
        b = {"title": "Same", "artist-credit": [{"artist": {"id": "b"}}]}
        self.assertFalse(keys_for(a) & keys_for(b))
        self.assertEqual(estado({"g1", "g2"}), "ambigua")


if __name__ == "__main__":
    unittest.main()
