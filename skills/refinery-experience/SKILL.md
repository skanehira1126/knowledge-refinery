---
name: refinery-experience
description: Search prior knowledge and record a meaningful development attempt as one integrated experience with purpose, evidence, findings, limitations, and future possibilities. Use after experiments, comparisons, debugging, rejected approaches, inconclusive work, or useful failures, including when evidence is untracked.
---

# Refinery experience

1. Resolve the current repository to an absolute `PROJECT_ROOT`, then run `knowledge-refinery project status --target "$PROJECT_ROOT" --json`. Never pass a literal placeholder path. Stop without calling refinery tools unless `ready` and `enabled` are true.
2. Pass the repository's absolute path as `project_path` to every repo-scoped MCP tool. Search relevant project memory, shared memory, and experiences before acting. Start narrow; use cross-project search only when the decision can generalize.
3. After a meaningful attempt or before closing the task, decide whether the result can change a future decision. Skip routine task logs.
4. Record one integrated document with `refinery_record_experience`. Do not split the attempt and its evaluation into separate records. Creating a new experience omits `expected_updated_at`. Updating an existing experience requires the exact `updated_at` returned by `refinery_get_experience` or the prior record response; if it is stale, read and reconcile before retrying.
5. Search the returned ID or read it back to confirm the saved record.

Use this body shape:

```markdown
## 試したこと

## 分かったこと

## 微妙だった点・限界

## 次の可能性
```

Keep observations, interpretations, limitations, and hypotheses distinguishable. Choose `completed`, `inconclusive`, `abandoned`, or `superseded` honestly; an unsuccessful result can still have high future value.

Pass evidence as structured mappings:

- Local or untracked file: `type: file`, `path`, `retention: reference`, and optional `git_state`.
- Committed source: `type: git`, `commit`, `path`, `retention: source`.
- Remote evidence: `type: mlflow`, `url`, or `external`, with `uri` and `retention: external`.

Link related or superseded experience IDs when known. Do not commit product files merely to preserve an experience, and do not invent evidence that was not inspected.

Use knowledge tags with one to three lowercase slug segments separated by `/`, such as `domain/ml/feature-selection`. Prefer existing project tag branches when known; a parent tag search also matches its descendants.
