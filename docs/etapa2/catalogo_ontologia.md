# Catálogo de la ontología

Generado desde `src/musica/etapa2/vocabulario.py` y `ontologia.py` mediante `python src/generar_ontologia.py`.

Namespace: `https://example.org/musica/`. Las etiquetas del vocabulario están en español (`@es`).

## Clases

| Clase | Superclase | Significado |
| --- | --- | --- |
| Artista | — | Participante musical; sus roles se expresan mediante relaciones. |
| Persona | Artista | Artista individual identificado explícitamente por la fuente. |
| Agrupacion | Artista | Artista colectivo identificado explícitamente por la fuente. |
| ObraMusical | — | Composición abstracta que puede tener varias grabaciones. |
| Grabacion | — | Realización sonora; su URI local se conserva al reconciliarla. |
| Lanzamiento | — | Edición publicada, no un ejemplar físico individual. |
| GrupoLanzamientos | — | Identidad musical que reúne ediciones relacionadas. |
| Album | GrupoLanzamientos | Grupo cuyo tipo primario declarado es Album. |
| Sencillo | GrupoLanzamientos | Grupo cuyo tipo primario declarado es Single. |
| EP | GrupoLanzamientos | Grupo cuyo tipo primario declarado es EP. |
| SelloDiscografico | — | Sello asociado a una edición publicada. |
| PublicacionDiscografica | — | Asociación entre edición y sello que conserva su número de catálogo. |
| GeneroMusical | — | Clasificación identificada dentro de su vocabulario de origen. |
| CreditoArtistico | — | Artista acreditado en una grabación o grupo, con nombre y orden publicados. |
| AsignacionGenero | — | Clasificación con fuente y calificadores como papel o votos. |
| AnalisisAcustico | — | Mediciones de un mismo análisis, fuente, índice y alcance. |
| Fuente | — | Proveedor de información. |
| CapturaFuente | — | Archivo, respuesta o instantánea utilizada como evidencia. |
| Correspondencia | — | Decisión de reconciliación con estado y método; no es identidad por sí sola. |

## Propiedades

Un dominio con «o» es una unión OWL. Dominio y rango permiten inferir tipos; no son controles de completitud.

