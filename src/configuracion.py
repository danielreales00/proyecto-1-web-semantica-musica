"""Endpoints de la segunda entrega; se pueden sustituir mediante el entorno."""

import os

FUSEKI_URL = os.environ.get("FUSEKI_URL", "http://localhost:3030").rstrip("/")
FUSEKI_DATASET = os.environ.get("FUSEKI_DATASET", "musica").strip("/")
DATASET_URL = f"{FUSEKI_URL}/{FUSEKI_DATASET}"
QUERY_URL = f"{DATASET_URL}/query"
UPDATE_URL = f"{DATASET_URL}/update"
DATA_URL = f"{DATASET_URL}/data"

GRAFO_ONTOLOGIA = "urn:musica:ontologia"
GRAFO_INSTANCIAS = "urn:musica:instancias"
