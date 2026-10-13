# Stage 2 Ontology Modeling Decisions

This log records agreed changes to the musical ontology for the second delivery. Implementation follows these decisions while preserving the source data and evidence.

## Remove the generic assertion class

Decision agreed on October 12, 2026: remove `AfirmacionExterna` from the revised ontology.

Represent supported musical facts through explicit properties, such as `compuso`, `produjo`, `interpretaObra`, `apareceEn`, `perteneceAGrupo`, and `publicadoPor`.

Use a specific relationship resource only when the relationship carries additional information that must be preserved. Examples include `CreditoArtistico` for credited name and order, `AsignacionGenero` for classification source and qualifiers, and a musical participation resource when role, instrument, or dates are required.

The specific relationship resources are introduced only for information present in the source data or needed by the competency questions. They do not replace every direct relationship.

Keep source relationships that have not been mapped in the preserved evidence files. Removing the generic ontology class does not discard raw evidence.

## Preserve release groups and editions

Retain `GrupoLanzamientos` as the identity of an album, single, or EP across its published editions. Keep `Lanzamiento` for a particular edition, with its publication events, label associations, and identifiers.

Use `perteneceAGrupo` to relate an edition to its group. A group match alone does not establish a particular edition or its track listing. The current Phase 1 data includes independent group matches and group-level genre assignments, which should preserve that scope.

Reference: [MusicBrainz release group documentation](https://musicbrainz.org/doc/Release_Group).

## Require readable labels throughout the ontology

Decision agreed on October 12, 2026: every project class, property, ontology resource, and exported domain or evidence instance must have at least one explicit, nonempty `rdfs:label`. This includes referenced artists, works, recordings, release groups, editions, labels, genres, credits, assignments, analyses, sources, captures, and correspondences, including domain instances represented by blank nodes.

Every `rdfs:label` must be a language-tagged literal with a valid BCP 47 tag. Use readable Spanish labels tagged `@es` for project vocabulary and Spanish generated descriptions. Preserve names, titles, and language tags from sources for musical instances. Use the known language of the label text, not the language of the song, artist nationality, interface, identifier, or source provider. If the label language cannot be determined, use `@und` rather than guessing. Multiple labels in different languages are allowed; translations are not required for every instance.

Label preference is the authoritative source name or title for the entity, followed by a compatible reported name, followed by a deterministic descriptive fallback. If no name is available, use the entity type and stable identifier, such as `Grabación sin nombre disponible (MBID ...)`, without inventing a name. Label generation does not establish identity or entity equivalence.

Generate contextual labels for relationship and evidence instances, such as `Crédito artístico 2 de la grabación X` or `Análisis jMIR de la grabación X`. Record whether each label was obtained from a source or generated in the label coverage report.

Anonymous OWL restriction expressions and RDF list cells are structural syntax rather than domain instances and do not require labels. Standard RDF, RDFS, OWL, and XSD vocabulary is not redefined by the project. External domain entities used as instance objects still require labels in the exported graph, while evidence URLs used only as document links are not treated as domain entities.

Enforce this policy with explicit validation of the serialized `ontology.ttl` and `instances.ttl`, considered together. Enumerate all project vocabulary terms and domain and evidence resources, including object-only references, and require at least one label containing non-whitespace text. Validate every `rdfs:label` as a language-tagged literal with a valid BCP 47 tag. The build fails if any required resource is unlabeled or any label is empty, untagged, or has an invalid tag; the coverage report must show 100 percent label and language-tag coverage, zero missing labels, and a separate count of `@und` labels. OWL open-world reasoning does not enforce exported label completeness. These generation and validation checks are required implementation work.

Reference: [RDF Schema label specification](https://www.w3.org/TR/rdf-schema/#ch_label).

Reference for undetermined language: [BCP 47 language tags](https://www.rfc-editor.org/rfc/rfc5646.html#section-4.1).
