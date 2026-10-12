# Mapeo de los datos consolidados al modelo musical

La generación RDF parte de los CSV de la etapa 1. Cada vínculo conserva su significado y alcance de fuente. Las tablas del piloto y de los volcados permanecen distinguibles; una correspondencia ambigua no se transforma en una relación musical aceptada.

| Tablas de entrada | Representación prevista | Regla de interpretación |
| --- | --- | --- |
| canciones.csv | Grabacion local y referencia a evidencia de entrada | track_id genera una URI estable. Títulos y créditos originales son metadatos reportados. El artista suministrado no certifica todos los participantes. |
| grabaciones_correspondencias_masivas.csv, musicbrainz_correspondencias.csv | Correspondencia | Los estados aceptados permiten recuperar hechos por recording_mbid. Los candidatos ambiguos se mantienen como evidencia. |
| grabaciones_masivas.csv, grabaciones.csv | Metadatos de la grabación identificada | No confundir duración en milisegundos con duration en segundos. No fusionar capturas silenciosamente. |
| artistas_masivos.csv, artistas.csv, musicbrainz_artistas.csv | Artista y clasificación respaldada | Person permite Persona; Group, Orchestra y Choir permiten Agrupacion. Otros tipos permanecen como Artista; no se convierten en personas por defecto. |
| creditos_grabaciones_masivos.csv, creditos_grabacion.csv | CreditoArtistico de grabación | Preservar artista, posición, nombre acreditado y unión. |
| creditos_grupo_lanzamiento.csv | CreditoArtistico de grupo | El sujeto acreditado es el grupo; no se propaga a todas sus grabaciones. |
| obras_masivas.csv, obras.csv | ObraMusical | Identidad basada en work_mbid, separada de Grabacion. |
| relaciones_musicales_masivas.csv, relaciones_musicbrainz.csv | compuso, produjo, interpretaObra y relaciones calificadas cuando sean necesarias | Usar tipo de relación y orientación; no inferir rol desde el nombre o crédito. Mantener evidencia no mapeada. |
| lanzamientos_masivos.csv, lanzamientos.csv | Lanzamiento | release_mbid identifica una edición, no un álbum abstracto. |
| grabacion_lanzamiento_masivo.csv, grabacion_lanzamiento.csv | apareceEn | Mantener relación muchos a muchos. La selección exportada no representa todas las ediciones existentes. |
| grupos_lanzamientos.csv | GrupoLanzamientos y tipos | grupo_lanzamiento_mbid identifica el grupo. Album, Single y EP son clasificaciones de grupo. |
| grupo_lanzamiento_correspondencias.csv, grupo_lanzamiento_candidatos.csv | Correspondencia con grupo | Una coincidencia de grupo no establece una edición ni confirma la identidad de una grabación. |
| eventos_lanzamientos_masivos.csv | Evento de publicación vinculado a una edición | Preservar país o área y precisión de fecha. No reemplazar el año original. |
| sellos_masivos.csv, lanzamiento_sello_masivo.csv | SelloDiscografico y asociación con edición | El número de catálogo pertenece a la asociación. No inferir contratos vigentes con artistas. |
| cancion_genero.csv | GeneroMusical y AsignacionGenero de grabación local | Preservar vocabulario tagtraum, papel y fuente. |
| grupo_lanzamiento_genero.csv | GeneroMusical y AsignacionGenero de grupo | Mantener MBID del género, votos y fuente; no heredar a grabaciones. |
| descriptores_acusticos.csv | AnalisisAcustico jMIR | Vincular a la referencia local por track_id y conservar el alcance de fragmento. No inferir unidades. |
| acousticbrainz_masivo.csv, acousticbrainz.csv | AnalisisAcustico AcousticBrainz | Conservar sujeto recording_mbid, índice, captura y características disponibles. Un mismo análisis no se duplica por cada entrada que lo referencia. |
| acousticbrainz_correspondencias_masivas.csv | Evidencia de cobertura de análisis | Distinguir ausencia de datos en el volcado y ausencia de grabación reconciliada. |
| isrc_masivos.csv, isrc.csv | Identificadores de grabación | ISRC no es la clave de la entrada ni se convierte automáticamente en propiedad inversamente funcional. |
| wikidata_correspondencias.csv, wikidata_hechos.csv, wikidata_entidades.csv | Evidencia de identidad y hechos tipados de artista | Usar únicamente correspondencias únicas. Preservar labels e idiomas. P136 clasifica al artista, no sus grabaciones. La alineación con ontologías externas no forma parte de esta etapa. |
| fuentes.csv | Fuente y CapturaFuente | Preservar proveedor, archivo, URL, huella y fecha. |
| musicbrainz_candidatos.csv, relaciones_grupo_lanzamiento.csv | Evidencia y relaciones seleccionadas | Los candidatos no son correspondencias aceptadas. Mapear relaciones explícitas útiles para las preguntas y conservar las restantes en la evidencia. |

## Reglas comunes

Cada recurso descrito o referenciado como entidad del dominio requiere label e idioma. Un nombre faltante produce una descripción determinista basada en tipo e identificador; no una identidad musical inventada. Los enlaces a documentos de evidencia no requieren convertir cada URL en una entidad musical.

Las identidades de créditos, asignaciones, análisis y correspondencias se derivan de claves compuestas estables, con el contexto de fuente o captura necesario. Una posición por sí sola no identifica un crédito globalmente. Una etiqueta por sí sola no identifica un género globalmente.

Los valores desconocidos se omiten como hechos musicales y su ausencia puede documentarse en la evidencia. Las fechas parciales mantienen su precisión; no se rellenan meses ni días. Los conteos y métricas distinguen filas originales, referencias locales, MBID aceptados y análisis.
