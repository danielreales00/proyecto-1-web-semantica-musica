"""Selecciona extractos reproducibles y añade nombres desde los CSV fuente."""

import csv
import json

from musica.comun.rutas import ROOT


def elegir_distintos(filas, campo):
    elegidas, vistos = [], set()
    for fila in filas:
        if fila[campo] not in vistos:
            elegidas.append(fila)
            vistos.add(fila[campo])
        if len(elegidas) == 2:
            break
    return elegidas


def seleccionar(n, rs, labels):
    first = list(rs[0])[0]
    if n in [2, 3, 4, 5, 6]:
        targets = sorted(
            {r[first] for r in rs},
            key=lambda uri: (
                len(labels.get(uri.rsplit("/", 1)[-1], "")) or 999,
                uri,
            ),
        )
        if n == 3:
            targets = [
                t for t in targets if all(r["compositor"] for r in rs if r[first] == t)
            ]
        target = targets[0]
        if n == 4:
            target = "https://example.org/musica/Grabacion/TRAABFT128F931150E"
        if n == 5:
            target = next(
                t for t in targets if labels.get(t.rsplit("/", 1)[-1]) == "Atlantic"
            )
        sample = [r for r in rs if r[first] == target]
        # Dos identificadores distintos demuestran el umbral; no seleccionar dos catálogos de una sola edición.
        secondary = {
            2: "artista",
            3: "mbid",
            4: "lanzamiento",
            5: "lanzamiento",
            6: "persona",
        }[n]
        chosen = elegir_distintos(sample, secondary)
        if n == 6:
            chosen = sample[:1]
    else:
        chosen = rs[:2]
    if n == 8:
        chosen = (
            [r for r in rs if r["genero"].endswith("/tagtraum/Rock")]
            + [r for r in rs if int(r["artistas"]) > 500][:1]
            + [r for r in rs if int(r["grupos"]) > 500][:1]
        )
    return chosen


def main():
    root = ROOT
    inp = root / "output/csv"
    results = root / "output/etapa2/consultas"

    def rows(name):
        with (inp / (name + ".csv")).open(encoding="utf-8", newline="") as archivo:
            return list(csv.DictReader(archivo))

    labels = {}
    for name, key, col in [
        ("canciones", "track_id", "title"),
        ("artistas", "artist_mbid", "nombre_musicbrainz"),
        ("artistas_masivos", "artist_mbid", "nombre"),
        ("obras", "work_mbid", "titulo"),
        ("obras_masivas", "work_mbid", "titulo"),
        ("lanzamientos", "release_mbid", "titulo"),
        ("lanzamientos_masivos", "release_mbid", "titulo"),
        ("grupos_lanzamientos", "grupo_lanzamiento_mbid", "titulo"),
        ("sellos_masivos", "label_mbid", "nombre"),
    ]:
        for r in rows(name):
            if r[col]:
                labels[r[key]] = r[col]
    allrows = {
        n: list(csv.DictReader(next(results.glob(f"{n:02d}*.csv")).open()))
        for n in range(1, 9)
    }
    examples = {}
    for n, rs in allrows.items():
        chosen = seleccionar(n, rs, labels)
        examples[n] = [
            dict(
                r,
                **{
                    k + "_etiqueta": labels[v.rsplit("/", 1)[-1]]
                    for k, v in r.items()
                    if v.rsplit("/", 1)[-1] in labels
                },
            )
            for r in chosen
        ]
    # Las etiquetas se añaden desde los CSV, sin alterar los valores devueltos.
    print(json.dumps(examples, ensure_ascii=False, indent=2))
    (root / "output/etapa2/muestras_consultas.json").write_text(
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
