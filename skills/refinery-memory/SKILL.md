---
name: refinery-memory
description: 検証済みのKnowledge Refinery experienceから繰り返し役立つ原則を抽出し、根拠を明示したprojectまたはshared memoryとして記録する。複数のexperienceが再利用可能な原則を支持するとき、既存memoryを改善するとき、ナレッジがproject固有かproject横断か判断するときに使用する。
---

# Refinery memory

1. Resolve the current repository to an absolute `PROJECT_ROOT`, then run `knowledge-refinery project status --target "$PROJECT_ROOT" --json`. Never pass a literal placeholder path. Stop unless `ready` and `enabled` are true.
2. Pass the repository's absolute path as `project_path` to every repo-scoped MCP tool. Search in this order: current project memory together with shared memory, current project experiences, then cross-project knowledge only when local evidence is insufficient. For a bounded cross-project search, choose IDs with `refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded set is defensible. Never combine `project_ids` with `all_projects: true`. Update a matching principle instead of duplicating it.
3. Read every supporting experience with `refinery_get_experience`. For cross-project evidence, pass the qualified `project-id/experience-id` source and check its evidence, applicability conditions, counterexamples, and confidence.
4. Keep project-specific principles in project memory. Normally require at least two experiences that show repetition or complementary validation, and use unqualified experience IDs. A single source is allowed only when the user explicitly asks to preserve it as memory; narrow the scope, state the unverified limits in the body, and do not assign high confidence.
5. Treat shared memory as a user-approved promotion. Independent experiences from at least two projects must support the same principle and every source must use `project-id/experience-id`, but satisfying that schema is not approval. Present the candidate principle, scope, limits, counterexamples, confidence, and source IDs, and call `refinery_record_memory(shared: true)` only after explicit user approval.
6. Record with `refinery_record_memory`, include every supporting experience ID, and read the result back with `refinery_get_memory`. Use the returned `scope`: for project memory pass its returned `project_id`; for shared memory use `scope: shared` and omit `project_id`. When updating shared memory, keep `shared: true`.
7. Normal search returns active memory only. When a saved principle is replaced, create or update the active successor first, then update the old record with `status: superseded` and its same-scope `superseded_by`. Use `status: retracted` only when the principle must no longer be used and there is no successor. Search explicit statuses when auditing inactive memory.

Creating a new memory omits `expected_updated_at`. Updating an existing memory requires the exact `updated_at` returned by `refinery_get_memory`; pass it as `expected_updated_at`. On update, omitted optional fields are preserved, an explicit empty list clears a list field, and `clear_confidence: true` explicitly clears confidence. If the server reports a stale revision, read the current memory again and reconcile the competing change instead of retrying blindly.

Write the reusable principle in `summary`. Put conditions, limits, counterexamples, and operational guidance in the body. Keep detailed attempt history in the source experiences.

Never create memory without `source_experiences`. Do not promote a one-off observation to shared memory, and do not silently overwrite a conflicting principle; preserve the conflict or ask for a decision.

Do not physically delete memory as routine cleanup. When deletion is explicitly requested, exact-get the target, call `refinery_delete_memory` without `confirm`, present its revision, references, and validation errors, and obtain explicit user confirmation. Retry with the same `expected_updated_at` and `confirm: true` only when `can_delete` is true. If the target is blocked, retire or update its references instead of forcing deletion.

Choose confidence from the evidence supporting the reusable principle:

| Confidence | Use when |
|---|---|
| `high` | Repeated or independent direct evidence supports the principle across its stated scope, and no important unresolved counterexample remains. |
| `medium` | More than one supporting observation exists, but coverage, independence, or applicability is limited. |
| `low` | Support is preliminary, includes a user-approved single source, or has important unresolved conflict or uncertainty. |

Omit confidence only when it has not yet been assessed. Never store secrets, credentials, access tokens, PII or other personal data, or customer data in memory or copied evidence. Redact sensitive log content; if it cannot be made safe, record only a non-sensitive limitation.

Before assigning tags, call `refinery_browse_knowledge_tags` without `parent_tag`, then follow relevant children one level at a time. Use `refinery_search_knowledge_tags` when a concept is easier to identify from words than from the hierarchy. Reuse the narrowest existing tag whose description fits; do not invent a parallel spelling when an existing branch applies. Choose the root deterministically: subject/domain → `domain`, output artifact → `artifact`, work type → `task`, technology → `tech`, symptom or quality issue → `issue`. Never invent another root. Use one to three lowercase slug segments separated by `/`, such as `domain/ml/feature-selection`; a parent tag search also matches its descendants.
