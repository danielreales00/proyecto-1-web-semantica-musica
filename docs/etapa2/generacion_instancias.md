# Generación de instancias y servicio SPARQL

## Ejecución

Desde la raíz del repositorio, con los 39 CSV de la etapa 1 en `output/csv`:

```bash
python -m pip install -r requirements.txt
python src/generar_ontologia.py
python src/generar_instancias.py
python src/validar_instancias.py

docker compose up -d --build
python src/cargar_fuseki.py
```

La generación escribe `output/etapa2/instances.ttl` y `instances.informe.json`. El validador abre el esquema y las instancias con PyOxigraph en un almacén temporal en disco, y produce `instances.validacion.json`. El archivo RDF es grande y se genera localmente; no se añade al historial Git. Una ejecución fallida del generador conserva el Turtle anterior. Los CSV de entrada no se modifican.

La escritura es incremental. Las URI y el archivo resultante son deterministas para los mismos CSV; el informe conserva las huellas SHA-256 de entrada y salida. El Turtle usa triples explícitos, por lo que también es legible por un procesador N-Triples.

## Identidad y correspondencias

Las 100.000 entradas conservan URI `https://example.org/musica/Grabacion/{track_id}`. No se reemplazan por URI de MusicBrainz. Solo el estado `aceptada` habilita relaciones externas. Se prefiere la correspondencia del volcado; el piloto completa los casos restantes. Un conflicto entre dos MBID aceptados se registra en el informe y no mezcla sus relaciones.

Varias referencias locales pueden compartir un MBID aceptado. No se añade `owl:sameAs` ni `owl:differentFrom`. Las consultas deben distinguir conteos de referencias locales de conteos por MBID. El nombre suministrado del artista se vincula mediante `artistaSuministrado`: no constituye un crédito ordenado y completo.

Las entidades con MBID usan ese identificador dentro de su clase. Créditos, asignaciones, publicaciones y análisis emplean hashes de claves compuestas que incluyen la captura. Los créditos de capturas distintas se mantienen separados; para analizar su orden debe agruparse también por `respaldadoPor`.

## Análisis, géneros y publicaciones

Los 16 estadísticos jMIR permanecen en análisis de fragmentos. AcousticBrainz conserva MBID, captura e índice cuando existe; el piloto no recibe un índice inventado. Un análisis de un mismo MBID se comparte entre sus referencias locales. Ninguna consulta debe combinar el tempo de un análisis con la tonalidad de otro.

Tagtraum clasifica grabaciones, MusicBrainz clasifica grupos y los hechos P136 de correspondencias únicas de Wikidata clasifican artistas. Los vocabularios mantienen identidades separadas, incluso cuando coinciden sus etiquetas. No hay propagación de géneros entre categorías.

Cada número de catálogo pertenece a una `PublicacionDiscografica` que relaciona edición y sello. Hay filas sin sello conocido: se conserva el catálogo y se omite el sello, sin crear una entidad ficticia. `publicadoPor` se exporta explícitamente desde las filas con sello; el axioma de cadena expresa la misma relación.

## Procedencia y alcance

Cada uno de los 39 CSV tiene una `CapturaFuente` con nombre de archivo y SHA-256. Los recursos exportados se vinculan con las tablas que los respaldan y, cuando la fila lo indica, con su proveedor. Para reconstruir la evidencia de una relación concreta se usa la tabla capturada y sus claves originales. No se introducen recursos genéricos de afirmación externa.

Esta versión proyecta al RDF los hechos necesarios para el modelo musical y las ocho preguntas: grabaciones, artistas y tipos, obras, grupos y tipos, ediciones, sellos, créditos, ISRC, composición, producción, interpretación de obras, géneros y análisis.

Permanecen en los CSV, inventariados por su huella: eventos de publicación y fechas parciales, candidatos de reconciliación no aceptados, cobertura de análisis, otras relaciones de MusicBrainz, propiedades de Wikidata distintas de P136 y metadatos adicionales no modelados. El informe cuenta las filas leídas y las relaciones seleccionadas que no se proyectan. Conservar una tabla como evidencia no significa que todos sus campos se hayan convertido en triples.

## Etiquetas y controles

Los nombres originales sin idioma comprobado usan `@und`. Las etiquetas de Wikidata conservan el idioma de su fuente. Las descripciones generadas usan `@es`. Una entidad sin nombre recibe al finalizar una etiqueta con su clase e identificador. El informe cuenta las etiquetas generadas y las etiquetas por idioma.

La validación del RDF comprueba recursos sin etiqueta, etiquetas vacías o sin idioma válido, propiedades no declaradas, estructura de créditos y asignaciones, tipos explícitos disjuntos y correspondencia entre las asociaciones edición–sello y `publicadoPor`. Estos controles de integridad no constituyen una prueba completa de consistencia OWL.

## Fuseki en Docker

El servicio utiliza Apache Jena Fuseki 6.2.0 con Java 21. El binario se verifica mediante SHA-256 en el Dockerfile. El volumen `fuseki-data` conserva TDB2 entre reinicios. El puerto se publica únicamente en `127.0.0.1:3030`.

Endpoints predeterminados:

- Dataset: `http://localhost:3030/musica`
- Consultas: `http://localhost:3030/musica/query`
- Actualizaciones: `http://localhost:3030/musica/update`
- Graph Store: `http://localhost:3030/musica/data`

`src/configuracion.py` centraliza estas direcciones. `FUSEKI_URL` y `FUSEKI_DATASET` permiten apuntar los clientes a otro servicio. Para cambiar el puerto local de Compose, usar `FUSEKI_PORT`; para cambiar el nombre del dataset del contenedor, editar también `docker/fuseki/config.ttl`.

`cargar_fuseki.py` reemplaza únicamente los grafos `urn:musica:ontologia` y `urn:musica:instancias`. La vista de consulta predeterminada une los grafos nombrados, sin activar inferencia OWL. La carga guarda códigos HTTP, hashes y conteos en `output/etapa2/fuseki_carga.json`.

El servidor expone los protocolos HTTP y una interfaz web en `http://localhost:3030/`. Para comprobar el servicio:

```bash
docker compose ps
docker compose logs --tail=30
curl --get --data-urlencode 'query=ASK {}' http://localhost:3030/musica/query
```

`docker compose stop` detiene el servicio; `docker compose start` lo reanuda conservando los datos.

Referencias: [Docker de Apache Jena](https://jena.apache.org/documentation/fuseki2/fuseki-docker.html), [configuración de Fuseki](https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html) y [distribuciones oficiales](https://jena.apache.org/download/).