| Propiedad | Tipo | Dominio | Rango | Significado |
| --- | --- | --- | --- | --- |
| compuso | Objeto | Artista | ObraMusical | Composición respaldada explícitamente por la fuente. |
| produjo | Objeto | Artista | Grabacion | Producción respaldada explícitamente por la fuente. |
| interpretaObra | Objeto | Grabacion | ObraMusical | Obra realizada por una grabación. |
| tieneGrabacion | Objeto | ObraMusical | Grabacion | Grabación que realiza una obra. |
| apareceEn | Objeto | Grabacion | Lanzamiento | Edición que contiene la grabación. |
| contieneGrabacion | Objeto | Lanzamiento | Grabacion | Grabación incluida en una edición. |
| perteneceAGrupo | Objeto | Lanzamiento | GrupoLanzamientos | Agrupación editorial de una edición. |
| tieneLanzamiento | Objeto | GrupoLanzamientos | Lanzamiento | Edición perteneciente a un grupo. |
| publicadoPor | Objeto | Lanzamiento | SelloDiscografico | Sello que publica una edición; el catálogo se conserva en la asociación. |
| tienePublicacion | Objeto | Lanzamiento | PublicacionDiscografica | Asociación editorial con sello y catálogo. |
| selloPublicacion | Objeto | PublicacionDiscografica | SelloDiscografico | Sello correspondiente a esta asociación editorial. |
| tieneCredito | Objeto | Grabacion o GrupoLanzamientos | CreditoArtistico | Crédito publicado para una grabación o grupo. |
| acreditaEntidad | Objeto | CreditoArtistico | Grabacion o GrupoLanzamientos | Entidad musical a la que pertenece el crédito. |
| artistaAcreditado | Objeto | CreditoArtistico | Artista | Artista del crédito; no implica composición ni producción. |
| tieneAsignacionGenero | Objeto | Grabacion o Artista o GrupoLanzamientos | AsignacionGenero | Clasificación explícita, sin herencia entre entidades musicales. |
| generoAsignado | Objeto | AsignacionGenero | GeneroMusical | Género de una asignación individual. |
| tieneAnalisis | Objeto | Grabacion | AnalisisAcustico | Análisis que describe el audio de esta grabación. |
| fuente | Objeto | owl:Thing | Fuente | Proveedor del recurso; dominio amplio para dominio y evidencia. |
| respaldadoPor | Objeto | owl:Thing | CapturaFuente | Captura que respalda el recurso; no representa una afirmación genérica. |
| tieneCorrespondencia | Objeto | Grabacion | Correspondencia | Decisión externa asociada a la referencia local. |
| titulo | Dato | Grabacion o ObraMusical o Lanzamiento o GrupoLanzamientos | string | Título publicado; no establece identidad. |
| identificador | Dato | owl:Thing | string | Identificador en su sistema de origen; no es una clave OWL. |
| mbid | Dato | owl:Thing | string | Identificador MusicBrainz respaldado por la fuente. |
| nombreAcreditado | Dato | CreditoArtistico | string | Nombre utilizado en el crédito original. |
| posicionCredito | Dato | CreditoArtistico | positiveInteger | Orden publicado, normalizado a base uno. |
| fraseUnion | Dato | CreditoArtistico | string | Texto que une este crédito con el siguiente. |
| numeroCatalogo | Dato | PublicacionDiscografica | string | Número del par edición-sello, conservado literalmente. |
| papelGenero | Dato | AsignacionGenero | string | Papel original: mayoritario o minoritario cuando la fuente lo declara. |
| votosGenero | Dato | AsignacionGenero | integer | Votos reportados por la fuente; no son una probabilidad. |
| indiceAnalisis | Dato | AnalisisAcustico | nonNegativeInteger | Índice de envío o análisis dentro de la fuente. |
| alcanceAnalisis | Dato | AnalisisAcustico | string | Alcance del audio analizado, por ejemplo fragmento. |
| tonica | Dato | AnalisisAcustico | string | Clave tonal literal de la fuente; C representa do en AcousticBrainz. |
| modo | Dato | AnalisisAcustico | string | Modo tonal literal; major representa mayor en AcousticBrainz. |
| estadoCorrespondencia | Dato | Correspondencia | string | Estado original: aceptada, ambigua o sin coincidencia conservadora. |
| metodoCorrespondencia | Dato | Correspondencia | string | Método utilizado en la reconciliación. |
| candidatoMBID | Dato | Correspondencia | string | Identificador candidato; no afirma identidad ni existencia de relaciones musicales. |
| sonoridadMedia | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: average_loudness; se conserva por análisis. |
| complejidadDinamica | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: dynamic_complexity; se conserva por análisis. |
| mediaMfccCero | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: mfcc_zero_mean; se conserva por análisis. |
| tempoBPM | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: bpm; se conserva por análisis. |
| mediaPrimerPicoBPM | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: bpm_histogram_first_peak_bpm_mean; se conserva por análisis. |
| medianaPrimerPicoBPM | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: bpm_histogram_first_peak_bpm_median; se conserva por análisis. |
| mediaSegundoPicoBPM | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: bpm_histogram_second_peak_bpm_mean; se conserva por análisis. |
| medianaSegundoPicoBPM | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: bpm_histogram_second_peak_bpm_median; se conserva por análisis. |
| bailabilidad | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: danceability; se conserva por análisis. |
| tasaAtaques | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: onset_rate; se conserva por análisis. |
| frecuenciaAfinacion | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: tuning_frequency; se conserva por análisis. |
| desviacionTemperamentoIgual | Dato | AnalisisAcustico | decimal | Valor de AcousticBrainz: tuning_equal_tempered_deviation; se conserva por análisis. |
| mediaCentroideEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Centroid_Overall_Average_1. |
| desviacionCentroideEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Centroid_Overall_Standard_Deviation_1. |
| mediaRolloffEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Rolloff_Point_Overall_Average_1. |
| desviacionRolloffEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Rolloff_Point_Overall_Standard_Deviation_1. |
| mediaFlujoEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Flux_Overall_Average_1. |
| desviacionFlujoEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Flux_Overall_Standard_Deviation_1. |
| mediaCompacidad | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Compactness_Overall_Average_1. |
| desviacionCompacidad | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Compactness_Overall_Standard_Deviation_1. |
| mediaVariabilidadEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Variability_Overall_Average_1. |
| desviacionVariabilidadEspectral | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Spectral_Variability_Overall_Standard_Deviation_1. |
| mediaRms | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Root_Mean_Square_Overall_Average_1. |
| desviacionRms | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Root_Mean_Square_Overall_Standard_Deviation_1. |
| mediaFraccionVentanasBajaEnergia | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Fraction_Of_Low_Energy_Windows_Overall_Average_1. |
| desviacionFraccionVentanasBajaEnergia | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Fraction_Of_Low_Energy_Windows_Overall_Standard_Deviation_1. |
| mediaCrucesPorCero | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Zero_Crossings_Overall_Average_1. |
| desviacionCrucesPorCero | Dato | AnalisisAcustico | decimal | Estadístico jMIR del fragmento: Zero_Crossings_Overall_Standard_Deviation_1. |
| artistaSuministrado | Objeto | Grabacion | Artista | Artista reportado en la entrada; no certifica el crédito completo ni su orden. |
| lanzamientoSuministrado | Dato | Grabacion | string | Texto original del lanzamiento; no establece identidad de una edición. |
| duracionSuministradaSegundos | Dato | Grabacion | decimal | Duración reportada por la entrada original, expresada en segundos. |
| isrc | Dato | Grabacion | string | Identificador ISRC reportado; no es una clave OWL. |
| archivoCaptura | Dato | CapturaFuente | string | Ruta relativa de la tabla consolidada en output/csv. |
| sha256Captura | Dato | CapturaFuente | string | Huella del CSV que permite recuperar la evidencia exacta y sus metadatos de origen. |

