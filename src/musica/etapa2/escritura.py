"""Escritura incremental de Turtle y registro de identidades y etiquetas."""

import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from musica.etapa2.etiquetas import idioma_valido
from musica.etapa2.vocabulario import CLASES, MUS

ETIQUETAS = {c.nombre: c.etiqueta for c in CLASES}


def uri(tipo, *clave):
    if not clave or any(not str(v).strip() for v in clave):
        raise ValueError(f"Clave vacía para {tipo}")
    return URIRef(
        str(MUS) + tipo + "/" + "/".join(quote(str(v), safe="") for v in clave)
    )


def huella(valor):
    return hashlib.sha256(
        json.dumps(valor, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def sha_archivo(ruta):
    with ruta.open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


class Escritor:
    """Mantiene solo el registro de entidades en memoria, no millones de triples."""

    def __init__(self, archivo):
        self.archivo = archivo
        self.tipos = set()
        self.pendientes = {}
        self.etiquetas = set()
        self.idiomas = Counter()
        self.clases = Counter()
        self.generadas = 0
        self.triples = 0

    def triple(self, sujeto, predicado, objeto):
        self.archivo.write(f"{sujeto.n3()} {predicado.n3()} {objeto.n3()} .\n")
        self.triples += 1

    def entidad(self, tipo, clave, nombre="", idioma="und", generada=False):
        recurso = uri(tipo, *clave) if isinstance(clave, tuple) else uri(tipo, clave)
        self.tipar(recurso, tipo)
        if recurso not in self.pendientes:
            self.pendientes[recurso] = False
        if nombre.strip():
            self.label(recurso, nombre, idioma, generada)
        return recurso

    def tipar(self, recurso, tipo):
        par = (recurso, tipo)
        if par not in self.tipos:
            self.tipos.add(par)
            self.clases[tipo] += 1
            self.triple(recurso, RDF.type, MUS[tipo])

    def label(self, recurso, nombre, idioma, generada=False):
        if not idioma_valido(idioma):
            raise ValueError(f"Idioma inválido para {recurso}: {idioma}")
        par = (recurso, nombre, idioma)
        if par not in self.etiquetas:
            self.etiquetas.add(par)
            self.triple(recurso, RDFS.label, Literal(nombre, lang=idioma))
            self.idiomas[idioma] += 1
            self.generadas += int(generada)
        self.pendientes[recurso] = True

    def dato(self, recurso, propiedad, valor, tipo=None):
        if valor is None or str(valor) == "":
            return
        if tipo == XSD.decimal:
            try:
                numero = Decimal(str(valor))
            except InvalidOperation as error:
                raise ValueError(f"Decimal inválido: {valor}") from error
            if not numero.is_finite():
                raise ValueError(f"Decimal no finito: {valor}")
            valor = format(numero, "f")
        if tipo in (XSD.integer, XSD.positiveInteger, XSD.nonNegativeInteger):
            valor = int(valor)
            if tipo == XSD.positiveInteger and valor < 1:
                raise ValueError("Posición del crédito debe ser positiva")
            if tipo == XSD.nonNegativeInteger and valor < 0:
                raise ValueError("Índice no puede ser negativo")
        self.triple(
            recurso, MUS[propiedad], Literal(valor, datatype=tipo or XSD.string)
        )

    def cerrar_etiquetas(self):
        for recurso, etiquetado in self.pendientes.items():
            if not etiquetado:
                tipo = str(recurso)[len(str(MUS)) :].split("/")[0]
                nombre = f"{ETIQUETAS[tipo]} {str(recurso).rsplit('/', 1)[-1]}"
                self.label(recurso, nombre, "es", generada=True)
        return {
            "recursos": len(self.pendientes),
            "etiquetas_por_idioma": dict(self.idiomas),
            "etiquetas_generadas": self.generadas,
            "por_clase": dict(self.clases),
            "triples_escritos": self.triples,
        }
