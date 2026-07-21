# YAML schema

## vault marker

```yaml
schema_version: 2
managed_by: knowledge-refinery
cli_version: 0.2.0
vault_id: 0123456789abcdef0123456789abcdef
```

`schema_version`または`managed_by`が未対応の場合、CLIとMCPはvaultへの接続と書き込みを拒否します。
`vault_id`はvault作成時に生成する不変の32桁hex IDです。

## repo設定

```yaml
schema_version: 2
project_id: my-project
enabled: true
```

`.refinery.yaml`はversion管理でき、clone間でproject IDを共有します。vault固有のbindingは
version管理しない`.refinery.local.yaml`へ分離します。setupはこのfileを`.gitignore`へ追加します。

```yaml
schema_version: 1
vault_id: 0123456789abcdef0123456789abcdef
```

local側の`vault_id`は、同じ`project_id`を持つ別vaultへの誤接続を防ぎます。status/doctor/MCPは
active vaultとの一致を検証します。旧versionまたは新しいcloneでlocal bindingがない場合は、
[移行・binding手順](troubleshooting.md#legacy-vault-id)で明示的にbindします。

## project metadata

中央vaultの `projects/<project_id>/project.yaml` に保存します。

```yaml
schema_version: 1
project_id: my-project
name: My Project
summary: 顧客向けAPIを提供する
tags: [backend, customer-facing]
technologies: [Python, FastAPI]
created_at: 2026-07-17T00:00:00+00:00
updated_at: 2026-07-17T00:10:00+00:00
```

`project_id` はdirectory名と一致し、`name` は空にできません。`tags` は重複のない
lowercase kebab-caseにし、projectの目的や領域を表す値だけを入れます。技術名はtagへ重複させず
`technologies` に標準的な表記で保存し、大文字・小文字だけが異なる重複も禁止します。
更新時は現在の `updated_at` を使い、省略fieldは保持、空listを明示したfieldだけをclearします。

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

`status` は次の意味で使います。

| 値 | 意味 |
|---|---|
| `completed` | 成否を問わず、試行が評価可能な結果へ到達した |
| `inconclusive` | 試行したが、根拠不足、矛盾、測定不能により問いへ答えられない |
| `abandoned` | blocker、cost、risk、前提崩壊により評価可能な結果の前に停止した |
| `superseded` | 保存済みの後続experienceがこの結論を置き換えた |

本文は「試したこと」「分かったこと」「微妙だった点・限界」「次の可能性」の4 headingを使い、
事実、解釈、限界、仮説を区別します。evidence typeは `file`、`git`、`mlflow`、`url`、`external`です。
Evidenceは参照だけを保存し、file内容を自動copyしません。`file`は`reference`、`git`は
`source`、`mlflow`・`url`・`external`は`external` retentionだけを受け付けます。
`file`と`git`のpathはrepository相対で`..`を含めません。fileの任意`git_state`は`tracked`、
`untracked`、`modified`、`staged`、`ignored`、`deleted`のいずれかです。typeごとに定義されて
いない追加fieldは拒否します。
`related_experiences`と`supersedes`は同じprojectの実在IDだけを参照し、自己参照、重複、
両listの重なりを拒否します。
secret、credential、access token、PII（個人情報）、顧客data、未redactの機密logはevidenceや本文へ保存しません。

## project memory

```yaml
schema_version: 2
memory_id: feature-selection
scope: project
project_id: my-project
title: 特徴量選択の原則
summary: 相関グループも確認する
status: active
superseded_by: null
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
status: active
superseded_by: null
source_experiences:
  - project-a/boruta-trial
  - project-b/permutation-trial
updated_at: 2026-07-14T00:30:00+00:00
tags: [domain/ml]
confidence: high
```

shared sourceは必ずqualified IDで2件以上、distinct projectが2つ以上で、参照experienceが実在する必要があります。

Project memoryはschema上1件以上のsourceを受け付けますが、通常運用では反復または相補的な
2件以上を要求します。1件だけのmemoryは利用者の明示依頼がある場合に限り、scopeと未検証の限界を
本文へ書き、`confidence: high`を使用しません。Shared memoryはschema条件を満たしても自動作成せず、
候補内容と根拠を提示して利用者の明示承認を得ます。

Memoryの`status`は`active`、`superseded`、`retracted`のいずれかです。旧文書で`status`が
省略されている場合は`active`として読みます。`superseded`では同じscopeに実在するactive memoryを
`superseded_by`へ指定します。`active`と`retracted`では`superseded_by`をnullにします。
通常検索はactive memoryだけを返し、廃止済みを調査するときだけstatusを明示します。

## confidence

`confidence`は省略可能で、省略時は未評価です。statusや試行の成否とは独立して選びます。

| 値 | Experience | Memory |
|---|---|---|
| `high` | 条件を明記した直接根拠が再現可能で、重要な未解決矛盾がない | stated scopeで反復または独立した直接根拠があり、重要な未解決反例がない |
| `medium` | 直接根拠はあるが、反復、coverage、適用範囲が限定的 | 複数の支持はあるが、coverage、独立性、適用範囲が限定的 |
| `low` | 部分的・間接的・再確認不能な根拠、または重要な未解決点がある | 予備的な支持、明示承認された1 source、または重要な競合・不確実性がある |

## revision付き更新

Experienceとmemoryの更新では、現在の`updated_at`を`expected_updated_at`へ渡します。
保存文書の`updated_at`とexperienceの`recorded_at`は必須で、timezone付きISO 8601にします。
optional fieldを省略すると現在値を保持し、空listを明示したlist fieldだけをclearします。
confidenceのclearは`clear_confidence: true`で明示します。作成前にstable IDを決め、結果不明の
createをretryする前にexact getまたはID検索で保存済みか確認します。

## 安全な削除

Experienceとmemoryのdeleteは既定でdry-runです。対象の現在`updated_at`を
`expected_updated_at`へ渡し、`confirm: true`またはCLIの`--confirm`を明示した場合だけ削除します。
構造化参照が残る場合、またはvault内にvalidationできず参照有無を判定できないknowledge文書が
ある場合は削除しません。Experienceではmemoryの`source_experiences`と他experienceの
`related_experiences`・`supersedes`、memoryでは他memoryの`superseded_by`を検査します。

## Knowledge tag

Experienceとmemoryの`tags`は、`/`で区切った1〜3階層です。各segmentは
lowercaseの英数字かhyphenを使い、空segment、重複tag、4階層以上は拒否します。
先頭segmentは`domain`、`artifact`、`task`、`tech`、`issue`のいずれかに固定します。

```yaml
tags:
  - domain/ml/feature-selection
  - artifact/cli/search
```

Project metadataの`tags`はproject発見用の別fieldです。Knowledge tagの階層とは混合せず、
project metadataでは引き続きlowercase kebab-caseの単一segmentを使います。

## Knowledge tag taxonomy

tagの説明を追加すると、中央vault直下の`knowledge-tags.yaml`へ保存します。利用件数は
Experienceとmemoryから動的に集計するため、このファイルには保存しません。

```yaml
schema_version: 1
updated_at: 2026-07-18T00:00:00+00:00
tags:
  domain:
    description: 対象となる業務・知識領域
  domain/ml:
    description: 機械学習モデルと分析手法
```

tag keyにはKnowledge tagと同じ形式を使い、descriptionは空にできません。ファイルがない
vaultでも`domain`、`artifact`、`task`、`tech`、`issue`の標準説明を読み取り専用の既定値として
返します。最初の説明登録ではrevisionを省略し、ファイル作成後の更新ではbrowseまたはsearchが
返した`taxonomy_updated_at`を指定します。
