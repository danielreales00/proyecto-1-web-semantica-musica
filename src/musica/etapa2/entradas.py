"""Lectura de CSV con inventario verificable y capturas de procedencia."""

import csv
from collections import Counter

from musica.etapa2.escritura import sha_archivo
from musica.etapa2.vocabulario import MUS


class Entradas:
    def __init__(self, carpeta, escritor):
        self.carpeta = carpeta
        self.e = escritor
        self.inventario = {}
        self.capturas = {}
        self.omitidas = Counter()
        self.leidas = Counter()
        for ruta in sorted(carpeta.glob("*.csv")):
            sha = sha_archivo(ruta)
            captura = self.e.entidad(
                "CapturaFuente", sha, f"Tabla consolidada {ruta.name}", "es", True
            )
            self.e.dato(captura, "archivoCaptura", ruta.name)
            self.e.dato(captura, "sha256Captura", sha)
            self.capturas[ruta.stem] = captura
            self.inventario[ruta.name] = {
                "sha256": sha,
                "proyeccion": "evidencia conservada en CSV",
            }

    def filas(self, nombre):
        ruta = self.carpeta / (nombre + ".csv")
        if not ruta.is_file():
            raise FileNotFoundError(ruta)
        self.inventario[ruta.name]["proyeccion"] = (
            "leída por el generador; alcance documentado"
        )
        with ruta.open(encoding="utf-8-sig", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                self.leidas[nombre] += 1
                yield fila

    def fuente(self, nombre):
        return self.e.entidad("Fuente", nombre, nombre, "und")

    def respaldar(self, recurso, tabla, fila):
        self.e.triple(recurso, MUS.respaldadoPor, self.capturas[tabla])
        fuente = fila.get("fuente_id") or fila.get("fuente_base")
        if fuente:
            self.e.triple(recurso, MUS.fuente, self.fuente(fuente))

    def resumen(self):
        return {
            "entradas": self.inventario,
            "filas_leidas": dict(self.leidas),
            "filas_sin_proyeccion_musical": dict(self.omitidas),
        }
