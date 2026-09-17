"""Compila los dos documentos finales y comprueba páginas, referencias y desbordamientos."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Usar únicamente paquetes TeX ya almacenados",
    )
    args = parser.parse_args()
    engine = shutil.which("tectonic")
    if not engine:
        raise SystemExit(
            "Falta Tectonic; ver README.md. Los .tex también se pueden compilar con pdfLaTeX."
        )
    subprocess.run([sys.executable, str(ROOT / "latex/generar_tablas.py")], check=True)
    staging = ROOT / "tmp/latex"
    staging.mkdir(parents=True, exist_ok=True)
    out = ROOT / "output/pdf"
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in ["informe_final", "modelo_anexo"]:
        command = [engine, "--keep-logs", "--outdir", str(staging)]
        if args.offline:
            command.append("--only-cached")
        command.append(str(ROOT / "latex" / f"{name}.tex"))
        subprocess.run(command, cwd=ROOT / "latex", check=True)
        log = (staging / f"{name}.log").read_text(errors="replace")
        assert "Overfull" not in log, f"{name}: revisar desbordamiento tipográfico"
        assert "undefined references" not in log and "Citation" not in log, (
            f"{name}: revisar referencias"
        )
        pdf = staging / f"{name}.pdf"
        reader = PdfReader(pdf)
        assert name != "informe_final" or len(reader.pages) <= 4
        text = "\n".join(p.extract_text() for p in reader.pages)
        assert "\ufffd" not in text and "??" not in text
        shutil.copy2(pdf, out / pdf.name)
        results[name] = {
            "paginas": len(reader.pages),
            "sin_desbordamientos": True,
            "referencias_resueltas": True,
        }
    (ROOT / "docs/validacion_latex.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
