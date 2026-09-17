# Proyecto de Web Semántica · Etapa 1

Entrega del grupo 2. Se conservan las 100.000 canciones y sus valores originales. El enriquecimiento incorpora datos de jMIR, tagtraum, Wikidata, MusicBrainz y AcousticBrainz. La unión de las fuentes aporta información a 99.990 canciones.

## Archivos para entregar

- `output/entrega_final_latex.zip`: paquete completo con código, documentos, datos y evidencia.
- `output/pdf/informe_final.pdf`: informe final de cuatro páginas, incluidas las referencias.
- `output/pdf/modelo_anexo.pdf`: modelo conceptual preliminar y consultas SPARQL.
- `output/csv/`: 39 tablas consolidadas. `canciones.csv` contiene una fila por canción suministrada.
- `docs/diccionario_datos.md`: significado de los campos, identificadores y procedencia.
- `src/`, `tests/`, `exploraciones/sparql/` y `latex/`: código, pruebas, consultas y fuentes editables de los documentos.
- `data/`: entradas y evidencia necesarias para repetir el proceso sin consultar los servicios externos.
- `manifiesto_archivos.json`: tamaño y SHA-256 de cada archivo del paquete.

El anexo conceptual y los CSV forman parte de los entregables del enunciado. No basta con entregar únicamente el informe y el código.

