---
name: refinery-memory
description: Knowledge Refineryのexperienceから再利用できる原則を抽出し、project・shared memoryを提案・記録・改善するときに使う。検索だけ、または単一試行の記録はrefinery-experienceを使う。
---

# Refinery memory

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Input is the current repo, a candidate principle or extraction
question, and supporting experience IDs found during review. If the request is proposal-only,
return the candidate, sources, scope, and limits without recording it.

1. Apply the shared operating rules' repo-scoped access check before retrieving knowledge.
2. Pass the repository's absolute path as `project_path` to every repo-scoped MCP tool. Search in this order: current project memory together with shared memory, current project experiences, then cross-project knowledge only when local evidence is insufficient. For a bounded cross-project search, choose IDs with `refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded set is defensible. Never combine `project_ids` with `all_projects: true`. Update a matching principle instead of duplicating it.
3. Read every supporting experience with `refinery_get_experience`. For cross-project evidence, pass the qualified `project-id/experience-id` source and check its evidence, applicability conditions, counterexamples, and confidence.
4. Keep project-specific principles in project memory. Normally require at least two experiences that show repetition or complementary validation, and use unqualified experience IDs. A single source is allowed only when the user explicitly asks to preserve it as memory; narrow the scope, state the unverified limits in the body, and do not assign high confidence.
5. Treat shared memory as a user-approved promotion. Independent experiences from at least two projects must support the same principle and every source must use `project-id/experience-id`, but satisfying that schema is not approval. Present the candidate principle, scope, limits, counterexamples, confidence, and source IDs, and call `refinery_record_memory(shared: true)` only after explicit user approval. Approval already given for that unchanged candidate is sufficient; new material evidence or a scope change requires reconsidering the candidate.
6. Record with `refinery_record_memory`, include every supporting experience ID, and read the result back with `refinery_get_memory`. Use the returned `scope`: for project memory pass its returned `project_id`; for shared memory use `scope: shared` and omit `project_id`. When updating shared memory, keep `shared: true`.

Creating a new memory omits `expected_updated_at`. Updating an existing memory requires the exact `updated_at` returned by `refinery_get_memory`; pass it as `expected_updated_at`. On update, omitted optional fields are preserved, an explicit empty list clears a list field, and `clear_confidence: true` explicitly clears confidence. If the server reports a stale revision, read the current memory again and reconcile the competing change instead of retrying blindly.

Write the reusable principle in `summary`. Put conditions, limits, counterexamples, and operational guidance in the body. Keep detailed attempt history in the source experiences.

Never create memory without `source_experiences`. Do not promote a one-off observation to shared memory, and do not silently overwrite a conflicting principle. A change to the principle, applicability, or treatment of counterexamples is a material rewrite: prepare its diff and supporting evidence, then require explicit approval unless that exact rewrite was already approved. Preserve an unresolved conflict and continue other independent work. Factual corrections that retain the principle can proceed within an authorized update.

Choose confidence from the evidence supporting the reusable principle:

| Confidence | Use when |
|---|---|
| `high` | Repeated or independent direct evidence supports the principle across its stated scope, and no important unresolved counterexample remains. |
| `medium` | More than one supporting observation exists, but coverage, independence, or applicability is limited. |
| `low` | Support is preliminary, includes a user-approved single source, or has important unresolved conflict or uncertainty. |

Omit confidence only when it has not yet been assessed.

When assigning tags, read [knowledge-tags.md](../knowledge-tags.md).
