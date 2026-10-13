"""Verifica una reproducción completa desde las entradas seleccionadas, sin resultados copiados."""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from pypdf import PdfReader

from archivos_entrega import firma_entradas, huellas_entradas
from musica.comun.rutas import ROOT


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def pdf_text(path):
    return [page.extract_text() for page in PdfReader(path).pages]


def main():
    inputs_expected = huellas_entradas(ROOT)
    csv_expected = {p.name: sha(p) for p in sorted((ROOT / "output/csv").glob("*.csv"))}
    assert len(csv_expected) == 39, "La referencia debe contener 39 CSV"
    queries = {
        p.name: json.loads(p.read_text())
        for p in sorted((ROOT / "output/sparql").glob("[0-9][0-9]_*.json"))
    }
    assert len(queries) == 8
    metrics = json.loads((ROOT / "docs/resultados.json").read_text())
    comparison = json.loads(
        (ROOT / "docs/comparacion_dbpedia_wikidata.json").read_text()
    )
    pdfs = {
        name: pdf_text(ROOT / "output/pdf" / name)
        for name in ["informe_final.pdf", "modelo_anexo.pdf"]
    }
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(tests.stdout + tests.stderr, flush=True)
    tests.check_returncode()
    match = re.search(r"Ran (\d+) tests?", tests.stdout + tests.stderr)
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="verificacion_entrega_", dir=ROOT / "tmp"
    ) as scratch:
        dest = Path(scratch) / "reproduccion"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "src/ejecutar.py"),
                "--offline",
                "--destino",
                str(dest),
            ],
            check=True,
        )
        actual = {p.name: sha(p) for p in sorted((dest / "output/csv").glob("*.csv"))}
        assert actual == csv_expected, (
            "Los CSV reconstruidos no coinciden con la entrega"
        )
        assert json.loads((dest / "docs/resultados.json").read_text()) == metrics, (
            "Métricas diferentes"
        )
        assert (
            json.loads((dest / "docs/comparacion_dbpedia_wikidata.json").read_text())
            == comparison
        ), "Comparación de fuentes diferente"
        for name, expected in queries.items():
            assert (
                json.loads((dest / "output/sparql" / name).read_text()) == expected
            ), name
        for name, expected in pdfs.items():
            assert pdf_text(dest / "output/pdf" / name) == expected, name
        assert huellas_entradas(dest) == inputs_expected, (
            "Entradas diferentes en la reproducción"
        )
        assert huellas_entradas(ROOT) == inputs_expected, (
            "Entradas modificadas durante la verificación"
        )
        report = {
            "estado": "correcto",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "modo": "reconstruccion_completa_sin_HTTP_desde_entradas_en_carpeta_nueva",
            "resultados_precalculados_copiados": False,
            "entradas_verificadas": len(inputs_expected),
            "firma_entradas_sha256": firma_entradas(inputs_expected),
            "csv_identicos_byte_a_byte": len(actual),
            "csv_sha256": actual,
            "metricas_identicas": True,
            "comparacion_dbpedia_wikidata_recalculada": True,
            "consultas_sparql_recalculadas_e_identicas": len(queries),
            "texto_pdf_identico": True,
            "paginas_pdf": {k: len(v) for k, v in pdfs.items()},
            "pruebas_automatizadas": int(match.group(1)) if match else None,
            "python": sys.version.split()[0],
            "dependencias": {
                name: version(name) for name in ["requests", "pypdf", "pyoxigraph"]
            },
            "alcance": "La instantánea se reproduce desde las respuestas y subconjuntos vinculados. Los archivos completos se adquieren de nuevo mediante los descargadores si se desea repetir también su filtrado.",
        }
    (ROOT / "docs/reproducibilidad_entrega.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ("csv_sha256", "codigo_sha256")
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
