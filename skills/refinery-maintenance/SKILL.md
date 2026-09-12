---
name: refinery-maintenance
description: Knowledge Refinery vaultの定期棚卸し、品質監査、指定したナレッジ・metadata・taxonomyの修復に使う。通常の開発レビューや単発の保存確認、repo設定診断は対象外。
---

# Refinery maintenance

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Input is the requested vault, project set, or records and
any reported defects. An audit-only or proposal-only request returns findings and repair candidates;
a repair request also authorizes supported factual fixes that preserve conclusions.

## Choose the review scope

- **Vault audit or periodic reconciliation:** start with `refinery_validate` and review project
  metadata, evidence, knowledge quality, and taxonomy across the requested scope.
- **Targeted review or repair:** inspect the specified records and the sources needed to assess
  them. Choose only the relevant checks below. A factual metadata or tag-description correction
  does not require a survey of unrelated projects, memories, or tags.
- **Schema or provenance defects:** use `refinery_validate` to establish the errors. This tool always
  scans the active vault; it has no project or record filter. Report unrelated errors separately
  without treating them as permission for additional repairs.

Vault-wide administrative validation and project listing can run independently of a repository.
Repo-scoped knowledge or tag access requires the shared access check; never switch repositories
to bypass an opt-out.

## Check the affected knowledge

- For project metadata, inspect current values and propose partial factual updates. Keep
  purpose/domain tags lowercase kebab-case, technology names in `technologies`, and local paths
  or unsupported guesses out of metadata. Preserve the project ID.
- For knowledge quality, search current project memory together with shared memory, then current
  project experiences. Choose cross-project IDs with `refinery_list_projects` and pass `project_ids`;
  use `all_projects: true` only for a necessary vault-wide review, never together with `project_ids`.
  Inspect relevant low-confidence records, duplicates, conflicts, stale principles, and source
  experiences. A moved or missing evidence reference is a limitation, not grounds to delete a conclusion.
- For taxonomy, read [knowledge-tags.md](../knowledge-tags.md) and inspect the affected branches.

## Repair and finish

Apply authorized factual metadata or taxonomy fixes with the current revision and read them back.
Use `refinery-experience` for experience content updates and `refinery-memory` for memory creation
or revision; those skills own record format, evidence, conflict handling, and promotion requirements.
A general maintenance request does not approve a specific shared principle, deletion, or material rewrite.

After schema or provenance repair, or writes made during a vault audit, run `refinery_validate`
once for the batch. A targeted factual update normally finishes after readback; validate more broadly
only if a concrete integrity concern remains. For a read-only audit, the initial validation is
sufficient unless the state changed or an unresolved concern requires another check.

Review the affected central-vault Git diff, including new files, after writes. Without vault Git,
review the changed files and report that limitation. Report unresolved paths and reasons; unrelated
pre-existing errors do not block completion of an otherwise verified targeted repair. Make no
product-repository changes as part of vault maintenance.
