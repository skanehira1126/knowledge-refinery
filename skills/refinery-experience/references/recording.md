# Record an experience

1. Before creating an experience, choose a stable, descriptive lowercase slug for `experience_id`. Record one integrated document with `refinery_record_experience`; do not split the attempt and its evaluation into separate records. Creating a new experience omits `expected_updated_at`. Updating an existing experience requires the exact `updated_at` returned by `refinery_get_experience` or the prior record response. On update, omitted optional fields are preserved, an explicit empty list clears a list field, and `clear_confidence: true` explicitly clears confidence. If the revision is stale, read and reconcile before retrying.
2. Search the returned ID or read it back to confirm the saved record.

If a create call has an ambiguous outcome, do not blindly retry it. First use exact get with the chosen `experience_id`, then search that ID if needed. Retry creation only after confirming that the record does not exist.

Use this body shape:

```markdown
## 試したこと

## 分かったこと

## 微妙だった点・限界

## 次の可能性
```

When a prior memory influenced a choice, identify its scope, project ID when applicable, memory ID, and the principle you read. Include the observed `updated_at` if a revision changes how the decision should be understood. Under 「試したこと」, say why you applied the principle or set it aside and what you did. Under 「分かったこと」, give the observed outcome and evidence, including any counterexample or uncertainty. A candidate first found in hindsight belongs to the review of the result. A search hit alone establishes only that it was returned. Include this detail in an experience that already warrants recording.

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

Link related or superseded experience IDs when known, and do not invent evidence that was not inspected.

When assigning tags, read [knowledge-tags.md](../../knowledge-tags.md).
