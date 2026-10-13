"""Catálogo del dominio: una única definición para código y documentación.

Una tupla de clases como dominio representa su unión, nunca su intersección.
Los nombres de propiedades se mantienen independientes de las columnas CSV.
"""

from dataclasses import dataclass

from rdflib import Namespace

MUS = Namespace("https://example.org/musica/")


@dataclass(frozen=True)
class Clase:
    nombre: str
    etiqueta: str
    descripcion: str
    padre: str | None = None


@dataclass(frozen=True)
class Propiedad:
    nombre: str
    etiqueta: str
    dominio: tuple[str, ...]
    rango: str
    descripcion: str
    dato: bool = False


CLASES = (
    Clase(
        "Artista",
        "Artista",
        "Participante musical; sus roles se expresan mediante relaciones.",
    ),
    Clase(
        "Persona",
        "Persona",
        "Artista individual identificado explícitamente por la fuente.",
        "Artista",
    ),
    Clase(
        "Agrupacion",
        "Agrupación",
        "Artista colectivo identificado explícitamente por la fuente.",
        "Artista",
    ),
    Clase(
        "ObraMusical",
        "Obra musical",
        "Composición abstracta que puede tener varias grabaciones.",
    ),
    Clase(
        "Grabacion",
        "Grabación",
        "Realización sonora; su URI local se conserva al reconciliarla.",
    ),
    Clase(
        "Lanzamiento",
        "Lanzamiento",
        "Edición publicada, no un ejemplar físico individual.",
    ),
    Clase(
        "GrupoLanzamientos",
        "Grupo de lanzamientos",
        "Identidad musical que reúne ediciones relacionadas.",
    ),
    Clase(
        "Album",
        "Álbum",
        "Grupo cuyo tipo primario declarado es Album.",
        "GrupoLanzamientos",
    ),
    Clase(
        "Sencillo",
        "Sencillo",
        "Grupo cuyo tipo primario declarado es Single.",
        "GrupoLanzamientos",
    ),
    Clase("EP", "EP", "Grupo cuyo tipo primario declarado es EP.", "GrupoLanzamientos"),
    Clase(
        "SelloDiscografico",
        "Sello discográfico",
        "Sello asociado a una edición publicada.",
    ),
    Clase(
        "PublicacionDiscografica",
        "Publicación discográfica",
        "Asociación entre edición y sello que conserva su número de catálogo.",
    ),
    Clase(
        "GeneroMusical",
        "Género musical",
        "Clasificación identificada dentro de su vocabulario de origen.",
    ),
    Clase(
        "CreditoArtistico",
        "Crédito artístico",
        "Artista acreditado en una grabación o grupo, con nombre y orden publicados.",
    ),
    Clase(
        "AsignacionGenero",
        "Asignación de género",
        "Clasificación con fuente y calificadores como papel o votos.",
    ),
    Clase(
        "AnalisisAcustico",
        "Análisis acústico",
        "Mediciones de un mismo análisis, fuente, índice y alcance.",
    ),
    Clase("Fuente", "Fuente", "Proveedor de información."),
    Clase(
        "CapturaFuente",
        "Captura de fuente",
        "Archivo, respuesta o instantánea utilizada como evidencia.",
    ),
    Clase(
        "Correspondencia",
        "Correspondencia",
        "Decisión de reconciliación con estado y método; no es identidad por sí sola.",
    ),
)

ACREDITABLE = ("Grabacion", "GrupoLanzamientos")
CLASIFICABLE = ("Grabacion", "Artista", "GrupoLanzamientos")

