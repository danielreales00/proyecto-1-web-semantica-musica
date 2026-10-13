"""Construcción reproducible del esquema OWL y su catálogo legible."""

from rdflib import BNode, Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, XSD

from musica.etapa2.vocabulario import ACREDITABLE, CLASES, MUS, PROPIEDADES

AXIOMAS = (
    (
        "A01",
        "disjunción",
        "Persona",
        "Agrupacion",
        "Un artista individual no es un colectivo.",
    ),
    (
        "A02",
        "disjunción",
        "Grabacion",
        "ObraMusical",
        "La realización sonora se distingue de la composición abstracta.",
    ),
    (
        "A03",
        "disjunción",
        "Lanzamiento",
        "GrupoLanzamientos",
        "Una edición no es la identidad que agrupa sus ediciones.",
    ),
    (
        "A04",
        "inversa",
        "apareceEn",
        "contieneGrabacion",
        "Ambas direcciones describen la misma inclusión de una grabación en una edición.",
    ),
    (
        "A05",
        "inversa",
        "interpretaObra",
        "tieneGrabacion",
        "Ambas direcciones vinculan la obra con su realización sonora.",
    ),
    (
        "A06",
        "inversa",
        "perteneceAGrupo",
        "tieneLanzamiento",
        "Ambas direcciones expresan la pertenencia de una edición al grupo.",
    ),
    (
        "A07",
        "inversa",
        "tieneCredito",
        "acreditaEntidad",
        "Permite recorrer el crédito desde su grabación o grupo y viceversa.",
    ),
    (
        "A08",
        "cardinalidad",
        "CreditoArtistico",
        "artistaAcreditado",
        "Cada crédito individual identifica exactamente un artista de clase Artista.",
    ),
    (
        "A09",
        "cardinalidad",
        "CreditoArtistico",
        "acreditaEntidad",
        "Cada crédito pertenece exactamente a una entidad de la unión Grabacion o GrupoLanzamientos.",
    ),
    (
        "A10",
        "cardinalidad",
        "AsignacionGenero",
        "generoAsignado",
        "Cada asignación individual identifica exactamente un GeneroMusical.",
    ),
)


def union(grafo, nombres):
    """Lista OWL con identificadores estables y orden explícito."""
    if len(nombres) == 1:
        return OWL.Thing if nombres[0] == "owl:Thing" else MUS[nombres[0]]
    clave = "union_" + "_".join(nombres)
    expresion = BNode(clave)
    grafo.add((expresion, RDF.type, OWL.Class))
    grafo.add((expresion, OWL.unionOf, BNode(clave + "_0")))
    for indice, nombre in enumerate(nombres):
        celda = BNode(f"{clave}_{indice}")
        siguiente = BNode(f"{clave}_{indice + 1}")
        grafo.add((celda, RDF.first, MUS[nombre]))
        grafo.add(
            (celda, RDF.rest, RDF.nil if indice == len(nombres) - 1 else siguiente)
        )
    return expresion


def rango(grafo, propiedad):
    if propiedad.dato:
        return XSD[propiedad.rango]
    if propiedad.rango == "@acreditable":
        return union(grafo, ACREDITABLE)
    return MUS[propiedad.rango]


def anotar(grafo, recurso, etiqueta, descripcion):
    grafo.add((recurso, RDFS.label, Literal(etiqueta, lang="es")))
    grafo.add((recurso, RDFS.comment, Literal(descripcion, lang="es")))


def agregar_axiomas(grafo):
    for identificador, tipo, sujeto, objeto, _ in AXIOMAS:
        if tipo == "disjunción":
            grafo.add((MUS[sujeto], OWL.disjointWith, MUS[objeto]))
        elif tipo == "inversa":
            grafo.add((MUS[sujeto], OWL.inverseOf, MUS[objeto]))
        else:
            restriccion = BNode(identificador)
            clases = {
                "artistaAcreditado": ("Artista",),
                "acreditaEntidad": ACREDITABLE,
                "generoAsignado": ("GeneroMusical",),
            }
            grafo.add((MUS[sujeto], RDFS.subClassOf, restriccion))
            grafo.add((restriccion, RDF.type, OWL.Restriction))
            grafo.add((restriccion, OWL.onProperty, MUS[objeto]))
            grafo.add((restriccion, OWL.onClass, union(grafo, clases[objeto])))
            grafo.add(
                (
                    restriccion,
                    OWL.qualifiedCardinality,
                    Literal(1, datatype=XSD.nonNegativeInteger),
                )
            )