El repositorio público es [danielreales00/proyecto-1-web-semantica-musica](https://github.com/danielreales00/proyecto-1-web-semantica-musica). El [paquete de entrega](https://github.com/danielreales00/proyecto-1-web-semantica-musica/releases/tag/entrega-etapa-1) incluye los datos y la evidencia que no se guardan en el historial Git. Para reproducir, descarga y descomprime `entrega_final_latex.zip`, y trabaja dentro de `entrega_etapa_1/`.

## Instalación

Se requiere Python 3.11 o posterior. La verificación de esta entrega se realizó con Python 3.13. Las dependencias están fijadas en `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

La instalación de dependencias requiere conexión si no están disponibles en la caché. Para compilar los PDF también se necesita Tectonic. La primera compilación puede descargar sus paquetes TeX:

```bash
python latex/compilar.py
```

Después de esa preparación, la reproducción completa funciona sin HTTP. Los PDF finales ya están incluidos. Los fuentes también se pueden compilar con pdfLaTeX u Overleaf, conservando las carpetas `latex/` y `exploraciones/sparql/` con su estructura relativa.

## Reproducir los resultados

Para reconstruir los CSV, la comparación inicial de fuentes, las ocho consultas SPARQL y los dos PDF:

```bash
python src/ejecutar.py --offline
```

El código bloquea las solicitudes HTTP, verifica la evidencia conservada y recalcula los resultados. El grafo de SPARQL se crea desde cero en una carpeta temporal y se elimina al terminar. Cada consulta se comprueba mediante un recorrido independiente de los CSV.

Para reconstruir únicamente los datos, sin necesitar Tectonic:

```bash
python src/ejecutar.py --offline --solo-datos
```

Para trabajar en una carpeta nueva, que no debe existir:

```bash
python src/ejecutar.py --offline --destino ../reproduccion_etapa_1
```

Solo se copian las entradas seleccionadas. Los CSV finales, las respuestas de SPARQL y los PDF se generan durante esa ejecución.

## Verificar la entrega

```bash
python src/verificar_entrega.py
```

Este comando ejecuta las pruebas automatizadas y repite el proceso completo en una carpeta temporal sin resultados precalculados. Compara los 39 CSV byte a byte, las métricas, la comparación de Wikidata y DBpedia, las ocho respuestas SPARQL y el texto de ambos PDF. El resultado queda en `docs/reproducibilidad_entrega.json`. Las fechas de ejecución y los metadatos internos de los PDF pueden variar.

La reconstrucción necesita espacio temporal adicional para los CSV intermedios y el grafo. La verificación elimina su copia de trabajo al terminar. Los archivos temporales de una ejecución directa se pueden retirar después de validar y preparar de nuevo el paquete:

```bash
python src/empaquetar.py
python src/limpiar_entrega.py --aplicar
```

La limpieza comprueba la integridad del paquete y de sus archivos antes de borrar copias, cachés e intermedios ajenos a la entrega. Conserva los archivos seleccionados y el entorno `.venv`, si existe.

## Código que se conserva

`src/` contiene 29 módulos. Cada uno participa en la reproducción, en sus verificaciones o en la adquisición opcional de las fuentes. El contenido del informe se mantiene en `latex/`, separado de los programas que procesan datos.

| Función | Archivos en `src/` |
|---|---|
| Ejecutar, verificar y preparar la entrega | `ejecutar.py`, `archivos_entrega.py`, `verificar_entrega.py`, `empaquetar.py`, `limpiar_entrega.py` |
| Preparar la entrada y consultar las fuentes iniciales | `diagnostico.py`, `descargar.py`, `fuentes_masivas.py`, `wikidata.py`, `wikidata_etiquetas.py`, `dbpedia.py`, `comparar_fuentes.py` |
| Reconstruir e integrar el piloto de las API | `musicbrainz.py`, `auditar_cache_musicbrainz.py`, `consolidar_piloto.py`, `integrar.py` |
| Integrar la ampliación final | `ampliar_artistas.py`, `ampliar_albumes.py`, `consolidar_musicbrainz_completo.py`, `consolidar_acousticbrainz_dump.py`, `integrar_ampliacion.py` |
| Repetir la adquisición y el filtrado de las bases completas | `descargar_musicbrainz_completo.py`, `extraer_musicbrainz_completo.py`, `detallar_musicbrainz_completo.py`, `descargar_musicbrainz_dump.py`, `descargar_acousticbrainz_dump.py`, `extraer_acousticbrainz_dump.py` |
| Validar los datos | `validar.py`, `validar_ampliacion.py` |

Se retiraron los scripts de resúmenes anteriores, el diagnóstico puntual de la API y los dos programas del mapeo histórico de 2016. También se eliminaron el generador antiguo de PDF basado en ReportLab, los generadores de notas auxiliares y las copias de consultas. El anexo utiliza los mismos archivos SPARQL que ejecuta el código. Las respuestas originales que respaldan el piloto se conservan porque forman parte de los resultados del informe.

Ruff revisa imports, errores comunes, formato y complejidad ciclomática. El límite de complejidad es 10 por función, sin excepciones a esa regla. Para ejecutar las mismas comprobaciones que GitHub:

```bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
```

## Evidencia que se conserva

- `grupo_2.csv`: entrada original del curso.
- `data/raw/`: archivos publicados de jMIR y tagtraum, respuestas de las API y de las consultas a Wikidata y DBpedia, y subconjuntos vinculados de MusicBrainz y AcousticBrainz.
- Los subconjuntos incluyen los candidatos necesarios para revisar aceptaciones y ambigüedades. Sus metadatos identifican el archivo completo, la fecha, la línea y el SHA-256.
- `data/processed/api_derivadas/`: respuestas individuales extraídas de lotes del piloto. Mantienen la solicitud lógica y el enlace a la respuesta original.
- `data/processed/estado_servicios/`: evidencia de los fallos y pausas del servicio durante la extracción.
- `output/sparql/`: resultados y comprobaciones de las ocho consultas. El almacén del grafo se regenera.

En `docs/` solo se conservan el diccionario, las métricas finales, la comparación de fuentes y la comprobación de reproducibilidad. Los diagnósticos intermedios se vuelven a calcular durante el proceso y se retiran al preparar la entrega.

Las bases completas descargadas, las versiones anteriores de los documentos, los paquetes antiguos y las copias de verificación se excluyen. Para reproducir los resultados publicados se utilizan los subconjuntos y respuestas conservados.

## Repetir la adquisición de las bases completas

Esta operación opcional requiere conexión y varios GB de espacio. Permite repetir también el filtrado de los archivos originales:

```bash
python src/ejecutar.py --offline --solo-datos
python src/descargar_musicbrainz_completo.py
python src/extraer_musicbrainz_completo.py
python src/detallar_musicbrainz_completo.py
python src/descargar_musicbrainz_dump.py release-group
python src/ampliar_albumes.py --extraer
python src/descargar_acousticbrainz_dump.py
python src/extraer_acousticbrainz_dump.py
python src/ejecutar.py --offline
```

Las fechas utilizadas son `20260916-002105` para el núcleo MusicBrainz, `20260912-001001` para sus grupos de lanzamientos y `20220623` para los archivos AcousticBrainz. Los descargadores verifican las sumas oficiales. La extracción AcousticBrainz requiere `zstd` y las grabaciones ya reconciliadas en `output/csv/grabaciones_masivas.csv`. La reproducción habitual desde la evidencia no necesita `zstd`.

Una captura nueva de una fuente puede producir resultados diferentes. Las consultas originales conservan fecha y respuesta. Para consultar nuevamente MusicBrainz o Wikidata se debe configurar su User-Agent con aplicación y contacto, y respetar las pausas del servicio.

## Interpretación y condiciones de las fuentes

Los géneros de artistas y grupos de lanzamientos mantienen ese nivel y no se trasladan a las canciones. El MBID de artista suministrado puede representar solo una parte del crédito original. Las correspondencias ambiguas no se aceptan. El año cero permanece en el campo original y queda vacío en el campo normalizado. Las fechas de reedición no lo reemplazan.

Los descriptores acústicos proceden de análisis publicados. jMIR describe fragmentos. AcousticBrainz utiliza el mismo índice de análisis cero en sus tres familias y aporta hasta 14 características por grabación vinculada. La cobertura no implica que todos los atributos estén completos.

Las condiciones se registran en `output/csv/fuentes.csv`. jMIR declara CC BY-NC-SA 2.0 y tagtraum limita el uso a investigación no comercial. El núcleo MusicBrainz es CC0 y sus datos suplementarios tienen condiciones adicionales. AcousticBrainz y los datos estructurados de Wikidata son CC0.
