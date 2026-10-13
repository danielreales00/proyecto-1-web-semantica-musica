# Proyecto de Web Semántica Etapa 2

La segunda entrega formaliza el dominio musical con RDF, RDFS y OWL, genera instancias desde los datos consolidados de la primera etapa y responde preguntas de competencia mediante SPARQL en Apache Jena Fuseki.

El diseño distingue composiciones, grabaciones, ediciones y grupos de lanzamientos. Las grabaciones mantienen identificadores locales estables, incluso cuando su correspondencia externa no está resuelta. Toda clase, propiedad e instancia exportada requiere un label legible con etiqueta de idioma.

## Documentación

- [Modelo musical](docs/etapa2/modelo.md): entidades, relaciones, identidad y conocimiento incompleto.
- [Mapeo de datos](docs/etapa2/mapeo_datos.md): significado de las transformaciones desde los CSV consolidados.
- [Preguntas de competencia](docs/etapa2/preguntas_competencia.md): las ocho preguntas acordadas.
- [Catálogo de la ontología](docs/etapa2/catalogo_ontologia.md): clases, propiedades, dominios, rangos y once axiomas justificados.
- [Decisiones de modelado](docs/etapa2/decisiones_modelado.md): eliminación de afirmaciones genéricas, distinción de ediciones y grupos, y cobertura de labels.
- [Generación y Fuseki](docs/etapa2/generacion_instancias.md): transformación de CSV, validación, carga y servicio Docker.
- [Etapa 1](README.md): datos de origen y comandos de reproducción disponibles.

Estos documentos complementan el informe académico en LaTeX. La documentación de uso y las definiciones del modelo permanecen en Markdown para su consulta en GitHub.

## Código disponible

El procesamiento de la etapa 1 y sus pruebas permanecen operativos. Las utilidades compartidas están en src/musica/comun: rutas del proyecto, escritura CSV y normalización conservadora. Los comandos existentes de la etapa 1 conservan su forma de ejecución.

El esquema [ontology.ttl](ontology.ttl) se genera desde un catálogo declarativo en `src/musica/etapa2/vocabulario.py`; las construcciones OWL están en `ontologia.py` y la validación de etiquetas en `etiquetas.py`.

Desde la raíz del repositorio, con Python 3.11 o posterior:

```bash
python -m pip install -r requirements.txt
python src/generar_ontologia.py
```

El comando genera `ontology.ttl` y actualiza el catálogo Markdown. Antes de escribir, exige etiquetas no vacías con idioma BCP 47 para todos los recursos del esquema. La salida informa cobertura e idiomas. Acepta `--salida` y `--catalogo` para elegir otras rutas. El Turtle se ordena de forma determinista para facilitar su revisión en Git.

Las pruebas se ejecutan con `python -m unittest discover -s tests`. Comprueban el esquema con RDFLib y PyOxigraph, las uniones de clases, los axiomas y la validación de etiquetas, incluidos objetos externos y nodos anónimos de dominio. No constituyen una prueba de consistencia con un razonador OWL.

La generación de instancias, la validación del RDF exportado y el servicio Docker están implementados:

```bash
python src/generar_instancias.py
python src/validar_instancias.py
docker compose up -d --build
python src/cargar_fuseki.py
```

La salida está en `output/etapa2`. Las consultas de competencia, la revisión con un razonador OWL y el informe académico siguen pendientes. La documentación de generación explica el alcance de los datos proyectados y la configuración de Fuseki.

## Archivos de la segunda entrega

La entrega incluirá ontology.ttl con clases, propiedades y axiomas; instances.ttl con instancias generadas; configuracion.py con parámetros de Fuseki; consultas SPARQL y sus resultados; evidencia de carga y ejecución; y un informe de máximo seis páginas. Se requieren al menos ocho axiomas OWL de tres tipos de construcción y al menos cinco preguntas implementadas de las ocho definidas.
