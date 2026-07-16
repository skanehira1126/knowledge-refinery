---
name: refinery-maintenance
description: Validate and reconcile the central Knowledge Refinery vault by checking schemas, evidence references, recent experiences, duplicate or stale memory, and cross-project promotion candidates. Use for scheduled maintenance, daily review, explicit vault audits, or knowledge quality checks.
---

# Refinery maintenance

1. Run `refinery_validate` and report every malformed document by path and reason.
2. When using repo-scoped search tools, require an enabled repository and pass its absolute path as `project_path`. Search recent experiences across projects and inspect records with low confidence, missing context, or likely duplicates.
3. Check evidence references when practical. Mark missing evidence as a limitation; do not delete the conclusion solely because evidence moved.
4. Search project and shared memory for duplicates, conflicts, stale principles, and cross-project candidates.
5. Propose changes with their supporting experience IDs. Record a new or updated memory only when provenance and scope are clear.
6. Run `refinery_validate` again after writes and review the central-vault Git diff.

Do not delete experiences or materially rewrite memory without user confirmation. Do not make product-repository changes during vault maintenance, and never combine product and vault changes in one commit or pull request.
