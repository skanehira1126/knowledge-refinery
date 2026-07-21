---
name: refinery-maintenance
description: schema、evidence参照、最近のexperience、重複・陳腐化したmemory、project横断の昇格候補を確認し、中央Knowledge Refinery vaultを検証・整合する。定期保守、日次レビュー、明示的なvault監査、ナレッジ品質確認に使用する。
---

# Refinery maintenance

1. Run `refinery_validate` and report every malformed taxonomy, project metadata, or knowledge document by path and reason.
2. Review `refinery_list_projects` for stale names, summaries, discovery tags, or technologies. Propose factual partial updates with the current revision. Keep purpose/domain tags in lowercase kebab-case, keep technology names only in `technologies`, and never add secrets, local absolute paths, or unsupported guesses.
3. When using repo-scoped search tools, require an enabled repository and pass its absolute path as `project_path`. Search current project memory together with shared memory first, then current project experiences. Use selected `project_ids` for a bounded cross-project review, or `all_projects: true` only when a vault-wide review is actually required; never combine them. Inspect records with low confidence, missing context, or likely duplicates.
4. Check evidence references when practical. Mark missing evidence as a limitation; do not delete the conclusion solely because evidence moved.
5. Search project and shared memory for duplicates, conflicts, stale principles, and cross-project candidates.
   Normal memory search returns active records only; also search `superseded` and `retracted` explicitly when auditing lifecycle consistency. A superseded memory must point to an active same-scope successor.
6. Browse the Knowledge tag hierarchy and identify used tags without descriptions, ambiguous descriptions, and parallel branches with the same meaning. Update a description only from the current `taxonomy_updated_at`; do not rename or delete used tags implicitly.
7. Propose changes with their supporting experience IDs. Normally require at least two repeated or complementary sources for project memory. Allow one source only after an explicit user request, with narrow scope, stated limits, and confidence below high. Always present a shared-memory candidate and obtain explicit user approval before creating or promoting it.
8. Run `refinery_validate` again after writes and review the central-vault Git diff.

Do not delete experiences or materially rewrite memory without user confirmation. Do not make product-repository changes during vault maintenance, and never combine product and vault changes in one commit or pull request.

For an explicitly requested deletion, read the exact document and call its delete tool with `confirm: false`. Present every structured reference and validation error. Call it again with the same `expected_updated_at` and `confirm: true` only after explicit user confirmation and only when `can_delete` is true. Never force deletion past a blocker.

Do not place secrets, credentials, access tokens, personal data, customer data, or unredacted sensitive logs in the vault. Report the affected path without reproducing the sensitive value, and redact before any safe rewrite.
