# Diccionario de datos

CSV UTF-8 con encabezado y separador coma. Los campos con comas o saltos usan comillas CSV. Vacío significa dato no disponible; no se reemplaza por cero. True/False son banderas. Los separadores `|` en campos de resumen no sustituyen las tablas relacionales.

Los campos `linea_fuente` son números de línea física, comenzando en 1. `url_evidencia` en la API identifica la respuesta guardada en data/raw/api mediante SHA-256 de su URL. En los volcados identifica el archivo original, complementado por tabla, línea y SHA-256. Los CSV con sufijo masivos describen el núcleo actual; recording_mbid_dump conserva la decisión de esta captura y recording_mbid conserva el piloto. Un grupo de lanzamientos no es una grabación ni una edición.

## acousticbrainz.csv

Valores para grabaciones reconciliadas. bpm en pulsos por minuto; tonalidad y escala tal como las reporta la fuente. average_loudness no se interpreta automáticamente como dB. Un 404 indica que no hubo datos en la consulta, no un valor cero.

Campos: `track_id`, `recording_mbid`, `bpm`, `tonalidad`, `escala`, `fuerza_tonalidad`, `danceability`, `average_loudness`, `fuente_id`, `metodo`, `url_evidencia`, `fecha_consulta`.

## acousticbrainz_correspondencias_masivas.csv

Una fila por las 100.000 canciones. Vincula track_id con el MBID de grabación aceptado en el volcado MusicBrainz. estado distingue disponible, sin_datos_en_volcado y sin_grabacion_reconciliada; las dos ausencias no equivalen a HTTP 404 ni a valores cero. evidencia_extraccion_sha256 identifica el manifiesto del recorrido completo.

Campos: `track_id`, `recording_mbid`, `estado`, `submission_offset`, `analisis_disponibles`, `fuente_id`, `fecha_snapshot`, `evidencia_extraccion_sha256`.

## acousticbrainz_masivo.csv

Una fila por recording_mbid, con 14 características del volcado compacto de 2022. Se elige submission_offset=0 en las tres familias, sin promediar análisis. analisis_disponibles cuenta índices de análisis distintos de ese MBID, no canciones; las filas repetidas no aumentan el conteo. bpm expresa pulsos por minuto; key_key y key_scale conservan los valores de la fuente. average_loudness no se interpreta como dB. Las columnas url, archivo_interno, sha256 y linea de cada familia identifican la evidencia original. No contiene fuerza de tonalidad, ausente del volcado compacto.

Campos: `recording_mbid`, `submission_offset`, `analisis_disponibles`, `average_loudness`, `dynamic_complexity`, `mfcc_zero_mean`, `bpm`, `bpm_histogram_first_peak_bpm_mean`, `bpm_histogram_first_peak_bpm_median`, `bpm_histogram_second_peak_bpm_mean`, `bpm_histogram_second_peak_bpm_median`, `danceability`, `onset_rate`, `key_key`, `key_scale`, `tuning_frequency`, `tuning_equal_tempered_deviation`, `fuente_id`, `fecha_snapshot`, `metodo`, `url_lowlevel`, `archivo_interno_lowlevel`, `sha256_lowlevel`, `linea_lowlevel`, `url_rhythm`, `archivo_interno_rhythm`, `sha256_rhythm`, `linea_rhythm`, `url_tonal`, `archivo_interno_tonal`, `sha256_tonal`, `linea_tonal`.

## artistas.csv

Clave artist_mbid suministrado. Agrupa nombres observados; el crédito completo no queda validado. Datos canónicos disponibles solo en las fuentes consultadas.

Campos: `artist_mbid`, `nombres_en_dataset`, `nombre_musicbrainz`, `tipo_musicbrainz`, `pais_musicbrainz`, `fuentes`, `estado_credito`, `url_musicbrainz`.

## artistas_masivos.csv

Clave artist_mbid. Metadatos del núcleo: nombre, tipo, área, fechas y género de la persona cuando existe. area_nombre puede representar distintos niveles geográficos; no se renombra automáticamente como país. genero_persona no es género musical.

Campos: `artist_mbid`, `nombre`, `tipo`, `area_mbid`, `area_nombre`, `fecha_inicio`, `fecha_fin`, `genero_persona`, `desambiguacion`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## cancion_genero.csv

Relación canción-género; clave compuesta track_id, genero, papel y fuente_id. Papel mayoritario o minoritario; se conserva el vocabulario tagtraum.

Campos: `track_id`, `genero`, `papel`, `fuente_id`, `identificador_fuente`, `metodo`, `archivo_fuente`, `linea_fuente`.

## canciones.csv

