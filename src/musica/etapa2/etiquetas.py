"""Comprobación de etiquetas fuera de la semántica de mundo abierto."""

import re
from collections import Counter

import langcodes
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ESTANDARES = tuple(map(str, (RDF, RDFS, OWL, XSD)))
REFERENCIAS = {RDFS.seeAlso, RDFS.isDefinedBy, OWL.versionIRI}


def recursos_etiquetables(grafo):
    estructurales = set(grafo.subjects(RDF.type, OWL.Restriction))
    for predicado in (OWL.unionOf, OWL.intersectionOf, OWL.oneOf, RDF.first, RDF.rest):
        estructurales.update(grafo.subjects(predicado, None))
    recursos = set()
    for sujeto, predicado, objeto in grafo:
        recursos.update((sujeto, predicado))
        if predicado not in REFERENCIAS:
            recursos.add(objeto)
    return {
        r
        for r in recursos
        if isinstance(r, (URIRef, BNode))
        and not str(r).startswith(ESTANDARES)
        and not (isinstance(r, BNode) and r in estructurales)
    }


def idioma_valido(idioma):
    return bool(
        idioma
        and re.fullmatch(r"[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*", idioma)
        and langcodes.tag_is_valid(idioma)
    )


def validar_etiquetas(grafo):
    """Falla si falta una etiqueta o si alguna etiqueta presente es inválida."""
    recursos = recursos_etiquetables(grafo)
    errores = []
    idiomas = Counter()
    for recurso in sorted(recursos, key=str):
        etiquetas = list(grafo.objects(recurso, RDFS.label))
        if not etiquetas:
            errores.append(f"{recurso}: falta rdfs:label")
        for etiqueta in etiquetas:
            if not isinstance(etiqueta, Literal) or not str(etiqueta).strip():
                errores.append(f"{recurso}: label debe ser un literal no vacío")
            elif not idioma_valido(etiqueta.language):
                errores.append(f"{recurso}: label sin idioma BCP 47 válido")
            else:
                idiomas[etiqueta.language.lower()] += 1
    if errores:
        raise ValueError("\n".join(errores))
    return {
        "recursos": len(recursos),
        "cobertura": 1.0,
        "etiquetas_por_idioma": dict(sorted(idiomas.items())),
    }