OBJETO = (
    Propiedad(
        "compuso",
        "compuso",
        ("Artista",),
        "ObraMusical",
        "Composición respaldada explícitamente por la fuente.",
    ),
    Propiedad(
        "produjo",
        "produjo",
        ("Artista",),
        "Grabacion",
        "Producción respaldada explícitamente por la fuente.",
    ),
    Propiedad(
        "interpretaObra",
        "interpreta obra",
        ("Grabacion",),
        "ObraMusical",
        "Obra realizada por una grabación.",
    ),
    Propiedad(
        "tieneGrabacion",
        "tiene grabación",
        ("ObraMusical",),
        "Grabacion",
        "Grabación que realiza una obra.",
    ),
    Propiedad(
        "apareceEn",
        "aparece en",
        ("Grabacion",),
        "Lanzamiento",
        "Edición que contiene la grabación.",
    ),
    Propiedad(
        "contieneGrabacion",
        "contiene grabación",
        ("Lanzamiento",),
        "Grabacion",
        "Grabación incluida en una edición.",
    ),
    Propiedad(
        "perteneceAGrupo",
        "pertenece a grupo",
        ("Lanzamiento",),
        "GrupoLanzamientos",
        "Agrupación editorial de una edición.",
    ),
    Propiedad(
        "tieneLanzamiento",
        "tiene lanzamiento",
        ("GrupoLanzamientos",),
        "Lanzamiento",
        "Edición perteneciente a un grupo.",
    ),
    Propiedad(
        "publicadoPor",
        "publicado por",
        ("Lanzamiento",),
        "SelloDiscografico",
        "Sello que publica una edición; el catálogo se conserva en la asociación.",
    ),
    Propiedad(
        "tienePublicacion",
        "tiene publicación",
        ("Lanzamiento",),
        "PublicacionDiscografica",
        "Asociación editorial con sello y catálogo.",
    ),
    Propiedad(
        "selloPublicacion",
        "sello de publicación",
        ("PublicacionDiscografica",),
        "SelloDiscografico",
        "Sello correspondiente a esta asociación editorial.",
    ),
    Propiedad(
        "tieneCredito",
        "tiene crédito",
        ACREDITABLE,
        "CreditoArtistico",
        "Crédito publicado para una grabación o grupo.",
    ),
    Propiedad(
        "acreditaEntidad",
        "acredita entidad",
        ("CreditoArtistico",),
        "@acreditable",
        "Entidad musical a la que pertenece el crédito.",
    ),
    Propiedad(
        "artistaAcreditado",
        "artista acreditado",
        ("CreditoArtistico",),
        "Artista",
        "Artista del crédito; no implica composición ni producción.",
    ),
    Propiedad(
        "tieneAsignacionGenero",
        "tiene asignación de género",
        CLASIFICABLE,
        "AsignacionGenero",
        "Clasificación explícita, sin herencia entre entidades musicales.",
    ),
    Propiedad(
        "generoAsignado",
        "género asignado",
        ("AsignacionGenero",),
        "GeneroMusical",
        "Género de una asignación individual.",
    ),
    Propiedad(
        "tieneAnalisis",
        "tiene análisis",
        ("Grabacion",),
        "AnalisisAcustico",
        "Análisis que describe el audio de esta grabación.",
    ),
    Propiedad(
        "fuente",
        "fuente",
        ("owl:Thing",),
        "Fuente",
        "Proveedor del recurso; dominio amplio para dominio y evidencia.",
    ),
    Propiedad(
        "respaldadoPor",
        "respaldado por",
        ("owl:Thing",),
        "CapturaFuente",
        "Captura que respalda el recurso; no representa una afirmación genérica.",
    ),
    Propiedad(
        "tieneCorrespondencia",
        "tiene correspondencia",
        ("Grabacion",),
        "Correspondencia",
        "Decisión externa asociada a la referencia local.",
    ),
)


def dato(nombre, etiqueta, dominio, rango, descripcion):
    """Construye una propiedad literal con dominio declarado."""
    return Propiedad(nombre, etiqueta, dominio, rango, descripcion, dato=True)


DATOS = (
    dato(
        "titulo",
        "título",
        ("Grabacion", "ObraMusical", "Lanzamiento", "GrupoLanzamientos"),
        "string",
        "Título publicado; no establece identidad.",
    ),
    dato(
        "identificador",
        "identificador",
        ("owl:Thing",),
        "string",
        "Identificador en su sistema de origen; no es una clave OWL.",
    ),
    dato(
        "mbid",
        "MBID",
        ("owl:Thing",),
        "string",
        "Identificador MusicBrainz respaldado por la fuente.",
    ),
    dato(
        "nombreAcreditado",
        "nombre acreditado",
        ("CreditoArtistico",),
        "string",
        "Nombre utilizado en el crédito original.",
    ),
    dato(
        "posicionCredito",
        "posición del crédito",
        ("CreditoArtistico",),
        "positiveInteger",
        "Orden publicado, normalizado a base uno.",
    ),
    dato(
        "fraseUnion",
        "frase de unión",
        ("CreditoArtistico",),
        "string",
        "Texto que une este crédito con el siguiente.",
    ),
    dato(
        "numeroCatalogo",
        "número de catálogo",
        ("PublicacionDiscografica",),
        "string",
        "Número del par edición-sello, conservado literalmente.",
    ),
    dato(
        "papelGenero",
        "papel del género",
        ("AsignacionGenero",),
        "string",
        "Papel original: mayoritario o minoritario cuando la fuente lo declara.",
    ),
    dato(
        "votosGenero",
        "votos del género",
        ("AsignacionGenero",),
        "integer",
        "Votos reportados por la fuente; no son una probabilidad.",
    ),
    dato(
        "indiceAnalisis",
        "índice del análisis",
        ("AnalisisAcustico",),
        "nonNegativeInteger",
        "Índice de envío o análisis dentro de la fuente.",
    ),
    dato(
        "alcanceAnalisis",
        "alcance del análisis",
        ("AnalisisAcustico",),
        "string",
        "Alcance del audio analizado, por ejemplo fragmento.",
    ),
    dato(
        "tonica",
        "tónica",
        ("AnalisisAcustico",),
        "string",
        "Clave tonal literal de la fuente; C representa do en AcousticBrainz.",
    ),
    dato(
        "modo",
        "modo",
        ("AnalisisAcustico",),
        "string",
        "Modo tonal literal; major representa mayor en AcousticBrainz.",
    ),
    dato(
        "estadoCorrespondencia",
        "estado de correspondencia",
        ("Correspondencia",),
        "string",
        "Estado original: aceptada, ambigua o sin coincidencia conservadora.",
    ),
    dato(
        "metodoCorrespondencia",
        "método de correspondencia",
        ("Correspondencia",),
        "string",
        "Método utilizado en la reconciliación.",
    ),
    dato(
        "candidatoMBID",
        "MBID candidato",
        ("Correspondencia",),
        "string",
        "Identificador candidato; no afirma identidad ni existencia de relaciones musicales.",
    ),
)

