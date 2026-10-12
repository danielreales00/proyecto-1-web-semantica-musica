# Proyecto de Web Semántica Etapa 2

La segunda entrega formaliza el dominio musical con RDF, RDFS y OWL, genera instancias desde los datos consolidados de la primera etapa y responde preguntas de competencia mediante SPARQL en Apache Jena Fuseki.

El diseño distingue composiciones, grabaciones, ediciones y grupos de lanzamientos. Las grabaciones mantienen identificadores locales estables, incluso cuando su correspondencia externa no está resuelta. Toda clase, propiedad e instancia exportada requiere un label legible con etiqueta de idioma.

## Documentación

- [Modelo musical](docs/etapa2/modelo.md): entidades, relaciones, identidad y conocimiento incompleto.
- [Mapeo de datos](docs/etapa2/mapeo_datos.md): significado de las transformaciones desde los CSV consolidados.
- [Preguntas de competencia](docs/etapa2/preguntas_competencia.md): ocho preguntas y criterios de interpretación.
- [Decisiones de modelado](docs/etapa2/decisiones_modelado.md): eliminación de afirmaciones genéricas, distinción de ediciones y grupos, y cobertura de labels.
- [Etapa 1](README.md): datos de origen y comandos de reproducción disponibles.

Estos documentos complementan el informe académico en LaTeX. La documentación de uso y las definiciones del modelo permanecen en Markdown para su consulta en GitHub.

## Código disponible

El procesamiento de la etapa 1 y sus pruebas permanecen operativos. Las utilidades compartidas están en src/musica/comun: rutas del proyecto, escritura CSV y normalización conservadora. Los comandos existentes de la etapa 1 conservan su forma de ejecución.

La generación de ontology.ttl e instances.ttl, la validación de labels e idiomas y la ejecución en Fuseki todavía están pendientes de implementación. Este README no presenta comandos para funciones que aún no están disponibles.

## Archivos de la segunda entrega

La entrega incluirá ontology.ttl con clases, propiedades y axiomas; instances.ttl con instancias generadas; configuracion.py con parámetros de Fuseki; consultas SPARQL y sus resultados; evidencia de carga y ejecución; y un informe de máximo seis páginas. Se requieren al menos ocho axiomas OWL de tres tipos de construcción y al menos cinco preguntas implementadas de las ocho definidas.
