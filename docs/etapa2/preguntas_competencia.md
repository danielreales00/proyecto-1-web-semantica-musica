# Preguntas de competencia de la etapa 2

Estas ocho preguntas tienen valores, fuentes y unidades de conteo definidos. Cada una corresponde a una consulta SPARQL fija, sin parámetros pendientes de elegir. El alcance es la captura consolidada del proyecto, no el catálogo completo de las fuentes.

## CQ1 Grabaciones Rock con BPM superior a 120

¿Cuáles son las primeras 20 grabaciones locales cuyo género mayoritario en tagtraum es exactamente Rock y cuyo análisis AcousticBrainz del volcado, con submission_offset igual a 0, tiene BPM estrictamente superior a 120?

- Entradas: cancion_genero.csv con genero = Rock, papel = mayoritario y fuente_id = tagtraum; grabaciones_correspondencias_masivas.csv con estado = aceptada; acousticbrainz_masivo.csv con submission_offset = 0 y fuente_id = acousticbrainz_dump.
- Ruta: Grabacion → AsignacionGenero → GeneroMusical; Grabacion → AnalisisAcustico → Fuente.
- Salida: track_id, URI y label de grabación, recording_mbid, BPM e identificadores y labels de las dos fuentes. Mostrar el idioma de los labels.
- Unidad: una fila por track_id. DISTINCT elimina duplicaciones debidas a los joins. BPM se compara como número, no como texto; valores vacíos no participan.
- Orden: BPM descendente, seguido de track_id ascendente. LIMIT 20 se aplica después del orden.

## CQ2 Grabaciones con al menos dos artistas acreditados

¿Qué grabaciones MusicBrainz aceptadas tienen al menos dos artistas distintos en los créditos del volcado completo, y cuáles son sus nombres acreditados y posiciones?

- Entradas: correspondencias aceptadas del volcado; creditos_grabaciones_masivos.csv y artistas_masivos.csv.
- Ruta: Grabacion → CreditoArtistico → Artista.
- Condición: COUNT DISTINCT artist_mbid por recording_mbid mayor o igual a 2. No usar el crédito textual original ni los créditos del grupo de lanzamientos.
- Salida: recording_mbid, label de grabación, número de artistas distintos, artist_mbid, label del artista, nombre acreditado, posición y frase de unión. Preservar cada crédito, aunque un artista aparezca varias veces.
- Orden: recording_mbid, posición numérica y artist_mbid ascendentes. Devolver todos los créditos de las grabaciones elegibles.
- Unidad: créditos de grabaciones identificadas. Varias entradas del dataset con el mismo recording_mbid no duplican el conteo ni los créditos.

## CQ3 Obras con varias grabaciones y artistas acreditados

¿Qué obras tienen al menos dos grabaciones MusicBrainz aceptadas y, entre esas grabaciones, al menos dos artistas acreditados distintos, y qué compositores explícitos constan para cada obra?

- Entradas: correspondencias aceptadas, obras_masivas.csv, relaciones_musicales_masivas.csv y creditos_grabaciones_masivos.csv.
- Ruta: Grabacion → interpretaObra → ObraMusical; Artista → compuso → ObraMusical; Grabacion → CreditoArtistico → Artista.
- Condiciones: al menos dos recording_mbid distintos y al menos dos artist_mbid distintos por work_mbid. La relación grabación-obra es performance y la relación artista-obra es composer, con la orientación documentada por la fuente.
- Salida: work_mbid, label de obra, conteos de grabaciones y artistas, y MBID y label de cada compositor conocido. Si no hay compositor explícito, conservar la obra y dejar esos campos sin vincular mediante OPTIONAL.
- Orden: número de grabaciones descendente, work_mbid y compositor ascendente. Sin LIMIT.
- No equiparar créditos a composición ni convertir writer o lyricist en composer. No contar referencias locales duplicadas como grabaciones MusicBrainz diferentes.

## CQ4 Grabaciones en al menos dos ediciones

¿Qué grabaciones MusicBrainz aceptadas aparecen en al menos dos ediciones distintas del volcado completo, y a qué grupo de lanzamientos pertenece cada edición cuando ese vínculo está disponible?

- Entradas: correspondencias aceptadas, grabacion_lanzamiento_masivo.csv y lanzamientos_masivos.csv; grupos_lanzamientos.csv aporta metadatos cuando existen.
- Ruta: Grabacion → apareceEn → Lanzamiento → perteneceAGrupo → GrupoLanzamientos.
- Condición: COUNT DISTINCT release_mbid por recording_mbid mayor o igual a 2. Una edición repetida por distintos medios o pistas cuenta una sola vez.
- Salida: recording_mbid, label, número de ediciones, release_mbid y label de edición, y grupo_lanzamiento_mbid y label de grupo si se conocen. La ausencia de grupo no excluye la edición.
- Orden: número de ediciones descendente, recording_mbid y release_mbid ascendentes. Sin LIMIT.

## CQ5 Sellos de las ediciones de Longing

¿Qué sellos publicaron las ediciones recuperadas en el volcado completo que contienen la grabación Longing, identificada por recording_mbid = 28a930f9-d6b6-451d-9004-c0670b693251, y qué números de catálogo constan para esas asociaciones?