# Columna de origen, propiedad y etiqueta: la transformación reutilizará este mapa.
ACOUSTICBRAINZ = (
    ("average_loudness", "sonoridadMedia", "sonoridad media"),
    ("dynamic_complexity", "complejidadDinamica", "complejidad dinámica"),
    ("mfcc_zero_mean", "mediaMfccCero", "media del coeficiente MFCC cero"),
    ("bpm", "tempoBPM", "tempo en BPM"),
    (
        "bpm_histogram_first_peak_bpm_mean",
        "mediaPrimerPicoBPM",
        "media del primer pico en BPM",
    ),
    (
        "bpm_histogram_first_peak_bpm_median",
        "medianaPrimerPicoBPM",
        "mediana del primer pico en BPM",
    ),
    (
        "bpm_histogram_second_peak_bpm_mean",
        "mediaSegundoPicoBPM",
        "media del segundo pico en BPM",
    ),
    (
        "bpm_histogram_second_peak_bpm_median",
        "medianaSegundoPicoBPM",
        "mediana del segundo pico en BPM",
    ),
    ("danceability", "bailabilidad", "bailabilidad"),
    ("onset_rate", "tasaAtaques", "tasa de ataques"),
    ("tuning_frequency", "frecuenciaAfinacion", "frecuencia de afinación"),
    (
        "tuning_equal_tempered_deviation",
        "desviacionTemperamentoIgual",
        "desviación del temperamento igual",
    ),
)
JMIR = (
    ("Spectral_Centroid", "CentroideEspectral", "centroide espectral"),
    ("Spectral_Rolloff_Point", "RolloffEspectral", "punto de rolloff espectral"),
    ("Spectral_Flux", "FlujoEspectral", "flujo espectral"),
    ("Compactness", "Compacidad", "compacidad"),
    ("Spectral_Variability", "VariabilidadEspectral", "variabilidad espectral"),
    ("Root_Mean_Square", "Rms", "raíz de la media cuadrática"),
    (
        "Fraction_Of_Low_Energy_Windows",
        "FraccionVentanasBajaEnergia",
        "fracción de ventanas de baja energía",
    ),
    ("Zero_Crossings", "CrucesPorCero", "cruces por cero"),
)
DESCRIPTORES = tuple(
    dato(
        nombre,
        etiqueta,
        ("AnalisisAcustico",),
        "decimal",
        f"Valor de AcousticBrainz: {columna}; se conserva por análisis.",
    )
    for columna, nombre, etiqueta in ACOUSTICBRAINZ
) + tuple(
    dato(
        f"{prefijo}{nombre}",
        f"{texto} de {etiqueta}",
        ("AnalisisAcustico",),
        "decimal",
        f"Estadístico jMIR del fragmento: {columna}_{sufijo}_1.",
    )
    for columna, nombre, etiqueta in JMIR
    for prefijo, texto, sufijo in (
        ("media", "media", "Overall_Average"),
        ("desviacion", "desviación estándar", "Overall_Standard_Deviation"),
    )
)
EVIDENCIA = (
    Propiedad(
        "artistaSuministrado",
        "artista suministrado",
        ("Grabacion",),
        "Artista",
        "Artista reportado en la entrada; no certifica el crédito completo ni su orden.",
    ),
    dato(
        "lanzamientoSuministrado",
        "lanzamiento suministrado",
        ("Grabacion",),
        "string",
        "Texto original del lanzamiento; no establece identidad de una edición.",
    ),
    dato(
        "duracionSuministradaSegundos",
        "duración suministrada en segundos",
        ("Grabacion",),
        "decimal",
        "Duración reportada por la entrada original, expresada en segundos.",
    ),
    dato(
        "isrc",
        "ISRC",
        ("Grabacion",),
        "string",
        "Identificador ISRC reportado; no es una clave OWL.",
    ),
    dato(
        "archivoCaptura",
        "archivo de captura",
        ("CapturaFuente",),
        "string",
        "Ruta relativa de la tabla consolidada en output/csv.",
    ),
    dato(
        "sha256Captura",
        "SHA-256 de captura",
        ("CapturaFuente",),
        "string",
        "Huella del CSV que permite recuperar la evidencia exacta y sus metadatos de origen.",
    ),
)
PROPIEDADES = OBJETO + DATOS + DESCRIPTORES + EVIDENCIA
