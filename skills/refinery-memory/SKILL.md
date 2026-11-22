---
name: refinery-memory
description: Knowledge Refineryのexperienceから再利用できる原則を抽出し、project・shared memoryを作成・改訂・統合・アーカイブするときや、その提案に使う。検索だけ、または単一試行の記録はrefinery-experienceを使う。
---

# Refinery memory

Read the [shared operating rules](../operating-rules.md) for authorization, blocked operations and completion. For a proposal, return the affected principles, evidence, scope and limits. Write only within the authorized request.

## Decide what the evidence changes

1. Apply the shared operating rules' access check. Continue a verified vault-maintenance context without requiring a product repository.
2. In a repository, pass its absolute path as `project_path` and search current project memory together with shared memory, current project experiences, then cross-project knowledge only when local evidence is insufficient. In direct vault maintenance, use the requested project set or shared scope and retain `project_path: null` plus `vault_context`. For a bounded cross-project search, choose IDs with `refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded set is defensible. Never combine `project_ids` with `all_projects: true`.
3. Read the matching memories and each supporting experience. Use `refinery_get_experience` with qualified `project-id/experience-id` for cross-project sources. Check what was tried, what happened, which conditions still apply, and any counterexamples.

- Create a memory for a distinct reusable decision. Revise the same ID when the principle gains evidence or still applies within narrower conditions. If the knowledge adds nothing to the existing decision or its evidence, leave it as it stands.
- Propose archiving when a successor covers the old principle's full scope, or when its premise has disappeared. If a counterexample remains unresolved, preserve the conflict and the conditions already supported. Age, low confidence and search frequency alone do not establish retirement.

For a material change to a principle, its applicability, the treatment of counterexamples, or its availability in ordinary search, present the affected IDs, diff, evidence and impact. Apply it with explicit approval of that concrete change, reusing approval already given. Factual corrections that retain the principle can proceed within an authorized update.

## Create or revise a principle

- Project memory normally requires at least two experiences showing repetition or complementary validation. Use unqualified experience IDs. A single source requires an explicit request to preserve it as memory, narrow scope, stated unverified limits and confidence below high.
- Shared memory requires independent experiences from at least two projects. Present the principle, scope, limits, counterexamples, confidence and qualified source IDs, and obtain explicit approval for the concrete creation or promotion. New material evidence or a scope change calls for reconsideration.

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

Once the change is approved, save or verify any active successor first, carrying forward the sources and exceptions that still apply. Call `refinery_archive_memory` on the old ID with its exact `expected_updated_at` and a `reason` that explains the decision. Use `shared: true` for a shared record. Supply `superseded_by` only for a replacement. Use the ID for the same scope and project, `shared/ID` for shared memory, or `project/PROJECT/ID` for a named project. Read back the old ID to confirm its status, reason and successor. If the revision is stale or the write outcome is uncertain, inspect the old ID before acting again.