- Entradas: grabacion_lanzamiento_masivo.csv, lanzamientos_masivos.csv, lanzamiento_sello_masivo.csv y sellos_masivos.csv.
- Referencia original: track_id = TRHECIK128F14692BC. El título es informativo; el filtro utiliza el MBID completo.
- Ruta: Grabacion → apareceEn → Lanzamiento → asociación de publicación → SelloDiscografico.
- Salida: release_mbid y label de edición, label_mbid y label del sello, número de catálogo cuando exista.
- Unidad: combinaciones distintas de edición, sello y número de catálogo. Un sello desconocido no se inventa; las asociaciones sin label_mbid quedan fuera de esta pregunta sobre sellos identificados.
- Orden: release_mbid, label_mbid y número de catálogo ascendentes. Sin LIMIT.
- La relación no demuestra contratos entre los sellos y los artistas.

## CQ6 Cobertura de créditos de personas y agrupaciones

¿Cuántas grabaciones locales tienen al menos un crédito del volcado completo vinculado a Persona y cuántas tienen al menos uno vinculado a Agrupacion?

- Entradas: correspondencias aceptadas, creditos_grabaciones_masivos.csv y artistas_masivos.csv.
- Clasificación: Person → Persona; Group, Orchestra y Choir → Agrupacion. Los demás tipos y valores vacíos no se fuerzan a estas clases.
- Ruta: Grabacion → CreditoArtistico → Artista → jerarquía de tipos.
- Salida: las categorías Persona y Agrupacion, con label, idioma y COUNT DISTINCT URI local de grabación. Presentar cero si una categoría no tiene resultados.
- Orden: Persona seguida de Agrupacion. Sin LIMIT.
- Una grabación con ambos tipos cuenta en ambas categorías; los resultados no constituyen una partición exclusiva. Se cuentan recursos locales, no grabaciones probadamente distintas en el mundo.

## CQ7 Cobertura acústica por estado de reconciliación

Para cada estado aceptada, ambigua y sin_coincidencia_conservadora del volcado MusicBrainz, ¿cuántas entradas del dataset tienen análisis jMIR, cuántas tienen análisis AcousticBrainz del volcado con submission_offset = 0, y qué porcentaje representan sobre las entradas de ese estado?

- Entradas: grabaciones_correspondencias_masivas.csv, descriptores_acusticos.csv, acousticbrainz_correspondencias_masivas.csv y acousticbrainz_masivo.csv.
- Ruta: Correspondencia → referencia local de Grabacion → AnalisisAcustico → Fuente.
- Salida: estado, total de track_id distintos, cantidad con jMIR, cantidad con AcousticBrainz y ambos porcentajes. Mostrar las tres categorías incluso si algún conteo es cero.
- Unidad: track_id distintos. No contar columnas de descriptores ni varias observaciones como entradas adicionales. jMIR y AcousticBrainz se cuentan por separado.
- Porcentaje: 100 × entradas con análisis / entradas del estado, redondeado a dos decimales. Si el denominador es cero, dejar el porcentaje sin vincular.
- Orden: aceptada, ambigua, sin_coincidencia_conservadora. Sin LIMIT.
- Un cero describe cobertura de la captura y del grafo exportado; no demuestra inexistencia de análisis en el dominio.

## CQ8 Géneros por nivel y fuente

Para los géneros de grabación local de tagtraum, los géneros de artista publicados en Wikidata mediante P136 y los géneros de grupo de lanzamientos de MusicBrainz, ¿cuántos sujetos distintos tienen cada género en su respectiva fuente y nivel?

- Entradas: cancion_genero.csv, wikidata_hechos.csv con propiedad = P136 y correspondencia única, grupo_lanzamiento_genero.csv y los catálogos de entidades asociados.
- Ruta: sujeto de cada nivel → AsignacionGenero → GeneroMusical; asignación → Fuente.
- Salida: nivel (Grabacion, Artista o GrupoLanzamientos), fuente, identificador de género, label e idioma del género y número de sujetos distintos.
- Unidad: URI local para Grabacion, artist_mbid para Artista y grupo_lanzamiento_mbid para GrupoLanzamientos. Los papeles mayoritario y minoritario de tagtraum se incluyen, pero no duplican un mismo sujeto para un mismo género.
- Orden: nivel y fuente ascendentes, cantidad descendente e identificador de género ascendente. Sin LIMIT.
- Las identidades de género permanecen separadas por vocabulario; no se fusionan Rock de tagtraum, rock de MusicBrainz o una entidad Wikidata solo por semejanza de labels. No se transfieren géneros entre niveles.

## Convenciones de ejecución

Los conjuntos de datos y las capturas utilizados quedan fijados por sus identificadores y huellas. Las preguntas basadas en el volcado completo excluyen hechos del piloto API para evitar mezclar alcances y versiones en una misma respuesta. La evidencia del piloto sigue preservada.

Labels e idiomas acompañan a los identificadores y no se utilizan como claves de identidad. Si hay varios labels, se selecciona uno de manera determinista: es, en, otros idiomas conocidos ordenados por tag y texto, y finalmente und. Las variantes regionales siguen su idioma base. Después se usa el texto del label como desempate. Esta selección no modifica los labels conservados.

Cada consulta requiere su archivo .rq y una respuesta exportada desde Fuseki sobre los mismos archivos Turtle que se entregan. La entrega requiere al menos cinco preguntas ejecutadas; los ocho IDs permanecen estables para relacionar consultas, resultados y documentación.
