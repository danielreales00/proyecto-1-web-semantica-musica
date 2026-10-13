"""Relaciones musicales, créditos ordenados y publicaciones calificadas."""

from rdflib.namespace import XSD

from musica.etapa2.escritura import huella
from musica.etapa2.vocabulario import MUS


def creditos(modelo):
    d, e = modelo.d, modelo.e
    for tabla in (
        "creditos_grabaciones_masivos",
        "creditos_grabacion",
        "creditos_grupo_lanzamiento",
    ):
        for f in d.filas(tabla):
            if "grupo_lanzamiento_mbid" in f:
                sujetos = [e.entidad("GrupoLanzamientos", f["grupo_lanzamiento_mbid"])]
            else:
                sujetos = modelo.registros(f["recording_mbid"])
            artista = e.entidad("Artista", f["artist_mbid"], f.get("nombre", ""))
            for sujeto in sujetos:
                clave = huella(
                    [
                        str(sujeto),
                        str(d.capturas[tabla]),
                        f["orden"],
                        f["artist_mbid"],
                        f["nombre_acreditado"],
                        f["union"],
                    ]
                )
                credito = e.entidad(
                    "CreditoArtistico",
                    clave,
                    f"Crédito {f['orden']} de {sujeto.rsplit('/', 1)[-1]} ({f['nombre_acreditado']})",
                    "es",
                    True,
                )
                e.triple(sujeto, MUS.tieneCredito, credito)
                e.triple(credito, MUS.acreditaEntidad, sujeto)
                e.triple(credito, MUS.artistaAcreditado, artista)
                e.dato(credito, "posicionCredito", f["orden"], XSD.positiveInteger)
                e.dato(credito, "nombreAcreditado", f["nombre_acreditado"])
                e.dato(credito, "fraseUnion", f["union"])
                d.respaldar(credito, tabla, f)


def publicaciones(modelo):
    d, e = modelo.d, modelo.e
    for tabla in ("grabacion_lanzamiento_masivo", "grabacion_lanzamiento"):
        for f in d.filas(tabla):
            lanzamiento = e.entidad("Lanzamiento", f["release_mbid"])
            for grabacion in modelo.registros(f["recording_mbid"]):
                e.triple(grabacion, MUS.apareceEn, lanzamiento)
                d.respaldar(grabacion, tabla, f)
    tabla = "lanzamiento_sello_masivo"
    for f in d.filas(tabla):
        lanzamiento = e.entidad("Lanzamiento", f["release_mbid"])
        publicacion = e.entidad(
            "PublicacionDiscografica",
            huella(
                [
                    f["release_mbid"],
                    f["label_mbid"],
                    f["numero_catalogo"],
                    str(d.capturas[tabla]),
                ]
            ),
            f"Publicación {f['release_mbid']} catálogo {f['numero_catalogo'] or 'no indicado'}",
            "es",
            True,
        )
        e.triple(lanzamiento, MUS.tienePublicacion, publicacion)
        e.dato(publicacion, "numeroCatalogo", f["numero_catalogo"])
        d.respaldar(publicacion, tabla, f)
        if f["label_mbid"]:
            sello = e.entidad("SelloDiscografico", f["label_mbid"])
            e.triple(publicacion, MUS.selloPublicacion, sello)
            # Hecho explícito de la misma fila; no exige activar un razonador.
            e.triple(lanzamiento, MUS.publicadoPor, sello)


MAPA = {
    ("artista", "composer", "obra"): "compuso",
    ("artista", "producer", "grabacion"): "produjo",
    ("grabacion", "performance", "obra"): "interpretaObra",
}
TIPOS = {"artista": "Artista", "obra": "ObraMusical"}


def extremos(modelo, tipo, mbid, nombre=""):
    if tipo == "grabacion":
        return modelo.registros(mbid)
    return [modelo.e.entidad(TIPOS[tipo], mbid, nombre)]


def relacion(modelo, tabla, fila, sujeto_tipo, sujeto, objeto_tipo, objeto, nombre=""):
    propiedad = MAPA.get((sujeto_tipo, fila["relacion"], objeto_tipo))
    if not propiedad:
        modelo.d.omitidas[tabla] += 1
        return
    for s in extremos(modelo, sujeto_tipo, sujeto):
        for o in extremos(modelo, objeto_tipo, objeto, nombre):
            modelo.e.triple(s, MUS[propiedad], o)
            modelo.d.respaldar(s, tabla, fila)


def relaciones(modelo):
    tabla = "relaciones_musicales_masivas"
    for f in modelo.d.filas(tabla):
        relacion(
            modelo,
            tabla,
            f,
            f["sujeto_tipo"],
            f["sujeto_mbid"],
            f["objeto_tipo"],
            f["objeto_mbid"],
        )
    tabla = "relaciones_musicbrainz"
    for f in modelo.d.filas(tabla):
        objeto_tipo = {
            "artist": "artista",
            "work": "obra",
            "recording": "grabacion",
        }.get(f["objeto_tipo"], f["objeto_tipo"])
        if f["direccion"] == "backward":
            relacion(
                modelo,
                tabla,
                f,
                objeto_tipo,
                f["objeto_id"],
                f["sujeto_tipo"],
                f["sujeto_id"],
            )
        else:
            relacion(
                modelo,
                tabla,
                f,
                f["sujeto_tipo"],
                f["sujeto_id"],
                objeto_tipo,
                f["objeto_id"],
                f["objeto_nombre"],
            )