## Axiomas OWL

Once axiomas de cuatro tipos de construcción, además de las jerarquías y las uniones usadas en dominios y rangos.

| ID | Construcción | Términos | Justificación |
| --- | --- | --- | --- |
| A01 | disjunción | Persona, Agrupacion | Un artista individual no es un colectivo. |
| A02 | disjunción | Grabacion, ObraMusical | La realización sonora se distingue de la composición abstracta. |
| A03 | disjunción | Lanzamiento, GrupoLanzamientos | Una edición no es la identidad que agrupa sus ediciones. |
| A04 | inversa | apareceEn, contieneGrabacion | Ambas direcciones describen la misma inclusión de una grabación en una edición. |
| A05 | inversa | interpretaObra, tieneGrabacion | Ambas direcciones vinculan la obra con su realización sonora. |
| A06 | inversa | perteneceAGrupo, tieneLanzamiento | Ambas direcciones expresan la pertenencia de una edición al grupo. |
| A07 | inversa | tieneCredito, acreditaEntidad | Permite recorrer el crédito desde su grabación o grupo y viceversa. |
| A08 | cardinalidad | CreditoArtistico, artistaAcreditado | Cada crédito individual identifica exactamente un artista de clase Artista. |
| A09 | cardinalidad | CreditoArtistico, acreditaEntidad | Cada crédito pertenece exactamente a una entidad de la unión Grabacion o GrupoLanzamientos. |
| A10 | cardinalidad | AsignacionGenero, generoAsignado | Cada asignación individual identifica exactamente un GeneroMusical. |
| A11 | cadena de propiedades | tienePublicacion, selloPublicacion → publicadoPor | El sello de una asociación editorial publica su lanzamiento. |

## Interpretación y validación

Las cardinalidades son calificadas y exactas (1). Con mundo abierto, un valor ausente no prueba una inconsistencia; dos URI tampoco prueban dos individuos diferentes. No se declaran claves, propiedades inversamente funcionales ni diferencias entre individuos por sus identificadores locales.

La validación de etiquetas es una comprobación explícita sobre la unión de esquema e instancias: exige texto no vacío y un código de idioma válido en todas las etiquetas, como `es` para español o `en` para inglés. Acepta `und` cuando el idioma es desconocido. Los nodos estructurales OWL y las celdas de listas RDF quedan exentos. Los nodos anónimos de dominio no.

La generación y las pruebas estructurales no ejecutan un razonador OWL.
