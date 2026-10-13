"""Contrato semántico mínimo y controles de calidad de la segunda entrega."""

import sys
import unittest
from pathlib import Path

from pyoxigraph import RdfFormat, Store
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from musica.etapa2.etiquetas import idioma_valido, validar_etiquetas
from musica.etapa2.ontologia import construir_ontologia, serializar
from musica.etapa2.vocabulario import MUS, PROPIEDADES


class OntologiaTest(unittest.TestCase):
    def setUp(self):
        self.grafo = construir_ontologia()

    def test_turtle_legible_por_dos_motores(self):
        turtle = serializar(self.grafo)
        self.assertTrue(
            isomorphic(self.grafo, Graph().parse(data=turtle, format="turtle"))
        )
        store = Store()
        store.load(input=turtle, format=RdfFormat.TURTLE)
        self.assertEqual(len(self.grafo), len(store))
        self.assertEqual(turtle, serializar(construir_ontologia()))

    def test_propiedades_con_dominio_y_rango(self):
        for propiedad in PROPIEDADES:
            self.assertEqual(
                len(list(self.grafo.objects(MUS[propiedad.nombre], RDFS.domain))), 1
            )
            self.assertEqual(
                len(list(self.grafo.objects(MUS[propiedad.nombre], RDFS.range))), 1
            )

    def test_credito_admite_grabacion_y_grupo_sin_interseccion(self):
        dominio = self.grafo.value(MUS.tieneCredito, RDFS.domain)
        lista = self.grafo.value(dominio, OWL.unionOf)
        self.assertEqual(
            set(self.grafo.items(lista)), {MUS.Grabacion, MUS.GrupoLanzamientos}
        )
        self.assertEqual(self.grafo.value(MUS.acreditaEntidad, RDFS.range), dominio)
        self.assertIn(
            (MUS.tieneCredito, OWL.inverseOf, MUS.acreditaEntidad), self.grafo
        )

    def test_diez_axiomas_de_tres_tipos(self):
        self.assertEqual(
            len(list(self.grafo.triples((None, OWL.disjointWith, None)))), 3
        )
        self.assertEqual(len(list(self.grafo.triples((None, OWL.inverseOf, None)))), 4)
        restricciones = list(self.grafo.subjects(RDF.type, OWL.Restriction))
        self.assertEqual(len(restricciones), 3)
        for restriccion in restricciones:
            self.assertEqual(
                int(self.grafo.value(restriccion, OWL.qualifiedCardinality)), 1
            )
            self.assertIsNotNone(self.grafo.value(restriccion, OWL.onClass))

    def test_no_reintroduce_entidades_eliminadas_ni_identidad_automatica(self):
        for nombre in ("RegistroDataset", "RegistroCancion", "AfirmacionExterna"):
            self.assertNotIn((MUS[nombre], RDF.type, OWL.Class), self.grafo)
        for propiedad in (OWL.sameAs, OWL.differentFrom, OWL.hasKey):
            self.assertFalse(list(self.grafo.triples((None, propiedad, None))))

    def test_etiquetas_esquema_completas(self):
        resultado = validar_etiquetas(self.grafo)
        self.assertEqual(resultado["cobertura"], 1.0)
        self.assertEqual(set(resultado["etiquetas_por_idioma"]), {"es"})

    def test_detecta_objeto_externo_y_nodo_anonimo_sin_label(self):
        for recurso in (URIRef("https://otro.example/artista/1"), BNode("artista")):
            with self.subTest(recurso=recurso):
                grafo = construir_ontologia()
                grafo.add((MUS.credito1, RDFS.label, Literal("Crédito 1", lang="es")))
                grafo.add((MUS.credito1, MUS.artistaAcreditado, recurso))
                with self.assertRaisesRegex(ValueError, "falta rdfs:label"):
                    validar_etiquetas(grafo)
                grafo.add((recurso, RDFS.label, Literal("Nombre original", lang="und")))
                self.assertEqual(
                    validar_etiquetas(grafo)["etiquetas_por_idioma"]["und"], 1
                )

    def test_no_admite_label_invalido_aunque_haya_otro_valido(self):
        for etiqueta in (
            Literal(" ", lang="es"),
            Literal("sin idioma"),
            Literal("inválido", lang="zz"),
        ):
            with self.subTest(etiqueta=etiqueta):
                grafo = construir_ontologia()
                grafo.add((MUS.Grabacion, RDFS.label, etiqueta))
                with self.assertRaises(ValueError):
                    validar_etiquetas(grafo)

    def test_bcp47_y_referencias_documentales(self):
        for idioma in ("es", "es-CO", "und", "zh-Hant"):
            self.assertTrue(idioma_valido(idioma))
        for idioma in (None, "", "en_US", "zz"):
            self.assertFalse(idioma_valido(idioma))
        self.grafo.add(
            (MUS.Grabacion, RDFS.seeAlso, URIRef("https://example.net/documento"))
        )
        validar_etiquetas(self.grafo)


if __name__ == "__main__":
    unittest.main()
