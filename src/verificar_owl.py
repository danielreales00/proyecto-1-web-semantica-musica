"""Comprueba el esquema y casos controlados con HermiT (no toda la ABox)."""

import argparse
import json
import shlex
import tempfile
from pathlib import Path

import owlready2
from rdflib import URIRef
from rdflib.namespace import OWL, RDF

from musica.comun.rutas import ROOT
from musica.etapa2.ontologia import construir_ontologia
from musica.etapa2.vocabulario import MUS


def configurar_java(carpeta):
    paquete = Path(owlready2.__file__).parent
    argumentos = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-w",
        "/tmp",
        "-v",
        f"{paquete}:{paquete}:ro",
        "-v",
        f"{carpeta}:{carpeta}:ro",
        "eclipse-temurin:21-jre-jammy",
        "java",
    ]
    wrapper = carpeta / "java-docker.sh"
    wrapper.write_text("#!/bin/sh\nexec " + shlex.join(argumentos) + ' "$@"\n')
    wrapper.chmod(0o755)
    owlready2.JAVA_EXE = str(wrapper)


def razonar(grafo, carpeta):
    archivo = carpeta / "caso.rdf"
    grafo.serialize(archivo, format="xml")
    mundo = owlready2.World()
    mundo.get_ontology(archivo.as_uri()).load()
    try:
        owlready2.sync_reasoner(mundo, infer_property_values=True, debug=0)
        inconsistentes = [
            c.iri for c in mundo.inconsistent_classes() if c != owlready2.Nothing
        ]
        if inconsistentes:
            raise AssertionError(f"Clases insatisfacibles: {inconsistentes}")
        resultado = set(mundo.as_rdflib_graph())
        for individuo in mundo.individuals():
            for clase in individuo.INDIRECT_is_a:
                if hasattr(clase, "iri"):
                    resultado.add((URIRef(individuo.iri), RDF.type, URIRef(clase.iri)))
        return resultado
    finally:
        mundo.close()


def verificar(carpeta):
    base = construir_ontologia()
    razonar(base, carpeta)
    r, p, s, g, o, c, a = [
        URIRef("urn:prueba:" + n)
        for n in (
            "edicion",
            "publicacion",
            "sello",
            "grabacion",
            "obra",
            "credito",
            "artista",
        )
    ]
    grupo = URIRef("urn:prueba:grupo")
    hechos = [
        (r, MUS.tienePublicacion, p),
        (p, MUS.selloPublicacion, s),
        (g, MUS.apareceEn, r),
        (g, MUS.interpretaObra, o),
        (r, MUS.perteneceAGrupo, grupo),
        (g, MUS.tieneCredito, c),
        (c, MUS.artistaAcreditado, a),
        (a, RDF.type, MUS.Persona),
    ]
    hechos.extend(
        (i, RDF.type, OWL.NamedIndividual) for i in (r, p, s, g, o, c, a, grupo)
    )
    for triple in hechos:
        base.add(triple)
    inferido = razonar(base, carpeta)
    esperados = [
        (r, MUS.publicadoPor, s),
        (r, MUS.contieneGrabacion, g),
        (o, MUS.tieneGrabacion, g),
        (grupo, MUS.tieneLanzamiento, r),
        (c, MUS.acreditaEntidad, g),
        (a, RDF.type, MUS.Artista),
    ]
    for triple in esperados:
        if triple not in inferido:
            raise AssertionError(f"Inferencia ausente: {triple}")
    negativos = {
        "disjuncion": [(a, RDF.type, MUS.Agrupacion)],
        "cardinalidad_con_individuos_distintos": [
            (c, MUS.artistaAcreditado, URIRef("urn:prueba:otro")),
            (a, OWL.differentFrom, URIRef("urn:prueba:otro")),
        ],
    }
    for nombre, adicionales in negativos.items():
        caso = construir_ontologia()
        for triple in hechos + adicionales:
            caso.add(triple)
        try:
            razonar(caso, carpeta)
        except owlready2.OwlReadyInconsistentOntologyError:
            continue
        raise AssertionError(f"No detectó inconsistencia: {nombre}")
    return {
        "razonador": "HermiT incluido en Owlready2 0.49",
        "alcance": "esquema completo y casos controlados; no la totalidad de instances.ttl",
        "esquema_consistente": True,
        "clases_insatisfacibles": [],
        "inferencias_verificadas": [[str(t) for t in triple] for triple in esperados],
        "inconsistencias_detectadas": list(negativos),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker-java", action="store_true")
    args = parser.parse_args()
    salida = ROOT / "output/etapa2"
    salida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=salida, prefix="owl-") as nombre:
        carpeta = Path(nombre).resolve()
        previo = tempfile.tempdir
        tempfile.tempdir = str(carpeta)
        try:
            if args.docker_java:
                configurar_java(carpeta)
            resultado = verificar(carpeta)
        finally:
            tempfile.tempdir = previo
    (salida / "razonamiento.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
