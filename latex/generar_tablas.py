"""Genera tablas LaTeX exclusivamente desde métricas y resultados conservados."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "tablas"
OUT.mkdir(exist_ok=True)


def read(path):
    return json.loads((ROOT / path).read_text())


def esc(s):
    return "".join(
        {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }.get(c, c)
        for c in str(s)
    )


def n(v):
    return f"{int(v):,}".replace(",", ".")


def table(name, caption, label, columns, headers, rows, note=""):
    lines = [
        r"\begin{center}\small",
        r"\captionof{table}{" + caption + "}" + r"\label{" + label + "}",
        r"\begin{tabularx}{\linewidth}{@{}" + columns + "@{}}",
        r"\toprule",
        " & ".join(r"\textbf{" + esc(h) + "}" for h in headers) + r" \\",
        r"\midrule",
    ]
    lines += [" & ".join(esc(x) for x in row) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabularx}"]
    if note:
        lines.append(r"\par\smallskip{\footnotesize " + note + "}")
    lines += [r"\end{center}"]
    (OUT / (name + ".tex")).write_text("\n".join(lines) + "\n")


r = read("docs/resultados.json")
s = read("output/sparql/resumen.json")
q1 = read("output/sparql/01_descriptores_cancion.json")
q2 = read("output/sparql/02_cobertura_descriptores.json")
q3 = read("output/sparql/03_tempo_mayor_120.json")
q4 = read("output/sparql/04_varios_lanzamientos.json")
assert r["canciones_conservadas"] == 100000
assert len(q1) == 16 and len(q2) == 16 and all(int(x["cantidad"]) == 99465 for x in q2)
assert len(q3) == 20 and s["resultados_verificados_con_csv"]
states = r["estados_reconciliacion"]
labels = [
    ("jMIR: 16 descriptores", "jmir"),
    ("tagtraum: géneros de canción", "tagtraum"),
    ("Wikidata: propiedades de artista", "wikidata_artista"),
    ("MusicBrainz: metadatos de artista", "musicbrainz_artista_completo"),
    ("MusicBrainz: grabación identificada", "musicbrainz_grabacion_completo"),
    ("MusicBrainz: grupo de lanzamientos", "musicbrainz_grupo_lanzamiento"),
    ("AcousticBrainz: hasta 14 características", "acousticbrainz_dump"),
]
rows = [
    [
        label,
        n(r["cobertura_por_fuente"][k]),
        f"{r['cobertura_por_fuente'][k] / 1000:.3f}".replace(".", ",") + " %",
    ]
    for label, k in labels
]
rows.append(
    [
        "Unión de fuentes",
        n(r["canciones_enriquecidas"]),
        f"{r['canciones_enriquecidas'] / 1000:.3f}".replace(".", ",") + " %",
    ]
)
table(
    "cobertura",
    "Cobertura sobre las 100.000 canciones, con categorías superpuestas.",
    "tab:cobertura",
    "Y r r",
    ["Aporte", "Canciones", "Cobertura"],
    rows,
)
rows = []
for x in q3[:3]:
    rows.append(
        [
            "Q3",
            x["titulo"],
            str(Decimal(x["bpm"]).quantize(Decimal("0.001"))).replace(".", ",")
            + " BPM",
        ]
    )
for x in q4[:3]:
    rows.append(["Q4", x["titulo"], x["cantidad"] + " lanzamientos"])
# Tabla técnica del anexo: nombres exactos y una instancia consultada.
vals = {x["descriptor"]: x["valor"] for x in q1}
features = [
    "Spectral_Centroid",
    "Spectral_Rolloff_Point",
    "Spectral_Flux",
    "Compactness",
    "Spectral_Variability",
    "Root_Mean_Square",
    "Fraction_Of_Low_Energy_Windows",
    "Zero_Crossings",
]
table(
    "descriptores",
    "Valores de Q1 para TRMMMCJ128F930BFF8.",
    "tab:descriptores",
    "Y r r",
    ["Nombre base del descriptor", "Promedio", "Desviación estándar"],
    [
        [
            f.replace("_", " "),
            vals[f + "_Overall_Average_1"],
            vals[f + "_Overall_Standard_Deviation_1"],
        ]
        for f in features
    ],
)
q6 = read("output/sparql/06_compositores.json")
q7 = read("output/sparql/07_generos_albumes.json")
am = read("output/sparql/resumen_ampliacion.json")
assert am["resultados_verificados_con_csv"] and q6 and q7
examples = [["Compositor", x["nombre"], n(x["canciones"])] for x in q6[:3]] + [
    ["Género del grupo", x["genero"], n(x["canciones"])] for x in q7[:3]
]
table(
    "evidencia_ampliacion",
    "Primeras tres filas de dos consultas sobre la ampliación.",
    "tab:evidencia_ampliacion",
    "p{3.0cm} Y r",
    ["Consulta", "Entidad o etiqueta", "Canciones"],
    examples,
)
q8 = read("output/sparql/08_tonalidades_volcado.json")
assert read("output/sparql/resumen_acousticbrainz.json")[
    "resultados_verificados_con_csv"
]
acoustic_examples = [["Compositor", x["nombre"], n(x["canciones"])] for x in q6[:3]] + [
    ["Tonalidad y escala", x["tonalidad"] + " / " + x["escala"], n(x["canciones"])]
    for x in q8[:3]
]
table(
    "tonalidades",
    "Primeras cinco filas de Q8, con el análisis de índice cero.",
    "tab:tonalidades",
    "Y Y r",
    ["Tonalidad", "Escala", "Canciones"],
    [[x["tonalidad"], x["escala"], n(x["canciones"])] for x in q8[:5]],
)
mb = r["ampliacion_grabaciones"]

# Las tablas de aportes distinguen valores/relaciones de canciones alcanzadas.
# Se recorren los CSV finales para comprobar cada cifra y conservar sus huellas.
source_hashes = {}


def csv_rows(name):
    path = ROOT / "output/csv" / (name + ".csv")
    with path.open("rb") as stream:
        source_hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


songs = list(csv_rows("canciones"))
assert len(songs) == 100000 and len({x["track_id"] for x in songs}) == 100000
by_rec = defaultdict(set)
by_artist = defaultdict(set)
by_group = defaultdict(set)
for song in songs:
    by_artist[song["artist_mbid"]].add(song["track_id"])
    if song["recording_mbid_dump"]:
        by_rec[song["recording_mbid_dump"]].add(song["track_id"])
    if song["grupo_lanzamiento_mbid"]:
        by_group[song["grupo_lanzamiento_mbid"]].add(song["track_id"])
relations = list(csv_rows("relaciones_musicales_masivas"))
by_work = defaultdict(set)
for rel in relations:
    if (
        rel["relacion"] == "performance"
        and rel["sujeto_tipo"] == "grabacion"
        and rel["objeto_tipo"] == "obra"
    ):
        by_work[rel["objeto_mbid"]].update(by_rec[rel["sujeto_mbid"]])
assert dict(Counter(x["relacion"] for x in relations)) == mb["relaciones_por_tipo"]
contributions = []


def contribution(source, kind, label, amount, covered, unit):
    contributions.append(
        {
            "fuente": source,
            "tipo": kind,
            "aporte": label,
            "cantidad": amount,
            "unidad": unit,
            "canciones": len(covered),
        }
    )


jm = list(csv_rows("descriptores_acusticos"))
jm_values = sum(
    bool(value) for row in jm for key, value in row.items() if "_Overall_" in key
)
assert jm_values == 16 * r["cobertura_por_fuente"]["jmir"]
contribution(
    "jMIR",
    "descriptores",
    "Canción: valores de 16 descriptores",
    jm_values,
    {x["track_id"] for x in jm},
    "valores no vacíos",
)
genres = list(csv_rows("cancion_genero"))
assert len(genres) == r["relaciones_genero"]
contribution(
    "tagtraum",
    "generos",
    "Canción: asignación de género",
    len(genres),
    {x["track_id"] for x in genres},
    "asignaciones con papel mayoritario/minoritario",
)
role_counts = {}
for role, label in [
    ("performance", "Grabación: interpretación de obra"),
    ("composer", "Artista: composición de obra"),
    ("lyricist", "Artista: letra de obra"),
    ("producer", "Artista: producción de grabación"),
    ("instrument", "Artista: instrumento en grabación"),
]:
    selected = [x for x in relations if x["relacion"] == role]
    covered = set()
    for rel in selected:
        for side in ["sujeto", "objeto"]:
            if rel[side + "_tipo"] == "grabacion":
                covered.update(by_rec[rel[side + "_mbid"]])
            elif rel[side + "_tipo"] == "obra":
                covered.update(by_work[rel[side + "_mbid"]])
    role_counts[role] = len(covered)
    contribution(
        "MusicBrainz",
        role,
        label,
        len(selected),
        covered,
        "filas de relación con identificador propio",
    )
assert role_counts["performance"] == mb["canciones_con_obra"]
assert role_counts["composer"] == am["canciones_con_compositor"]
group_genres = list(csv_rows("grupo_lanzamiento_genero"))
covered = set()
for row in group_genres:
    covered.update(by_group[row["grupo_lanzamiento_mbid"]])
assert len(group_genres) == r["ampliacion_albumes"]["relaciones_genero"]
assert len(covered) == r["ampliacion_albumes"]["canciones_con_genero_del_grupo"]
contribution(
    "MusicBrainz",
    "genero_grupo",
    "Grupo de lanzamientos: género",
    len(group_genres),
    covered,
    "asignaciones de género al grupo",
)
facts = list(csv_rows("wikidata_hechos"))
for prop, label in [
    ("P136", "Artista: género musical"),
    ("P264", "Artista: sello discográfico"),
    ("P27", "Artista: ciudadanía"),
]:
    selected = [x for x in facts if x["propiedad"] == prop]
    covered = set()
    for row in selected:
        covered.update(by_artist[row["artist_mbid"]])
    expected = r["ampliacion_artistas"]["por_propiedad"][prop]
    assert len(selected) == expected["hechos"] and len(covered) == expected["canciones"]
    contribution(
        "Wikidata",
        prop,
        label,
        len(selected),
        covered,
        "afirmaciones simples de la propiedad",
    )
acoustic = list(csv_rows("acousticbrainz_masivo"))
covered = set()
for row in acoustic:
    covered.update(by_rec[row["recording_mbid"]])
ab = r["ampliacion_acousticbrainz"]
assert (
    len(acoustic) == ab["grabaciones_con_datos"]
    and len(covered) == ab["canciones_con_datos"]
)
contribution(
    "AcousticBrainz",
    "analisis",
    "Grabación: análisis elegido (índice 0)",
    len(acoustic),
    covered,
    "análisis seleccionados, uno por grabación",
)
ac_values = sum(
    bool(row[field]) for row in acoustic for field in ab["campos_caracteristicas"]
)
assert ac_values == ab["valores_no_vacios_grabaciones"]
contribution(
    "AcousticBrainz",
    "valores",
    "Análisis: valores de hasta 14 campos",
    ac_values,
    covered,
    "valores no vacíos por grabación",
)
table(
    "aportes_por_fuente",
    "Relaciones y valores vinculados a la entrada, por fuente.",
    "tab:aportes",
    r"p{2.7cm} Y r r",
    ["Fuente", "Relación o aporte", "Cantidad", "Canciones"],
    [
        [x["fuente"], x["aporte"], n(x["cantidad"]), n(x["canciones"])]
        for x in contributions
    ],
)
table(
    "estados_vinculacion",
    "Estados finales de vinculación; cada bloque suma 100.000 canciones.",
    "tab:estados_vinculacion",
    r"p{3.0cm} Y r",
    ["Proceso", "Estado", "Canciones"],
    [
        ["MusicBrainz", "Grabación aceptada", n(mb["estados"]["aceptada"])],
        ["MusicBrainz", "Ambigua: no se acepta un MBID", n(mb["estados"]["ambigua"])],
        [
            "MusicBrainz",
            "Sin coincidencia conservadora",
            n(mb["estados"]["sin_coincidencia_conservadora"]),
        ],
        ["AcousticBrainz", "Datos vinculados", n(ab["estados"]["disponible"])],
        [
            "AcousticBrainz",
            "Grabación aceptada sin datos en el volcado",
            n(ab["estados"]["sin_datos_en_volcado"]),
        ],
        [
            "AcousticBrainz",
            "Sin grabación previamente reconciliada",
            n(ab["estados"]["sin_grabacion_reconciliada"]),
        ],
    ],
)
q5 = read("output/sparql/05_propiedades_artistas.json")
wd_label = next(x for x in q5 if x["propiedad"].endswith("/P264"))
dylan = next(x for x in q6 if x["nombre"] == "Bob Dylan")
rock = next(x for x in q7 if x["genero"] == "rock")
tonal = next(x for x in q8 if x["tonalidad"] == "C" and x["escala"] == "major")
table(
    "evidencia_fuentes",
    "Ejemplos de resultados SPARQL, contando canciones distintas.",
    "tab:evidencia_fuentes",
    r">{\raggedright\arraybackslash}p{3.6cm} Y r",
    ["Consulta / fuente", "Ruta consultada y resultado", "Canciones"],
    [
        [
            "Q5 / Wikidata",
            "Artista con algún sello declarado (P264)",
            n(wd_label["canciones"]),
        ],
        [
            "Q6 / MusicBrainz",
            "Grabación y obra con compositor Bob Dylan",
            n(dylan["canciones"]),
        ],
        [
            "Q7 / MusicBrainz",
            "Grupo de lanzamientos con género rock",
            n(rock["canciones"]),
        ],
        [
            "Q8 / AcousticBrainz",
            "Análisis con tonalidad C y escala major",
            n(tonal["canciones"]),
        ],
    ],
)
(ROOT / "docs/relaciones_por_fuente.json").write_text(
    json.dumps(
        {
            "comprobado_con_csv": True,
            "aportes": contributions,
            "fuentes_sha256": source_hashes,
            "nota": "Las cantidades no se suman: mezclan filas de relaciones, asignaciones y valores, con su unidad explícita. Canciones cuenta track_id distintos alcanzados mediante las rutas documentadas.",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
values = {
    "TotalEnriquecidas": r["canciones_enriquecidas"],
    "NumeroTablas": r["tablas_csv"],
    "GrabacionesMasivas": mb["grabaciones"],
    "ObrasMasivas": mb["obras"],
    "CancionesObra": mb["canciones_con_obra"],
    "CancionesCompositor": am["canciones_con_compositor"],
}
values.update(
    CancionesAcousticBrainz=r["ampliacion_acousticbrainz"]["canciones_con_datos"],
    GrabacionesAcousticBrainz=r["ampliacion_acousticbrainz"]["grabaciones_con_datos"],
    CancionesTempoRapido=r["ampliacion_acousticbrainz"]["canciones_bpm_mayor_120"],
)
values.update(
    CancionesProductor=role_counts["producer"],
    CancionesInstrumento=role_counts["instrument"],
    RelacionesProductor=mb["relaciones_por_tipo"]["producer"],
    RelacionesInstrumento=mb["relaciones_por_tipo"]["instrument"],
    RelacionesMusicales=mb["relaciones"],
    CancionesContextoArtista=r["canciones_con_metadatos_artista_union"],
    CancionesSinEnriquecer=r["canciones_sin_enriquecer"],
    CancionesMB=mb["estados"]["aceptada"],
    CancionesMBAmbiguas=mb["estados"]["ambigua"],
    CancionesMBSinCoincidencia=mb["estados"]["sin_coincidencia_conservadora"],
)
(OUT / "cifras.tex").write_text(
    "\n".join(
        chr(92) + "newcommand{" + chr(92) + key + "}{" + n(value) + "}"
        for key, value in values.items()
    )
    + "\n"
)
print("Tablas y cifras generadas a partir de resultados verificados.")
