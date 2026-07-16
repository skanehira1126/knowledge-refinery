# YAML schema

## vault marker

```yaml
schema_version: 2
managed_by: knowledge-refinery
cli_version: 0.2.0
```

`schema_version` または `managed_by` が未対応の場合、CLIとMCPはvaultへの接続と書き込みを拒否します。

## repo設定

```yaml
schema_version: 2
project_id: my-project
enabled: true
```

## experience

```yaml
schema_version: 2
experience_id: boruta-trial
project_id: my-project
title: Boruta検証
purpose: 特徴量を選択する
status: completed
recorded_at: 2026-07-14T00:00:00+00:00
updated_at: 2026-07-14T00:10:00+00:00
tags: [domain/ml]
evidence:
  - type: file
    path: notebooks/boruta.ipynb
    git_state: untracked
    retention: reference
related_experiences: []
supersedes: []
confidence: medium
```

`status` は `completed`、`inconclusive`、`abandoned`、`superseded`です。evidence typeは `file`、`git`、`mlflow`、`url`、`external` です。

## project memory

```yaml
schema_version: 2
memory_id: feature-selection
scope: project
project_id: my-project
title: 特徴量選択の原則
summary: 相関グループも確認する
source_experiences: [boruta-trial]
updated_at: 2026-07-14T00:20:00+00:00
tags: [domain/ml]
confidence: medium
```

## shared memory

```yaml
schema_version: 2
memory_id: validate-feature-groups
scope: shared
project_id: null
title: 特徴量グループを検証する
summary: 個別特徴量だけでなく相関グループを比較する
source_experiences:
  - project-a/boruta-trial
  - project-b/permutation-trial
updated_at: 2026-07-14T00:30:00+00:00
tags: [domain/ml]
confidence: high
```

shared sourceは必ずqualified IDで2件以上、distinct projectが2つ以上で、参照experienceが実在する必要があります。
