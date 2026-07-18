---
name: refinery-experience
description: 過去のナレッジを検索し、意味のある開発上の試行を、目的、根拠、発見、限界、次の可能性を含む一つのexperienceとして記録する。実験、比較、デバッグ、不採用案、結論が出なかった作業、有用な失敗の後に使用し、evidenceが未追跡でも対象にする。
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
