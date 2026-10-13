"""Contrasta todos los resultados SPARQL con respuestas calculadas desde CSV."""

import csv
import json
from decimal import Decimal

from musica.comun.rutas import ROOT
from musica.etapa2.auditoria import OraculoCSV, sha


def main():
    oraculo = OraculoCSV(ROOT / "output/csv")
    resultados = []
    for numero in range(1, 9):
        ruta = next((ROOT / "output/etapa2/consultas").glob(f"{numero:02d}_*.csv"))
        with ruta.open(encoding="utf-8", newline="") as archivo:
            lector = csv.reader(archivo)
            encabezado = next(lector)
            filas = list(lector)
        observadas = {
            tuple(
                Decimal(v) if k == "bpm" else v
                for k, v in zip(encabezado, f, strict=True)
            )
            for f in filas
        }
        esperadas = getattr(oraculo, f"pregunta{numero}")()
        extras, faltantes = observadas - esperadas, esperadas - observadas
        consulta = next((ROOT / "consultas/etapa2").glob(f"{numero:02d}_*.rq"))
        resultado = {
            "pregunta": numero,
            "filas": len(filas),
            "esperadas": len(esperadas),
            "sobrantes": len(extras),
            "faltantes": len(faltantes),
            "duplicadas": len(filas) - len(observadas),
            "campos_no_ligados": {
                k: sum(f[i] == "" for f in filas) for i, k in enumerate(encabezado)
            },
            "sha256_consulta": sha(consulta),
            "sha256_resultado": sha(ruta),
        }
        if extras or faltantes:
            resultado["ejemplos_diferencias"] = {
                "sobrantes": list(extras)[:3],
                "faltantes": list(faltantes)[:3],
            }
        resultados.append(resultado)
        print(resultado, flush=True)
    informe = {
        "metodo": "Comparación completa de conjuntos de resultados con cálculo independiente sobre los CSV; decimales comparados por valor",
        "fuentes_sha256": oraculo.huellas,
        "preguntas": resultados,
    }
    salida = ROOT / "output/etapa2/auditoria_consultas.json"
    salida.write_text(
        json.dumps(informe, ensure_ascii=False, indent=2, default=str) + "\n"
    )
    if any(r["sobrantes"] or r["faltantes"] or r["duplicadas"] for r in resultados):
        raise SystemExit("La auditoría detectó diferencias; revisar el informe.")


if __name__ == "__main__":
    main()
