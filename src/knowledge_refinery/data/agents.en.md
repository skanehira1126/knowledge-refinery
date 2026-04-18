## Refinery Rules

This repository uses refinery to manage working notes.

- Start each session with `knowledge-refinery skills init-session --task "..."`.
- Record evidence in `raw/`, tentative knowledge in `flow/`, and current status in `state.md`.
- Keep only stable knowledge in `shared/stock`.
- Store review snapshots copied from `flow` in `shared/review`.
- Store removed review candidates in `shared/review/rejected`.
- For any session that updates `flow`, prepare or refresh the review snapshot before ending the task, then check the review queue with `knowledge-refinery skills search review` or an equivalent command, and if there are promotion candidates, use `refinery-shared` to decide whether to promote or reject them.
- Knowledge files should generally be Markdown (`.md`) with YAML front matter at the top for searchability.
- Put directory-specific operating rules in each directory's `AGENTS.md`.
- You may update shared content autonomously when the change satisfies the shared-layer rules.
- Prefer `knowledge-refinery skills update-session` when updating `sessions/*/meta.yaml`, and preserve YAML types if manual editing is unavoidable.

### Knowledge File Format

- Use `.md` for knowledge files under `raw/`, `flow/`, `shared/review/`, and `shared/stock`.
- Keep one topic per file.
- `flow` files must include at least `title`, `description`, and `summary`.
- `review` and `stock` files must include at least `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, and `derived_from`.
- You may add fields such as `tags` and `confidence` as YAML when useful.
- For `tags`, prefer a prefix-based taxonomy such as `domain/...`, `artifact/...`, `task/...`, `tech/...`, and `issue/...` so search terms stay consistent.
- In `flow` and `stock`, prefer adding 2-4 tags and include at least one `domain/...` or `artifact/...` tag. In `raw`, tags remain optional.
- Keep front matter valid YAML. Do not break arrays or booleans by stringifying them.
- Treat both `flow -> review` and `review -> stock` as copy operations, and keep lineage traceable through `derived_from`.

```yaml
---
title: API Rate Limit Notes
description: Notes about observed 429 response conditions
summary: Summary of observed 429 response conditions
knowledge_id: api-rate-limit-notes
source_sessions:
  - 20260411T041820Z-l5al2u
derived_from:
  - .refinery/sessions/20260411T041820Z-l5al2u/flow/api-rate-limit-notes.md
tags:
  - domain/api
  - issue/rate-limit
  - task/investigation
confidence: medium
---
```

### Skills To Use

- Use `refinery-session` for session start, deciding when to capture or curate knowledge, and preparing review snapshots.
- Use `refinery-capture` when recording lightweight evidence into `raw/` during active work.
- Use `refinery-curation` when reorganizing `raw/` evidence into provisional `flow/` knowledge at task milestones.
- Before ending a session that updated `flow`, check the review queue and use `refinery-shared` to decide whether promotion candidates should be promoted or rejected.
- Use `refinery-repair` when broken front matter or `meta.yaml` prevents the CLI from reading refinery files.
- After updating the package, refresh distributed skills and shared template files with `knowledge-refinery update-template --target .`, then refresh the managed guide block with `knowledge-refinery update-agents-md --target . --lang jp|en`. Existing `shared/state.md` is preserved during `update-template`.

### meta.yaml Update Rules

- Keep `sessions/*/meta.yaml` valid YAML.
- Preserve existing keys and avoid unintended deletions or type changes.
- Keep `null`, `[]`, and scalar types intact.
- After updates, validate with search CLI commands such as `knowledge-refinery skills search sessions` and `knowledge-refinery skills search knowledge`.

### meta.yaml Format

- Treat `meta.yaml` as the single session metadata format.
- Do not mix it with JSON metadata files.