Tabla central; clave track_id. Columnas originales intactas y banderas de cobertura. fuentes_enriquecimiento usa musicbrainz_artista/musicbrainz_grabacion como categorías de la fuente musicbrainz. Un género de artista no rellena genero_mayoritario.

Campos: `track_id`, `title`, `artist_name`, `release`, `year`, `duration`, `artist_mbid`, `titulo_normalizado`, `artista_normalizado`, `lanzamiento_normalizado`, `anio_normalizado`, `incidencias`, `fuente_base`, `fuentes_enriquecimiento`, `enriquecida`, `genero_mayoritario`, `genero_minoritario`, `tiene_descriptores_jmir`, `recording_mbid`, `estado_musicbrainz_grabacion`, `estado_detalle_musicbrainz`, `estado_acousticbrainz`, `artista_qid`, `estado_wikidata`, `propiedades_artista_wikidata`, `hechos_artista_wikidata`, `hechos_artista_wikidata_sin_tipo`, `grupo_lanzamiento_mbid`, `estado_grupo_lanzamiento`, `recording_mbid_dump`, `estado_musicbrainz_dump`, `estado_acousticbrainz_dump`.

## creditos_grabacion.csv

Créditos por grabación; artista, orden, nombre acreditado y frase de unión. Los artistas externos adicionales también se incluyen en artistas.csv.

Campos: `recording_mbid`, `artist_mbid`, `nombre`, `nombre_acreditado`, `orden`, `union`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## creditos_grabaciones_masivos.csv

Grabación, artista, posición desde 1, nombre acreditado y frase de unión. Los participantes se resuelven en artistas_masivos.csv; no se infiere composición desde este crédito.

Campos: `recording_mbid`, `artist_mbid`, `nombre_acreditado`, `orden`, `union`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## creditos_grupo_lanzamiento.csv

Grupo, artista acreditado, orden, nombre y frase de unión. Describe el crédito del grupo, no certifica que cada canción tenga exactamente esos intérpretes.

Campos: `grupo_lanzamiento_mbid`, `artist_mbid`, `nombre`, `nombre_acreditado`, `orden`, `union`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `miembro`, `linea_archivo`, `fecha_snapshot`.

## descriptores_acusticos.csv

Una fila por track_id con 16 características jMIR. Media y desviación estándar de ocho descriptores. Nombres y valores originales; unidades no inferidas. Datos calculados previamente sobre fragmentos.

Campos: `track_id`, `Spectral_Centroid_Overall_Standard_Deviation_1`, `Spectral_Rolloff_Point_Overall_Standard_Deviation_1`, `Spectral_Flux_Overall_Standard_Deviation_1`, `Compactness_Overall_Standard_Deviation_1`, `Spectral_Variability_Overall_Standard_Deviation_1`, `Root_Mean_Square_Overall_Standard_Deviation_1`, `Fraction_Of_Low_Energy_Windows_Overall_Standard_Deviation_1`, `Zero_Crossings_Overall_Standard_Deviation_1`, `Spectral_Centroid_Overall_Average_1`, `Spectral_Rolloff_Point_Overall_Average_1`, `Spectral_Flux_Overall_Average_1`, `Compactness_Overall_Average_1`, `Spectral_Variability_Overall_Average_1`, `Root_Mean_Square_Overall_Average_1`, `Fraction_Of_Low_Energy_Windows_Overall_Average_1`, `Zero_Crossings_Overall_Average_1`, `fuente_id`, `identificador_fuente`, `metodo`, `archivo_fuente`, `linea_fuente`.

## eventos_lanzamientos_masivos.csv

Edición, país/área y fecha de publicación con precisión original. Conserva eventos múltiples y país desconocido vacío; no reemplaza el año de la canción.

Campos: `release_mbid`, `pais_area_mbid`, `pais_nombre`, `fecha`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## fuentes.csv

Catálogo de fuentes, archivos, URLs, condiciones declaradas, fechas y hashes. Los archivos API se verifican individualmente mediante el manifiesto.

Campos: `fuente_id`, `url`, `documentacion`, `archivo`, `sha256`, `licencia`, `fecha_descarga_utc`.

## grabacion_lanzamiento.csv

Relación muchos a muchos por recording_mbid y release_mbid. Procedencia en la consulta de la grabación.

Campos: `recording_mbid`, `release_mbid`, `fuente_id`, `url_evidencia`.

## grabacion_lanzamiento_masivo.csv

Par único recording_mbid/release_mbid; una pista fuente de respaldo y medio. La relación no indica que se hayan exportado todas las ediciones posibles.

Campos: `recording_mbid`, `release_mbid`, `track_mbid`, `numero_pista`, `medio_posicion`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## grabaciones.csv

