---
name: refinery-experience
description: 過去のナレッジを検索し、意味のある開発上の試行を、目的、根拠、発見、限界、次の可能性を含む一つのexperienceとして記録する。実験、比較、デバッグ、不採用案、結論が出なかった作業、有用な失敗の後に使用し、evidenceが未追跡でも対象にする。
---

# Refinery experience

1. Resolve the current repository to an absolute `PROJECT_ROOT`, then run `knowledge-refinery project status --target "$PROJECT_ROOT" --json`. Never pass a literal placeholder path. Stop without calling refinery tools unless `ready` and `enabled` are true.
2. Pass the repository's absolute path as `project_path` to every repo-scoped MCP tool. Search in this order: current project memory together with shared memory, current project experiences, then cross-project knowledge only when the local result is insufficient. For a bounded cross-project search, first use `refinery_list_projects` to choose IDs and pass `project_ids`; use `all_projects: true` only when no bounded project set is defensible. Never combine `project_ids` with `all_projects: true`.
3. After a meaningful attempt or before closing the task, ask: "Would this result change how a future agent chooses, avoids, verifies, or diagnoses something?" Record a comparison, rejection, non-obvious failure, constraint, or reusable discovery when the answer is yes. Skip routine completion logs, progress summaries, obvious typo fixes, and repetitions that add no new evidence, condition, or counterexample.
4. Before creating an experience, choose a stable, descriptive lowercase slug for `experience_id`. Record one integrated document with `refinery_record_experience`; do not split the attempt and its evaluation into separate records. Creating a new experience omits `expected_updated_at`. Updating an existing experience requires the exact `updated_at` returned by `refinery_get_experience` or the prior record response. On update, omitted optional fields are preserved, an explicit empty list clears a list field, and `clear_confidence: true` explicitly clears confidence. If the revision is stale, read and reconcile before retrying.
5. Search the returned ID or read it back to confirm the saved record.

If a create call has an ambiguous outcome, do not blindly retry it. First use exact get with the chosen `experience_id`, then search that ID if needed. Retry creation only after confirming that the record does not exist.

Use this body shape:

```markdown
## 試したこと

## 分かったこと

## 微妙だった点・限界

## 次の可能性
```

Keep observations, interpretations, limitations, and hypotheses distinguishable. Choose status by this table; success and status are separate concepts.

| Status | Use when |
|---|---|
| `completed` | The planned attempt reached an evaluable result, including a definitive negative result. |
| `inconclusive` | The attempt ran, but evidence is insufficient, conflicting, or cannot answer the question. |
| `abandoned` | The attempt stopped before an evaluable result because of a blocker, cost, risk, or invalidated premise. State why it stopped. |
| `superseded` | A later saved experience replaces this record's conclusion. Link the successor/predecessor before marking the old record superseded. |

Choose confidence independently from status.

| Confidence | Use when |
|---|---|
| `high` | Direct evidence is reproducible under stated conditions and no important unresolved contradiction remains. |
| `medium` | Direct evidence exists, but repetition, coverage, or applicability is limited. |
| `low` | Evidence is partial, indirect, unavailable for re-checking, or has important unresolved uncertainty. |

Omit confidence only when it has not yet been assessed. A failed attempt may still be `completed` with high confidence when the negative result is reproducible.

Pass evidence as structured mappings:

- Local or untracked file: `type: file`, `path`, `retention: reference`, and optional `git_state`. When present, `git_state` must be one of `tracked`, `untracked`, `modified`, `staged`, `ignored`, or `deleted`.
- Committed source: `type: git`, `commit`, `path`, `retention: source`.
- Remote evidence: `type: mlflow`, `url`, or `external`, with `uri` and `retention: external`.

Link related or superseded experience IDs when known. Do not commit product files merely to preserve an experience, and do not invent evidence that was not inspected.

Never store secrets, credentials, access tokens, PII or other personal data, or customer data in a title, body, metadata, evidence, or copied log. Redact sensitive values before recording a safe excerpt or reference; if safe redaction is not possible, record only a non-sensitive description of the evidence and its limitation.

Before assigning tags, call `refinery_browse_knowledge_tags` without `parent_tag`, then follow relevant children one level at a time. Use `refinery_search_knowledge_tags` when a concept is easier to identify from words than from the hierarchy. Reuse the narrowest existing tag whose description fits; do not invent a parallel spelling when an existing branch applies. Choose the root deterministically: subject/domain → `domain`, output artifact → `artifact`, work type → `task`, technology → `tech`, symptom or quality issue → `issue`. Never invent another root. Use one to three lowercase slug segments separated by `/`, such as `domain/ml/feature-selection`; a parent tag search also matches its descendants.
