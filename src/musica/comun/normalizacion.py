"""Normalización conservadora para comparar textos sin borrar versiones o acentos."""

import unicodedata


def normalizar(s):
    return " ".join(unicodedata.normalize("NFKC", s).casefold().split())
