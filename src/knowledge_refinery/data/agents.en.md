## Refinery Rules

This repository uses refinery to manage working notes.

- Start each session with `knowledge-refinery init-session --task "..."`.
- Record evidence in `raw/`, tentative knowledge in `flow/`, and current status in `state.md`.
- Keep only stable knowledge in `shared/stock`.
- Store review snapshots copied from `flow` in `shared/review`.
- Store removed review candidates in `shared/review/rejected`.
- Knowledge files should generally be Markdown (`.md`) with YAML front matter at the top for searchability.
- Put directory-specific operating rules in each directory's `AGENTS.md`.
- Update shared content only when the user explicitly asks for it.
- Use `PyYAML` when reading or updating `sessions/*/meta.yaml`.

### Knowledge File Format

- Use `.md` for knowledge files under `raw/`, `flow/`, `shared/review/`, and `shared/stock`.
- Keep one topic per file.
- `flow` files must include at least `title`, `description`, and `summary`.
- `review` and `stock` files must include at least `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, and `derived_from`.
- You may add fields such as `tags` and `confidence` as YAML when useful.
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
  - api
  - rate-limit
confidence: medium
---
```

### Required Files

- `.codex/skills/refinery-session/SKILL.md` or `.agent/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-shared/SKILL.md` or `.agent/skills/refinery-shared/SKILL.md`
- `.refinery/shared/review/AGENTS.md`
- `.refinery/shared/review/rejected/AGENTS.md`
- `.refinery/shared/stock/AGENTS.md`

After updating the package, refresh distributed skills and shared template files with `knowledge-refinery update-template --target .`, then refresh the managed guide block with `knowledge-refinery update-agents-md --target . --lang jp|en`. Existing `shared/state.md` is preserved during `update-template`.

### meta.yaml Update Rules

- Keep `sessions/*/meta.yaml` valid YAML.
- Preserve existing keys and avoid unintended deletions or type changes.
- Keep `null`, `[]`, and scalar types intact.
- After updates, validate with YAML-reading CLI commands such as `knowledge-refinery list-sessions` and `knowledge-refinery list-headers`.

### meta.yaml Format

- Treat `meta.yaml` as the single session metadata format.
- Do not mix it with JSON metadata files.
