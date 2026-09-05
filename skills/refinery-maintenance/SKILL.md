---
name: refinery-maintenance
description: 中央Knowledge Refinery vaultのschema・evidence参照・metadata・重複や陳腐化したmemoryを点検・整合する。定期保守、日次棚卸し、明示的なvault監査やナレッジ品質確認に使用する。通常の開発レビュー、単発の検索・記録後の確認、repositoryの設定診断は対象外。
---

# Refinery maintenance

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Use the requested vault, project set, or record set to bound
the review. An audit-only or proposal-only request returns findings and repair candidates; a repair request
also authorizes supported factual fixes that preserve conclusions. Do not expand a narrow repair
into unrelated cleanup. Repo-scoped steps require a ready, enabled repository; do not switch to
another repository to bypass an opt-out. Vault-wide administrative checks can run independently.

1. Run `refinery_validate` and report every malformed taxonomy, project metadata, or knowledge document by path and reason.
2. Review `refinery_list_projects` for stale names, summaries, discovery tags, or technologies. Propose factual partial updates with the current revision. Keep purpose/domain tags in lowercase kebab-case, keep technology names only in `technologies`, and never add secrets, local absolute paths, or unsupported guesses.
3. When using repo-scoped search tools, require an enabled repository and pass its absolute path as `project_path`. Search current project memory together with shared memory first, then current project experiences. Use selected `project_ids` for a bounded cross-project review, or `all_projects: true` only when a vault-wide review is actually required; never combine them. Inspect records with low confidence, missing context, or likely duplicates.
4. Check evidence references when practical. Mark missing evidence as a limitation; do not delete the conclusion solely because evidence moved.
5. Search project and shared memory for duplicates, conflicts, stale principles, and cross-project candidates.
6. Browse the Knowledge tag hierarchy and identify used tags without descriptions, ambiguous descriptions, and parallel branches with the same meaning. Update a description only from the current `taxonomy_updated_at`; do not rename or delete used tags implicitly.
7. Prepare changes with their supporting experience IDs. Apply authorized factual metadata or taxonomy fixes using the current revision; use `refinery-memory` for memory creation or revision. Normally require at least two repeated or complementary sources for project memory. Allow one source only after an explicit user request, with narrow scope, stated limits, and confidence below high. Present a shared-memory candidate and obtain explicit user approval before creating or promoting it; reuse approval already given for that unchanged candidate.
8. After the batch of writes, run `refinery_validate` again and review the central-vault Git diff, including newly created files. If the vault has no Git repository, review the changed files and report that limitation. For a read-only review, the initial validation is sufficient unless the inspected state changes or a concrete concern remains. Finish when the requested review and required checks are complete; report unresolved paths and reasons.

Do not delete experiences or materially rewrite memory without user confirmation. Do not make product-repository changes during vault maintenance, and never combine product and vault changes in one commit or pull request.

Do not place secrets, credentials, access tokens, personal data, customer data, or unredacted sensitive logs in the vault. Report the affected path without reproducing the sensitive value, and redact before any safe rewrite.
