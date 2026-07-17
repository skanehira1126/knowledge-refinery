---
name: refinery-maintenance
description: Validate and reconcile the central Knowledge Refinery vault by checking schemas, evidence references, recent experiences, duplicate or stale memory, and cross-project promotion candidates. Use for scheduled maintenance, daily review, explicit vault audits, or knowledge quality checks.
---

# Refinery maintenance

1. Run `refinery_validate` and report every malformed project metadata or knowledge document by path and reason.
2. Review `refinery_list_projects` for stale names, summaries, discovery tags, or technologies. Propose factual partial updates with the current revision. Keep purpose/domain tags in lowercase kebab-case, keep technology names only in `technologies`, and never add secrets, local absolute paths, or unsupported guesses.
3. When using repo-scoped search tools, require an enabled repository and pass its absolute path as `project_path`. Search recent experiences across projects and inspect records with low confidence, missing context, or likely duplicates.
4. Check evidence references when practical. Mark missing evidence as a limitation; do not delete the conclusion solely because evidence moved.
5. Search project and shared memory for duplicates, conflicts, stale principles, and cross-project candidates.
6. Propose changes with their supporting experience IDs. Record a new or updated memory only when provenance and scope are clear.
7. Run `refinery_validate` again after writes and review the central-vault Git diff.

Do not delete experiences or materially rewrite memory without user confirmation. Do not make product-repository changes during vault maintenance, and never combine product and vault changes in one commit or pull request.