Clave recording_mbid. Duración en milisegundos; no confundir con duration del MSD en segundos. Primera fecha reportada separada del año original. estado_detalle distingue entidades con detalle de las recuperadas solamente en búsquedas. Lista de lanzamientos no necesariamente completa.

Campos: `recording_mbid`, `titulo`, `duracion_ms`, `fecha_primer_lanzamiento`, `lista_lanzamientos_completa`, `estado_detalle`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## grabaciones_correspondencias_masivas.csv

Una fila por las 100.000 canciones. Estado aceptada, ambigua o sin_coincidencia_conservadora. candidatos_elegibles contiene todos los MBID que cumplen la regla en el volcado; solo la unicidad produce recording_mbid. recording_id es interno y depende de la instantánea.

Campos: `track_id`, `estado`, `recording_id`, `recording_mbid`, `candidatos_elegibles`, `metodo`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`.

## grabaciones_masivas.csv

Clave recording_mbid. Realización sonora reconciliada contra el volcado completo. duracion_ms en milisegundos, es_video y desambiguación originales. Las ediciones recuperadas se restringen a títulos compatibles con la entrada.

Campos: `recording_mbid`, `titulo`, `duracion_ms`, `desambiguacion`, `es_video`, `estado_detalle`, `alcance_lanzamientos`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## grupo_lanzamiento_candidatos.csv

Todos los grupos candidatos para cada track_id, incluidos ambiguos. Cada vínculo conserva línea y hash del archivo JSON original.

Campos: `track_id`, `grupo_lanzamiento_mbid`, `estado`, `linea_archivo`, `archivo_sha256`.

## grupo_lanzamiento_correspondencias.csv

Una fila por track_id. Correspondencia por título del álbum normalizado y MBID acreditado, con grupo único; no identifica una grabación ni una edición. Los candidatos ambiguos permanecen sin grupo aceptado.

Campos: `track_id`, `artist_mbid`, `release_original`, `grupo_lanzamiento_mbid`, `estado`, `candidatos`, `metodo`, `fuente_id`, `archivo_sha256`, `subconjunto_sha256`.

## grupo_lanzamiento_genero.csv

Grupo, género MusicBrainz, nombre y votos publicados. La asignación pertenece al grupo y no se hereda como género de canción; los votos no son una probabilidad.

Campos: `grupo_lanzamiento_mbid`, `genero_mbid`, `genero`, `votos`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `miembro`, `linea_archivo`, `fecha_snapshot`.

## grupos_lanzamientos.csv

Clave grupo_lanzamiento_mbid. Agrupa ediciones relacionadas; tipo primario, tipos secundarios y primera fecha publicada con precisión original. El año de la canción no se reemplaza.

Campos: `grupo_lanzamiento_mbid`, `titulo`, `tipo_primario`, `tipos_secundarios`, `fecha_primer_lanzamiento`, `desambiguacion`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `miembro`, `linea_archivo`, `fecha_snapshot`.

## isrc.csv

Identificadores ISRC publicados para una grabación. No se usan como claves primarias de canciones.

Campos: `recording_mbid`, `isrc`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## isrc_masivos.csv

Grabación e ISRC publicado, con tabla y línea de origen. Puede haber varios ISRC por grabación; no se usa como clave de canción.

Campos: `recording_mbid`, `isrc`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## lanzamiento_sello_masivo.csv

Edición, sello y número de catálogo. Puede existir número de catálogo con sello desconocido vacío. No representa una relación directa canción-sello ni artista-sello.

Campos: `release_mbid`, `label_mbid`, `numero_catalogo`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## lanzamientos.csv

Clave release_mbid. Una edición publicada; no se identifica por nombre de álbum. Fechas pueden tener solo año o año-mes.

Campos: `release_mbid`, `titulo`, `fecha`, `pais`, `estado`, `codigo_barras`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## lanzamientos_masivos.csv

Clave release_mbid. Edición publicada, estado, código de barras y MBID del grupo. La evidencia de su grupo está en el subconjunto relacional; el catálogo de grupos enriquecidos de la otra captura es independiente.

Campos: `release_mbid`, `titulo`, `estado`, `codigo_barras`, `grupo_lanzamiento_mbid`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## musicbrainz_artistas.csv

Entidades consultadas por MBID, incluyendo ID actual, fechas reportadas, nombre, tipo, país y URL.

Campos: `artist_mbid_suministrado`, `artist_mbid_actual`, `nombre`, `tipo`, `pais`, `area`, `inicio`, `fin`, `generos`, `fuente_id`, `url_evidencia`, `fecha_consulta`, `status_http`, `tipo_consulta`, `etiquetas`.

## musicbrainz_candidatos.csv

Candidatos recuperados y evidencia de título, artista, álbum y duración. puntaje es una heurística de ordenamiento; no una probabilidad. elegible no equivale a aceptada si hay varios candidatos o resultados truncados.

Campos: `track_id`, `recording_mbid`, `titulo`, `titulo_exacto`, `artista_mbid_presente`, `album_exacto`, `diferencia_duracion_s`, `elegible`, `puntaje`, `url_evidencia`.

## musicbrainz_correspondencias.csv

Una fila por canción de la submuestra: método, estado, candidato aceptado y evidencia. Las demás canciones constan como no_consultada en canciones.csv.

Campos: `track_id`, `artist_mbid_suministrado`, `nombre_artista_validado`, `estado`, `recording_mbid`, `candidatos`, `fuente_id`, `metodo`, `url_evidencia`, `fecha_consulta`, `estado_detalle`, `estado_acousticbrainz`.

## obras.csv

Clave work_mbid. Composición abstracta vinculada a una grabación mediante relaciones_musicbrainz.csv.

Campos: `work_mbid`, `titulo`, `tipo`, `idioma`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## obras_masivas.csv

Clave work_mbid. Composición asociada con una grabación aceptada, con título y tipo publicados. Se distingue de la realización sonora.

Campos: `work_mbid`, `titulo`, `tipo`, `desambiguacion`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## relaciones_grupo_lanzamiento.csv

Afirmaciones con sujeto grupo y objeto identificado por tipo/ID o URL. Conserva relación, dirección y atributos; las entidades externas referidas no se presentan como entidades descritas exhaustivamente.

Campos: `grupo_lanzamiento_mbid`, `relacion`, `direccion`, `objeto_tipo`, `objeto_id`, `objeto_nombre`, `atributos`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `miembro`, `linea_archivo`, `fecha_snapshot`.

## relaciones_musicales_masivas.csv

Clave relacion_id. Relación artista-grabación, grabación-obra o artista-obra; orientación entity0 a entity1 del esquema. Tipo identificado por MBID, frases directa/inversa, atributos y fechas. link_id y linea_link remiten al detalle de relación en la evidencia.

Campos: `relacion_id`, `sujeto_tipo`, `sujeto_mbid`, `relacion`, `tipo_relacion_mbid`, `objeto_tipo`, `objeto_mbid`, `frase_directa`, `frase_inversa`, `atributos`, `fecha_inicio`, `fecha_fin`, `link_id`, `linea_link`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## relaciones_musicbrainz.csv

Relaciones tipadas de grabaciones y obras hacia otras entidades. direccion se conserva tal como aparece en la respuesta; no invertir sin interpretarla.

Campos: `sujeto_tipo`, `sujeto_id`, `relacion`, `direccion`, `objeto_tipo`, `objeto_id`, `objeto_nombre`, `atributos`, `fuente_id`, `url_evidencia`, `fecha_consulta`.

## sellos_masivos.csv

Clave label_mbid y nombre del sello. Entidades relacionadas con ediciones compatibles de grabaciones aceptadas, sin inferir contratos vigentes de los artistas.

Campos: `label_mbid`, `nombre`, `fuente_id`, `url_evidencia`, `archivo_sha256`, `fecha_snapshot`, `tabla_fuente`, `linea_fuente`.

## wikidata_correspondencias.csv

Una o varias filas por artist_mbid. estado distingue única, ambigua y sin coincidencia. consulta_sha256 ubica la respuesta que incluyó ese MBID, incluso si no hubo coincidencia.

Campos: `artist_mbid`, `artista_qid`, `estado`, `metodo`, `fuente_id`, `consulta_sha256`, `fecha_consulta`.

## wikidata_entidades.csv

Clave entidad_qid/entidad_uri. Etiqueta en español, inglés de respaldo o vacío. La etiqueta no reemplaza la identidad y no implica equivalencia con vocabularios de otras fuentes.

Campos: `entidad_qid`, `entidad_uri`, `etiqueta`, `idioma`, `fuente_id`, `consulta_sha256`, `fecha_consulta`.

## wikidata_hechos.csv

Clave compuesta artist_mbid, artista_qid, propiedad y valor. Solo identificaciones únicas. P136 describe género del artista; P264 relaciona al artista con un sello, sin vigencia temporal inferida. P31 por sí solo no cuenta en cobertura sustantiva. Los nombres de objetos preservan idioma y evidencia separada.

Campos: `artist_mbid`, `artista_qid`, `propiedad`, `relacion`, `valor`, `tipo_valor`, `datatype`, `fuente_id`, `metodo`, `url_entidad`, `consulta_sha256`, `fecha_consulta`, `estado_correspondencia`, `etiqueta_valor`, `idioma_etiqueta`, `consulta_etiqueta_sha256`.
