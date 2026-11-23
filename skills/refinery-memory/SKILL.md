---
name: refinery-memory
description: Knowledge Refineryのexperienceから再利用できる原則を抽出し、project・shared memoryを作成・改訂・統合・アーカイブするときや、その提案に使う。検索だけ、または単一試行の記録はrefinery-experienceを使う。
---

# Refinery memory

Read the [shared operating rules](../operating-rules.md). During ordinary work under the project's
operating instructions, act when newly inspected experiences support a reusable decision or change
the evidence for an existing principle. Create supported project memories and maintain existing
project and shared memories in the same task, through saving and readback.
For a proposal-only request, return the candidate, source IDs, scope and limits.

## Decide what the evidence changes

1. Apply the shared operating rules' access check. Continue a verified vault-maintenance context without requiring a product repository.
2. In a repository, pass its absolute path as `project_path` and search current project memory together with shared memory, current project experiences, then cross-project knowledge only when local evidence is insufficient. In direct vault maintenance, use the requested project set or shared scope and retain `project_path: null` plus `vault_context`. For a bounded cross-project search, choose IDs with `refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded set is defensible. Never combine `project_ids` with `all_projects: true`.
3. Read the matching memories and each supporting experience. Use `refinery_get_experience` with qualified `project-id/experience-id` for cross-project sources. Check what was tried, what happened, which conditions still apply, and any counterexamples.

- Create a memory for a distinct reusable decision. When new experiences change the decision, its applicability or its counterexamples, revise the same ID and record the evidence. Keep the conditions still supported. Leave the record untouched when neither the decision nor the evidence has changed.
- Archive when a verified successor covers the full scope or the premise has disappeared. Record an unresolved counterexample alongside the conditions that still hold. Age, low confidence and search frequency alone do not establish retirement.

## Create or revise a principle

- Project memory normally requires at least two experiences showing repetition or complementary validation. Use unqualified experience IDs. A single source requires an explicit request to preserve it as memory, narrow scope, stated unverified limits and confidence below high.
- Shared memory requires independent experiences from at least two projects. For creation or promotion, present the principle, scope, limits, counterexamples, confidence and qualified source IDs and obtain explicit approval. Revise an existing shared memory on its own ID as the evidence changes.

Record the decision and its decisive condition in `summary`, and its limits and counterexamples in the body. Call `refinery_record_memory` with every supporting experience in `source_experiences`. Use `shared: true` for shared writes. Read back the saved ID with `refinery_get_memory`, passing its returned scope and, for project memory, its project ID.

Omit `expected_updated_at` on creation. For updates, use the exact revision returned by get. Omitted optional fields retain their values, an empty list clears a list, and `clear_confidence: true` clears confidence. On a stale revision, read the current record and reconcile the change.

Choose confidence from the evidence supporting the reusable principle:

| Confidence | Use when |
|---|---|
| `high` | Repeated or independent direct evidence supports the principle across its stated scope, and no important unresolved counterexample remains. |
| `medium` | More than one supporting observation exists, but coverage, independence, or applicability is limited. |
| `low` | Support is preliminary, includes a user-approved single source, or has important unresolved conflict or uncertainty. |

Omit confidence only when it has not yet been assessed.

When assigning tags, read [knowledge-tags.md](../knowledge-tags.md).

## Archive a principle

For a replacement, save or verify the active successor first, carrying forward the sources and exceptions that still apply. Call `refinery_archive_memory` on the old ID with its exact `expected_updated_at` and a `reason` that identifies the evidence for retirement. Use `shared: true` for a shared record. Supply `superseded_by` only for a replacement. Use the ID for the same scope and project, `shared/ID` for shared memory, or `project/PROJECT/ID` for a named project. Read back the old ID to confirm its status, reason and successor. If the revision is stale or the write outcome is uncertain, inspect the old ID before acting again.
