"""Las interrupciones del proveedor no deben producir tormentas de reintentos."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from musicbrainz import Cliente, ServicioPausado


class PausaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = patch("musicbrainz.ROOT", Path(self.tmp.name))
        self.root.start()
        self.addCleanup(self.root.stop)
        self.sleep = patch("musicbrainz.time.sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_503_detiene_y_bloquea_reinicio_pero_permite_cache(self):
        client = Cliente()
        response = Mock(
            status_code=503, headers={"Retry-After": "0"}, text="Service unavailable"
        )
        client.session.get = Mock(return_value=response)
        with self.assertRaises(ServicioPausado):
            client.get("https://musicbrainz.org/ws/2/artist")
        self.assertEqual(client.session.get.call_count, 1)
        state = json.loads((client.state_dir / "musicbrainz.org.json").read_text())
        self.assertEqual(state["respuesta"], "Service unavailable")
        self.assertEqual(list(client.cache.glob("*.json")), [])
        restarted = Cliente()
        restarted.session.get = Mock()
        with self.assertRaises(ServicioPausado):
            restarted.get("https://musicbrainz.org/ws/2/recording")
        restarted.session.get.assert_not_called()
        from musicbrainz import clave_solicitud

        key, _ = clave_solicitud("https://musicbrainz.org/cached", None)
        (client.cache / f"{key}.json").write_text('{"status":200,"data":{}}')
        self.assertEqual(restarted.get("https://musicbrainz.org/cached")["status"], 200)

    def test_respeta_retry_after_mayor_a_cinco_minutos(self):
        client = Cliente()
        client.session.get = Mock(
            return_value=Mock(
                status_code=429, headers={"Retry-After": "900"}, text="limited"
            )
        )
        with patch("musicbrainz.time.time", return_value=1000):
            with self.assertRaises(ServicioPausado):
                client.get("https://musicbrainz.org/ws/2/artist")
        state = json.loads((client.state_dir / "musicbrainz.org.json").read_text())
        self.assertEqual(state["no_consultar_antes_epoch"], 1900)


if __name__ == "__main__":
    unittest.main()
