# Consultas de competencia y resultados

Las ocho consultas están en `consultas/etapa2`. Se ejecutan con `python src/consultar_etapa2.py`, usando el endpoint de `src/configuracion.py`. No tienen `LIMIT`: los CSV y JSON contienen todos los resultados. Se usa la unión de los grafos de esquema e instancias, sin inferencia automática.

| Pregunta | Filas | Entidades principales distintas |
| --- | ---: | --- |
| 1. Rock mayoritario y tempo > 120 BPM | 2.731 | 2.709 referencias de grabación |
| 2. Créditos y orden | 2.350 | 1.042 referencias de grabación |
| 3. Obras, grabaciones y compositores | 278 | 96 obras |
| 4. Ediciones y grupos | 63.643 | 15.635 referencias de grabación |
| 5. Sellos, ediciones y catálogos | 56.819 | 4.388 sellos |
| 6. Créditos con persona y agrupación | 489 | 389 referencias de grabación |
| 7. AcousticBrainz: do mayor y tempo > 120 BPM | 789 | 789 análisis |
| 8. Géneros por categoría | 1.968 | 1.968 géneros identificados en sus vocabularios |

Las filas pueden multiplicarse por análisis, créditos, compositores o ediciones. No deben interpretarse automáticamente como número de grabaciones.

## Interpretación de los identificadores

- En la pregunta 1, Rock es el género del vocabulario tagtraum y el papel debe ser `mayoritario`. El tempo pertenece a un análisis enlazado a la grabación.
- En las preguntas 2 y 6 se exige la misma captura para los créditos comparados. La posición se conserva en base uno; si una fuente contiene un empate, se presenta tal cual, sin inventar una posición.
- En la pregunta 3, las grabaciones se cuentan por MBID aceptado. Así, dos referencias locales al mismo MBID no cumplen por sí solas el umbral. Se cuentan artistas por su URI, cuya clave es su MBID.
- En las demás preguntas se devuelven referencias locales de grabación, que conservan `track_id`. Los conteos son operativos sobre identificadores, no una demostración de `owl:differentFrom`.
- La pregunta 4 conserva la edición aunque no haya un grupo conocido. La pregunta 5 conserva la edición aunque falte título o catálogo; el catálogo siempre se une por edición y sello.
- La pregunta 7 exige tónica `C`, modo `major` y tempo mayor que 120 en el mismo análisis de AcousticBrainz. No mezcla capturas.
- La pregunta 8 incluye géneros sin miembros de una categoría con un conteo de cero. No fusiona un género de Wikidata, MusicBrainz y tagtraum por compartir nombre.

## Archivos de evidencia

Los resultados completos de referencia se versionan comprimidos en `docs/etapa2/resultados/*.csv.gz`. El paquete de entrega incluye también CSV y JSON sin comprimir bajo `output/etapa2/consultas`. Los JSON conservan los tipos de los valores y las variables no ligadas; en CSV, una celda vacía representa un valor no ligado.

`docs/etapa2/evidencia/consultas.json` registra endpoint, respuesta HTTP, hash de la consulta, filas y duración observada. El tiempo no es una comparación de rendimiento: depende de cachés y recursos del equipo.

## Validación semántica

Las pruebas incluyen situaciones donde una consulta debe devolver cero filas: créditos de capturas diferentes, dos referencias de una misma grabación, catálogos de otro sello y tonalidad/tempo repartidos en análisis distintos. También verifican que la pregunta 8 no multiplique conteos por asignaciones repetidas.

HermiT se ejecuta por separado:

```bash
python -m pip install -r requirements-owl.txt
python src/verificar_owl.py --docker-java
```

Con Java instalado localmente se puede omitir `--docker-java`. La revisión usa el esquema completo y casos controlados. Confirma consistencia del esquema y seis inferencias; exige detectar dos casos deliberadamente inconsistentes. No ejecuta HermiT sobre las 742.915 instancias. Los controles del conjunto completo están en `instances.validacion.json`.

## Auditoría independiente y extractos de evidencia

```bash
python src/auditar_consultas.py
python src/generar_evidencias_consultas.py
```

La auditoría reconstruye las ocho respuestas directamente desde los CSV, sin ejecutar SPARQL ni importar el generador RDF. Compara conjuntos completos de filas y columnas, normaliza los BPM por valor decimal y detecta filas faltantes, sobrantes o duplicadas. Las ocho consultas coinciden: cero diferencias y cero duplicados. `evidencia/auditoria_consultas.json` registra huellas SHA-256 de entradas, consultas y resultados.

La PC3 cuenta los artistas del conjunto de grabaciones: una grabación sin crédito conocido se conserva si la obra cumple ambos umbrales. Una prueba de regresión cubre esta situación.

Hay valores no ligados: 44 filas sin compositor (PC3), 40 sin grupo (PC4) y 9.932 sin catálogo (PC5). La consulta responde con el conocimiento disponible; esas filas no proporcionan todos los campos solicitados. Ausencia no equivale a inexistencia.

`evidencia/muestras_consultas.json` adjunta filas reales y nombres recuperados de los CSV. El PDF presenta estos extractos junto a cada pregunta. Los extractos no sustituyen los resultados completos ni la auditoría; las etiquetas añadidas solo facilitan su lectura.