def construir_ontologia():
    grafo = Graph()
    for prefijo, espacio in (
        ("mus", MUS),
        ("owl", OWL),
        ("rdfs", RDFS),
        ("rdf", RDF),
        ("xsd", XSD),
    ):
        grafo.bind(prefijo, espacio)
    grafo.add((MUS.OntologiaMusical, RDF.type, OWL.Ontology))
    anotar(
        grafo,
        MUS.OntologiaMusical,
        "Ontología musical",
        "Modelo musical y evidencia de la segunda entrega. Dominio abierto; las etiquetas se validan con código.",
    )
    for clase in CLASES:
        grafo.add((MUS[clase.nombre], RDF.type, OWL.Class))
        anotar(grafo, MUS[clase.nombre], clase.etiqueta, clase.descripcion)
        if clase.padre:
            grafo.add((MUS[clase.nombre], RDFS.subClassOf, MUS[clase.padre]))
    for propiedad in PROPIEDADES:
        recurso = MUS[propiedad.nombre]
        grafo.add(
            (
                recurso,
                RDF.type,
                OWL.DatatypeProperty if propiedad.dato else OWL.ObjectProperty,
            )
        )
        grafo.add((recurso, RDFS.domain, union(grafo, propiedad.dominio)))
        grafo.add((recurso, RDFS.range, rango(grafo, propiedad)))
        anotar(grafo, recurso, propiedad.etiqueta, propiedad.descripcion)
    agregar_axiomas(grafo)
    return grafo


def serializar(grafo):
    """Turtle ordenado por triples, sin depender del orden de un hash Python.

    Se conservan prefijos y nombres estables de nodos estructurales para que
    dos ejecuciones produzcan el mismo archivo y un diff legible en Git.
    """
    prefijos = (("mus", MUS), ("owl", OWL), ("rdf", RDF), ("rdfs", RDFS), ("xsd", XSD))
    cabecera = "\n".join(f"@prefix {p}: <{n}> ." for p, n in prefijos)
    triples = sorted(
        " ".join(termino.n3(grafo.namespace_manager) for termino in triple) + " ."
        for triple in grafo
    )
    return cabecera + "\n\n" + "\n".join(triples) + "\n"


def catalogo_markdown():
    lineas = [
        "# Catálogo de la ontología",
        "",
        "Generado desde `src/musica/etapa2/vocabulario.py` y `ontologia.py` mediante `python src/generar_ontologia.py`.",
        "",
        "Namespace: `https://example.org/musica/`. Las etiquetas del vocabulario están en español (`@es`).",
        "",
        "## Clases",
        "",
        "| Clase | Superclase | Significado |",
        "| --- | --- | --- |",
    ]
    lineas.extend(
        f"| {c.nombre} | {c.padre or '—'} | {c.descripcion} |" for c in CLASES
    )
    lineas.extend(
        [
            "",
            "## Propiedades",
            "",
            "Un dominio con «o» es una unión OWL. Dominio y rango permiten inferir tipos; no son controles de completitud.",
            "",
            "| Propiedad | Tipo | Dominio | Rango | Significado |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for p in PROPIEDADES:
        destino = (
            "Grabacion o GrupoLanzamientos" if p.rango == "@acreditable" else p.rango
        )
        lineas.append(
            f"| {p.nombre} | {'Dato' if p.dato else 'Objeto'} | {' o '.join(p.dominio)} | {destino} | {p.descripcion} |"
        )
    lineas.extend(
        [
            "",
            "## Axiomas OWL",
            "",
            "Diez axiomas de tres tipos de construcción, además de las jerarquías y las uniones usadas en dominios y rangos.",
            "",
            "| ID | Construcción | Términos | Justificación |",
            "| --- | --- | --- | --- |",
        ]
    )
    lineas.extend(f"| {i} | {t} | {s}, {o} | {j} |" for i, t, s, o, j in AXIOMAS)
    lineas.extend(
        [
            "",
            "## Interpretación y validación",
            "",
            "Las cardinalidades son calificadas y exactas (1). Con mundo abierto, un valor ausente no prueba una inconsistencia; dos URI tampoco prueban dos individuos diferentes. No se declaran claves, propiedades inversamente funcionales ni diferencias entre individuos por sus identificadores locales.",
            "",
            "La validación de etiquetas es una comprobación explícita sobre la unión de esquema e instancias: exige texto no vacío e idioma BCP 47 en todas las etiquetas. Acepta `und` cuando el idioma es desconocido. Los nodos estructurales OWL y las celdas de listas RDF quedan exentos; los nodos anónimos de dominio no.",
            "",
            "La generación y las pruebas estructurales no ejecutan un razonador OWL. Las consultas deberán declarar si usan triples explícitos o inferencias materializadas. Contar URI distintas no prueba que representen individuos diferentes en el mundo.",
            "",
        ]
    )
    return "\n".join(lineas)
