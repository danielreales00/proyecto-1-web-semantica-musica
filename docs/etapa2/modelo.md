# Modelo musical de la etapa 2

El modelo representa obras, grabaciones, artistas y publicaciones musicales. Los registros originales y las decisiones de reconciliación se conservan como evidencia, sin convertir cada fila de entrada en una clase del dominio musical.

## Entidades e identidad

| Entidad | Significado e identidad |
| --- | --- |
| Artista | Participante musical identificado por MBID cuando está disponible. |
| Persona | Artista individual, según una clasificación explícita de la fuente. |
| Agrupacion | Artista colectivo. Los tipos no resueltos permanecen como Artista. |
| ObraMusical | Composición abstracta, identificada por work_mbid. |
| Grabacion | Realización sonora descrita por una entrada. Conserva una URI local estable basada en track_id; la reconciliación no cambia esa URI. |
| Lanzamiento | Edición publicada, identificada por release_mbid. No representa un ejemplar físico individual. |
| GrupoLanzamientos | Identidad que reúne ediciones relacionadas, identificada por grupo_lanzamiento_mbid. |
| Album | Especialización de GrupoLanzamientos para grupos cuyo tipo primario sea Album. Single y EP mantienen su tipo propio. |
| SelloDiscografico | Sello asociado con ediciones publicadas, identificado por label_mbid. |
| GeneroMusical | Clasificación con identidad propia en su vocabulario de origen. Un mismo nombre en fuentes diferentes no establece equivalencia. |
| CreditoArtistico | Crédito que conserva artista, sujeto acreditado, posición, nombre y frase de unión. Puede acreditar una grabación o un grupo de lanzamientos. |
| AsignacionGenero | Clasificación de un sujeto con fuente y calificadores como papel o votos cuando existen. |
| AnalisisAcustico | Conjunto de características del audio descrito por una entrada o una grabación reconciliada, con fuente, índice y alcance de medición. |
| Fuente | Proveedor de información. |
| CapturaFuente | Respuesta, archivo o instantánea utilizada como evidencia. |
| Correspondencia | Decisión de reconciliación con sus candidatos, estado y método. Pertenece a la evidencia. |

El código no debe confundir el identificador de pista del MSD con el identificador de grabación de MusicBrainz. Para relacionar tablas MusicBrainz con las grabaciones locales se utiliza la correspondencia aceptada. Cuando varias entradas tienen el mismo MBID aceptado, los hechos externos pueden recuperarse para cada referencia local; la identidad compartida se documenta y solo se expresa lógicamente cuando la decisión establece identidad completa.

## Relaciones musicales

| Sujeto | Propiedad | Objeto |
| --- | --- | --- |
| Artista | compuso | ObraMusical |
| Artista | produjo | Grabacion |
| Grabacion | interpretaObra | ObraMusical |
| Grabacion | apareceEn | Lanzamiento |
| Lanzamiento | perteneceAGrupo | GrupoLanzamientos |
| Lanzamiento | publicadoPor | SelloDiscografico |
| Grabacion o GrupoLanzamientos | tieneCredito | CreditoArtistico |
| CreditoArtistico | artistaAcreditado | Artista |
| Sujeto clasificado | tieneAsignacionGenero | AsignacionGenero |
| AsignacionGenero | generoAsignado | GeneroMusical |
| Grabacion | tieneAnalisis | AnalisisAcustico |

Un crédito publicado no implica automáticamente composición, producción ni una función instrumental concreta. Estas relaciones requieren hechos explícitos. Un número de catálogo asociado a un par edición-sello se conserva en una relación calificada, en lugar de atribuirlo a todos los sellos o a todas las ediciones.

## Identidad y conocimiento incompleto

Las URI locales de grabación se generan de manera determinista y permanecen estables aunque mejore la reconciliación. Tener nombres distintos no implica que dos recursos denoten grabaciones distintas. No se generan declaraciones owl:differentFrom a partir de track_id distintos. owl:sameAs se reserva para identidad completa respaldada por evidencia.

Una correspondencia desconocida no establece la inexistencia de una obra, artista, edición o registro MusicBrainz. Una coincidencia ambigua no añade las relaciones de ninguno de sus candidatos. Los campos ausentes no producen ceros, fechas inventadas ni nombres supuestos.

Los conteos de recursos locales se distinguen de los conteos de MBID aceptados y de los conteos de filas de entrada. No se presentan como un número probado de grabaciones distintas en el mundo.

## Análisis y clasificación

jMIR conserva el alcance de fragmento y su vínculo al identificador de entrada. AcousticBrainz conserva el MBID analizado y submission_offset. Los análisis de fuentes distintas no se fusionan; sus valores tampoco se promedian. Cada análisis puede tener propiedades de datos para sus características. Una observación separada se introduce solo cuando un valor requiere metadatos propios.

Los géneros de artistas y grupos de lanzamientos no se heredan a sus grabaciones. Los votos de una clasificación no son una probabilidad. La fecha de un lanzamiento no sustituye el año suministrado por el dataset.

## Etiquetas y lenguaje

Toda clase, propiedad e instancia de dominio o evidencia exportada requiere al menos un rdfs:label explícito y no vacío. Se incluyen los recursos que aparecen únicamente como objetos. Todos los labels requieren una etiqueta de idioma BCP 47 válida.

El vocabulario y las descripciones generadas en español usan @es. Los nombres y títulos preservan su idioma conocido; si no se puede determinar, usan @und. El idioma del label no se deduce de la nacionalidad del artista ni del idioma de la canción. Las etiquetas no establecen identidad.

Los recursos anónimos de dominio también deben tener labels. Las restricciones OWL y celdas de listas RDF son estructuras de sintaxis y quedan fuera de esta obligación. La validación se aplica a ontology.ttl e instances.ttl juntos y debe impedir una entrega con recursos sin label o etiquetas vacías, sin idioma o inválidas.

## Formalización OWL

Las jerarquías y propiedades inversas expresan relaciones del dominio. La disjointness separa obra y grabación, edición y grupo, y persona y agrupación. Las cardinalidades se aplican a estructuras definidas, como un crédito con un artista y un sujeto acreditado. Los créditos de grupos no deben restringirse accidentalmente a grabaciones.

Compositor y productor son roles compatibles, expresados por relaciones. Las clases derivadas de esos roles pueden definirse mediante OWL si las consultas requieren razonamiento. El proyecto debe documentar cualquier materialización o configuración de inferencia utilizada; cargar axiomas no equivale a configurar un razonador.

## Referencias

- [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/)
- [Release Group en MusicBrainz](https://musicbrainz.org/doc/Release_Group)
- [Release en MusicBrainz](https://musicbrainz.org/doc/Release)
- [rdfs:label](https://www.w3.org/TR/rdf-schema/#ch_label)
- [BCP 47](https://www.rfc-editor.org/rfc/rfc5646.html)
