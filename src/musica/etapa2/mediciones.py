"""Géneros por sujeto y mediciones independientes por análisis."""

from rdflib.namespace import XSD

from musica.etapa2.escritura import huella
from musica.etapa2.vocabulario import ACOUSTICBRAINZ, JMIR, MUS


def asignar(
    modelo, sujeto, tabla, fila, vocabulario, identificador, nombre, idioma="und"
):
    e, d = modelo.e, modelo.d
    genero = e.entidad("GeneroMusical", (vocabulario, identificador), nombre, idioma)
    clave = huella(
        [str(sujeto), str(genero), fila.get("papel", ""), str(d.capturas[tabla])]
    )
    asignacion = e.entidad(
        "AsignacionGenero",
        clave,
        f"Asignación de {nombre or identificador} a {sujeto.rsplit('/', 1)[-1]}",
        "es",
        True,
    )
    e.triple(sujeto, MUS.tieneAsignacionGenero, asignacion)
    e.triple(asignacion, MUS.generoAsignado, genero)
    e.dato(asignacion, "papelGenero", fila.get("papel"))
    e.dato(asignacion, "votosGenero", fila.get("votos"), XSD.integer)
    d.respaldar(asignacion, tabla, fila)
    d.respaldar(genero, tabla, fila)


def generos(modelo):
    tabla = "cancion_genero"
    for f in modelo.d.filas(tabla):
        asignar(
            modelo,
            modelo.locales[f["track_id"]],
            tabla,
            f,
            "tagtraum",
            f["genero"],
            f["genero"],
        )
    tabla = "grupo_lanzamiento_genero"
    for f in modelo.d.filas(tabla):
        grupo = modelo.e.entidad("GrupoLanzamientos", f["grupo_lanzamiento_mbid"])
        asignar(
            modelo,
            grupo,
            tabla,
            f,
            "musicbrainz",
            f["genero_mbid"] or f["genero"],
            f["genero"],
        )
    tabla = "wikidata_hechos"
    for f in modelo.d.filas(tabla):
        if (
            f["propiedad"] != "P136"
            or f["estado_correspondencia"] != "unica"
            or f["tipo_valor"] != "uri"
        ):
            modelo.d.omitidas[tabla] += 1
            continue
        artista = modelo.e.entidad("Artista", f["artist_mbid"])
        asignar(
            modelo,
            artista,
            tabla,
            f,
            "wikidata",
            f["valor"].rsplit("/", 1)[-1],
            f["etiqueta_valor"],
            f["idioma_etiqueta"] or "und",
        )


def nuevo_analisis(modelo, tabla, clave, nombre, fila):
    recurso = modelo.e.entidad(
        "AnalisisAcustico",
        huella([tabla, str(modelo.d.capturas[tabla]), clave]),
        nombre,
        "es",
        True,
    )
    modelo.d.respaldar(recurso, tabla, fila)
    return recurso


def jmir(modelo):
    tabla = "descriptores_acusticos"
    for f in modelo.d.filas(tabla):
        analisis = nuevo_analisis(
            modelo, tabla, f["track_id"], f"Análisis jMIR de {f['track_id']}", f
        )
        modelo.e.triple(modelo.locales[f["track_id"]], MUS.tieneAnalisis, analisis)
        modelo.e.dato(analisis, "alcanceAnalisis", "fragmento")
        for columna, nombre, _ in JMIR:
            for prefijo, sufijo in (
                ("media", "Overall_Average"),
                ("desviacion", "Overall_Standard_Deviation"),
            ):
                modelo.e.dato(
                    analisis, prefijo + nombre, f[f"{columna}_{sufijo}_1"], XSD.decimal
                )


def acousticbrainz(modelo):
    for tabla in ("acousticbrainz_masivo", "acousticbrainz"):
        for f in modelo.d.filas(tabla):
            registros = modelo.registros(f["recording_mbid"])
            if not registros:
                modelo.d.omitidas[tabla] += 1
                continue
            clave = [
                f["recording_mbid"],
                f.get("submission_offset"),
                f.get("fecha_consulta"),
            ]
            analisis = nuevo_analisis(
                modelo,
                tabla,
                clave,
                f"Análisis AcousticBrainz de {f['recording_mbid']} ({tabla})",
                f,
            )
            for registro in registros:
                modelo.e.triple(registro, MUS.tieneAnalisis, analisis)
            modelo.e.dato(analisis, "mbid", f["recording_mbid"])
            modelo.e.dato(
                analisis,
                "indiceAnalisis",
                f.get("submission_offset"),
                XSD.nonNegativeInteger,
            )
            # No se supone que el audio sea completo: la fuente no lo garantiza.
            modelo.e.dato(
                analisis,
                "alcanceAnalisis",
                "audio enviado a AcousticBrainz; extensión no verificada",
            )
            modelo.e.dato(analisis, "tonica", f.get("key_key") or f.get("tonalidad"))
            modelo.e.dato(analisis, "modo", f.get("key_scale") or f.get("escala"))
            for columna, propiedad, _ in ACOUSTICBRAINZ:
                modelo.e.dato(analisis, propiedad, f.get(columna), XSD.decimal)
