# Knowledge tags

Read this when assigning knowledge tags or reviewing the taxonomy. Project discovery tags use
the separate purpose/domain convention in `refinery-project`.

Reuse the narrowest existing tag whose description fits. Find candidates with
`refinery_search_knowledge_tags` for known concepts, or `refinery_browse_knowledge_tags` to explore
a branch. Browsing without `parent_tag` starts at the roots; each call returns immediate children.
Use either route as needed. A tag whose meaning was already verified in the current task does not
need another lookup unless the relevant taxonomy changed.

Do not create a parallel spelling when an existing branch applies. Choose the root by meaning:
subject/domain → `domain`, output artifact → `artifact`, work type → `task`, technology → `tech`,
symptom or quality issue → `issue`. Use only these roots and one to three lowercase slug segments
separated by `/`, such as `domain/ml/feature-selection`. A parent tag search also matches descendants.

Taxonomy review checks used tags for missing or ambiguous descriptions and parallel branches.
Update descriptions using the current `taxonomy_updated_at`. Do not implicitly rename or delete
used tags.
