"""Validaciones sobre RDF exportado mediante un almacén temporal en disco.

Comprueba integridad de la exportación; no realiza razonamiento OWL completo.
"""

import tempfile

from pyoxigraph import RdfFormat, Store

from musica.etapa2.etiquetas import idioma_valido

PREFIJOS = """
PREFIX mus: <https://example.org/musica/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
"""

CONTROLES = {
    "recursos_sin_etiqueta": """
        SELECT DISTINCT ?r WHERE {
          { ?r ?p ?o } UNION { ?s ?r ?o } UNION {
            ?s ?p ?r . FILTER(isIRI(?r) || isBlank(?r))
            FILTER(?p NOT IN (rdfs:seeAlso, rdfs:isDefinedBy, owl:versionIRI))
          }
          FILTER(isBlank(?r) || (!STRSTARTS(STR(?r), STR(rdf:)) && !STRSTARTS(STR(?r), STR(rdfs:)) &&
                 !STRSTARTS(STR(?r), STR(owl:)) &&
                 !STRSTARTS(STR(?r), 'http://www.w3.org/2001/XMLSchema#')))
          FILTER NOT EXISTS { ?r rdfs:label ?label }
          FILTER NOT EXISTS { ?r a owl:Restriction }
          FILTER NOT EXISTS { ?r owl:unionOf ?lista }
          FILTER NOT EXISTS { ?r rdf:first ?primero }
        } LIMIT 10
    """,
    "etiquetas_vacias_o_sin_idioma": """
        SELECT ?r ?label WHERE { ?r rdfs:label ?label .
          FILTER(!isLiteral(?label) || LANG(?label) = '' || !REGEX(STR(?label), '\\\\S'))
        } LIMIT 10
    """,
    "propiedades_no_declaradas": """
        SELECT DISTINCT ?p WHERE { ?s ?p ?o .
          FILTER(STRSTARTS(STR(?p), STR(mus:)))
          FILTER NOT EXISTS { ?p a owl:ObjectProperty }
          FILTER NOT EXISTS { ?p a owl:DatatypeProperty }
        } LIMIT 10
    """,
    "creditos_incompletos_o_ambiguos": """
        SELECT ?c WHERE { ?c a mus:CreditoArtistico .
          OPTIONAL { ?c mus:artistaAcreditado ?a }
          OPTIONAL { ?c mus:acreditaEntidad ?s }
          OPTIONAL { ?c mus:posicionCredito ?p }
        } GROUP BY ?c
        HAVING(COUNT(DISTINCT ?a) != 1 || COUNT(DISTINCT ?s) != 1 || COUNT(DISTINCT ?p) != 1)
        LIMIT 10
    """,
    "asignaciones_sin_genero_unico": """
        SELECT ?c WHERE { ?c a mus:AsignacionGenero . OPTIONAL { ?c mus:generoAsignado ?g } }
        GROUP BY ?c HAVING(COUNT(DISTINCT ?g) != 1) LIMIT 10
    """,
    "tipos_disjuntos_explicitos": """
        SELECT ?s ?a ?b WHERE { ?a owl:disjointWith ?b . ?s a ?a, ?b } LIMIT 10
    """,
    "publicaciones_sin_relacion_directa": """
        SELECT ?r ?s WHERE { ?r mus:tienePublicacion/mus:selloPublicacion ?s .
          FILTER NOT EXISTS { ?r mus:publicadoPor ?s }
        } LIMIT 10
    """,
}


def validar_archivos(ontologia, instancias, progreso=print):
    with tempfile.TemporaryDirectory(prefix="musica-rdf-") as carpeta:
        store = Store(carpeta)
        for ruta in (ontologia, instancias):
            progreso(f"Lectura RDF: {ruta}", flush=True)
            store.bulk_load(path=str(ruta), format=RdfFormat.TURTLE)
        resultado = {
            "triples_distintos_esquema_e_instancias": len(store),
            "controles": {},
        }
        for nombre, consulta in CONTROLES.items():
            progreso(f"Validación: {nombre}", flush=True)
            errores = list(store.query(PREFIJOS + consulta))
            if errores:
                raise ValueError(f"{nombre}: {errores}")
            resultado["controles"][nombre] = "correcto"
        idiomas = {}
        for fila in store.query(
            PREFIJOS
            + "SELECT ?idioma (COUNT(*) AS ?n) WHERE { ?s rdfs:label ?label . BIND(LANG(?label) AS ?idioma) } GROUP BY ?idioma"
        ):
            idioma = fila["idioma"].value
            if not idioma_valido(idioma):
                raise ValueError(f"Idioma inválido: {idioma}")
            idiomas[idioma] = int(fila["n"].value)
        resultado["etiquetas_por_idioma"] = idiomas
        del store
        return resultado
