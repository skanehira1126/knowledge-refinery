# knowledge-refinery

複数リポジトリに導入するための **refinery テンプレート配布リポジトリ** です。
このリポジトリ自身では refinery を運用せず、`src/knowledge_refinery/template/` 配下の配布物を管理します。

今回のテンプレートは、利用時に必要な以下2点を最優先で揃える構成です。

1. `skills` の配置
2. `AGENTS.md` または `CLAUDE.md` への管理ブロック追記

## テンプレート構成

```text
src/
  knowledge_refinery/
    cli.py
    template/
      codex/
        skills/
          refinery-capture/
            SKILL.md
          refinery-curation/
            SKILL.md
          refinery-repair/
            SKILL.md
          refinery-session/
            SKILL.md
          refinery-shared/
            SKILL.md
      refinery/
        shared/
          review/
            AGENTS.md
            rejected/
              AGENTS.md
          state.md
          stock/
            AGENTS.md
```

## メタデータとヘッダ仕様

refinery では、構造化メタデータを以下の 3 系統で管理します。

1. YAML ファイルとしての `meta.yaml`
2. `state.md` の YAML front matter
3. 知識 Markdown (`raw/`, `flow/`, `shared/review/`, `shared/stock/`) の YAML front matter

CLI が読むメタデータは YAML として正しく保ってください。文字列置換で壊さず、session metadata は `knowledge-refinery skills update-session` などの CLI 経由で更新する前提です。

### `.refinery/template-meta.yaml`

テンプレート配布状態を表すメタデータです。現時点の canonical なキーは以下です。

| キー | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `cli_version` | string | 必須 | `apply-template` または `update-template` を実行した CLI バージョン。 |

例:

```yaml
cli_version: 0.1.0
```

### `.refinery/sessions/<session_id>/meta.yaml`

セッション単位の状態を管理する canonical な YAML です。`init-session` は初期状態として次のキーを生成します。

| キー | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `session_id` | string | 必須 | `YYYYMMDDTHHMMSSZ-xxxxxx` 形式の一意な session ID。 |
| `kind` | string | 必須 | session の種別。既定値は `task`。 |
| `title` | string | 必須 | session の短いタイトル。 |
| `task` | string | 必須 | 依頼内容や作業目的の要約。 |
| `created_at` | string | 必須 | UTC の ISO 8601 タイムスタンプ。 |
| `created_by` | string | 必須 | 作成者。現状は `user` または `llm`。 |
| `repository` | string \| null | 任意 | 対象リポジトリ名。未設定なら `null`。 |
| `domain` | string \| null | 任意 | ドメインやテーマ名。未設定なら `null`。 |
| `status` | string | 必須 | session の状態。初期値は `active`。 |
| `phase` | string | 必須 | 進行フェーズ。初期値は `capture`。 |
| `current_step` | string | 必須 | 現在やっていることの要約。 |
| `next_action` | string | 必須 | 次にやるべきことの要約。 |
| `last_updated_at` | string | 必須 | 最終更新時刻。UTC の ISO 8601。 |
| `closed_at` | string \| null | 任意 | session を閉じた時刻。 |
| `blocked_reason` | string \| null | 任意 | ブロック理由。 |
| `resume_condition` | string \| null | 任意 | 再開条件。 |
| `parent_session_id` | string \| null | 任意 | 親 session ID。 |
| `child_session_ids` | list[string] | 必須 | 子 session ID 群。 |
| `related_sessions` | list[string] | 必須 | 関連 session ID 群。 |
| `depends_on` | list[string] | 必須 | 依存先 session ID 群。 |
| `supersedes` | list[string] | 必須 | 置き換える session ID 群。 |
| `superseded_by` | string \| null | 任意 | 置き換え先 session ID。 |
| `evidence_status` | string | 必須 | raw 証拠収集の状態。初期値は `collecting`。 |
| `flow_status` | string | 必須 | flow 整理の状態。初期値は `not_started`。 |
| `synthesis_status` | string | 必須 | synthesis の状態。初期値は `not_started`。 |
| `coverage_status` | string | 必須 | カバレッジの状態。初期値は `unknown`。 |
| `confidence` | string | 必須 | session の確からしさ。初期値は `low`。 |
| `raw_item_count` | integer | 必須 | raw アイテム数。 |
| `flow_item_count` | integer | 必須 | flow アイテム数。 |
| `last_flow_update_at` | string \| null | 任意 | 最後に flow を更新した時刻。 |

運用ルール:

- `meta.yaml` はトップレベル mapping として保つ
- 既存キーは意味と型を維持する
- `null`, list, scalar を文字列化しない
- 更新後は `knowledge-refinery skills search sessions` で読み取り確認する

### `state.md`

`state.md` は本文と別に YAML front matter を持つ Markdown です。session 用と shared 用で本文の粒度は違いますが、header の基本形は共通です。

| キー | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `title` | string | 必須 | 状態ファイルのタイトル。 |
| `description` | string | 必須 | 何の現在地かを説明する短文。 |

session `state.md` の初期例:

```yaml
---
title: Session State (20260411T041820Z-l5al2u)
description: このセッションの現在地
---
```

shared `state.md` の初期例:

```yaml
---
title: Shared State
description: プロジェクト全体の現在地（要点のみ）
---
```

本文ルール:

- session `state.md` は少なくとも `目的`, `進捗`, `次アクション` を追える形にする
- shared `state.md` はプロジェクト全体の現在地だけを要点で保つ
- `state.md` は知識ファイルではなく現在地メモなので、`knowledge_id` や `source_sessions` は不要

### 知識 Markdown の YAML front matter

refinery で扱う知識ファイルは、`raw/`, `flow/`, `shared/review/`, `shared/stock/` を問わず、原則 Markdown (`.md`) で管理します。1 ファイル 1 トピックを基本とし、各ファイルの先頭に YAML front matter を付けます。

共通フィールド:

| キー | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `title` | string | 必須 | 知識のタイトル。 |
| `description` | string | 必須 | 何を記録しているかの短い説明。 |
| `summary` | string | `flow` 以降で必須 | 要点の要約。`raw` では任意。 |
| `knowledge_id` | string | `review` / `stock` で必須 | 知識の識別子。`^[a-z0-9][a-z0-9-]*$` に一致する lowercase slug。`flow` では省略時にファイル名から導出。 |
| `knowledge_type` | string | 任意 | 知識の性質。`reference` または `constructive`。`tags` とは別の検索・運用軸として使う。 |
| `source_sessions` | list[string] | `review` / `stock` で必須 | この知識の根拠になった session ID 群。`flow` では省略可能だが review 生成時に session ID が補完される。 |
| `derived_from` | list[string] | `review` / `stock` で必須 | 元ファイルへの repository-relative path 群。`flow -> review -> stock` の系譜を辿るために使う。 |
| `tags` | list[string] | 任意 | 検索・分類用タグ。非空文字列の list で記載する。`domain/...`, `artifact/...`, `task/...` など prefix 付きの taxonomy を推奨する。 |
| `confidence` | string | 任意 | 内容の確からしさ。CLI 上は非空文字列ならよい。 |

レイヤー別の最小要件:

| レイヤー | 最低限必要な header |
| --- | --- |
| `raw/` | `title`, `description` |
| `flow/` | `title`, `description`, `summary` |
| `shared/review/` | `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` |
| `shared/stock/` | `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` |

補足:

- `prepare-review` は `flow` から `review` を生成する際に `knowledge_id`, `source_sessions`, `derived_from` を正規化する
- `knowledge_type` を付けた知識は、review / stock のファイル名にも type を織り込み、`reference` と `constructive` の衝突を避ける
- `promote-review` は `review` から新規 `stock` へコピーする。既存 `stock` がある場合は、安定知識の本文を暗黙に置換しないためスキップする
- `tags` は string 1 個でも CLI では受理するが、canonical format は YAML list
- `source_sessions` と `derived_from` も canonical format は YAML list
- `review` / `stock` では `summary` を空にしない

### 検索シチュエーション別の対象

| シチュエーション | 主な検索対象 | 最低限ほしい metadata | 補足 |
| --- | --- | --- | --- |
| 初回入力時 | `shared/stock` | `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` | 既知の安定知識を先に探す。`source_sessions`, `derived_from` は根拠確認に使う。 |
| 初回入力時 | `flow/` | `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags`, `source_sessions` | まだ stock 化されていない進行中知識や関連 session を探す。review 済み・stock 昇格済み knowledge は主対象から外す。 |
| 作業中 | 同一 session の `raw/` | `title`, `description` | 基本は重い検索をしない。必要なときだけ局所確認する。 |
| 個別タスク完了時 | 同一 session の `raw/` | `title`, `description`, `tags` | 証拠の取りこぼしや同 topic の raw を確認する。 |
| 個別タスク完了時 | `flow/` | `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` | 重複した暫定知識を作らないために確認する。 |
| 個別タスク完了時 | `shared/stock` | `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` | 似た stock があるなら、新しい flow を作る価値があるかを判断する。 |
| 作業終了時 | `shared/review` | `knowledge_id`, `knowledge_type`, `source_sessions`, `derived_from` | review キュー管理用。通常の knowledge 再利用検索には使わない。 |
| review から stock へ昇格するとき | `shared/stock` | `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags`, `derived_from` | 既存 stock を更新するか、新規 stock を作るかを判断する。 |

### `knowledge_type` の運用方針

- `knowledge_type` は layer ではなく知識の性質を表す別軸で、`tags` とは分けて扱う。
- canonical values は `reference` と `constructive` の 2 つに限定する。
- `reference` は固有名詞、ルール、定義、固定的な対応関係など、lookup 前提で短く正規化したい知識に使う。
- `constructive` は手順、判断基準、因果理解、適用条件、反例など、考え方の過程ごと残したい知識に使う。
- `flow` で付けた `knowledge_type` は review / stock にそのまま引き継ぐ。
- `knowledge_type` を付けた knowledge は、review では `<session_id>--<knowledge_type>--<knowledge_id>.md`、stock では `<knowledge_type>--<knowledge_id>.md` を既定のファイル名とする。

### `tags` の運用方針

- `tags` は layer や state を表すためではなく、topic と検索軸を安定化するために使う。`raw` / `flow` / `review` / `stock` の区別は path で表現する。
- canonical format は YAML list とし、各 tag は lowercase の短い文字列で揃える。
- tag には prefix を付け、検索時に prefix 単位で絞り込みやすくする。

推奨 prefix:

- `domain/...`: 業務・機能領域。例: `domain/api`, `domain/auth`
- `artifact/...`: 対象物。例: `artifact/cli`, `artifact/template`, `artifact/test`
- `task/...`: 作業意図。例: `task/investigation`, `task/debug`, `task/review`
- `tech/...`: 技術要素。例: `tech/pytest`, `tech/pydantic`, `tech/github-actions`
- `issue/...`: 問題や論点。例: `issue/rate-limit`, `issue/schema-mismatch`

レイヤー別の目安:

- `raw/`: tags は任意。必要なら `artifact/...` または `tech/...` を 1-2 個付ける。
- `flow/`: 重複防止と再利用のため、原則 2-4 個付ける。少なくとも `domain/...` または `artifact/...` のどちらか 1 つを含める。
- `shared/review/`: `flow` の tags をそのまま引き継ぎ、review 用に個別最適化しない。
- `shared/stock/`: 再利用検索の主対象なので、原則 2-5 個付ける。`domain/...` または `artifact/...` に加えて、必要なら `task/...` と `issue/...` を付ける。

例:

```yaml
---
title: API Rate Limit Notes
description: 429 応答条件の観測メモ
summary: 429 応答条件の要約
knowledge_id: api-rate-limit-notes
knowledge_type: reference
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

この方針により、`search knowledge` で metadata と本文を横断的に拾い、LLM が多数ファイルを俯瞰しやすい形を保つ。

## CLI の使い方

CLI は `argparse` ベースの `knowledge_refinery.cli` で実装しており、パッケージをインストールすると `knowledge-refinery` コマンドが使えます。

```bash
uv tool install /path/to/knowledge-refinery
knowledge-refinery --help
```

開発中はインストールせずに、リポジトリ直下でそのまま次のようにも実行できます。

```bash
uv run knowledge-refinery --help
```

`pyproject.toml` の依存に `PyYAML` を含めているため、このパッケージをインストールして CLI を使う場合は別途 `PyYAML` を追加する必要はありません。

## 開発時の検証

このリポジトリの検証は `tox` を入口にして、`ruff`・`mypy`・`pytest` をまとめて実行します。

```bash
uv run tox
```

個別に確認したい場合は、env を絞って実行できます。

```bash
uv run tox -e ruff
uv run tox -e mypy
uv run tox -e py313
```

## 導入手順

### 1) テンプレートを対象リポジトリへコピー

```bash
uv run knowledge-refinery apply-template --target /path/to/your-repo
uv run knowledge-refinery apply-template --target /path/to/your-repo --skill-destination agent
```

`apply-template` は package に埋め込まれた template 資産から以下をまとめて配置します。

- `.codex/skills/` または `.agent/skills/` 配下の skill 配布
- `.refinery/shared/` の初期配置
- `.refinery/template-meta.yaml` への `cli_version` 記録

### 2) 対象リポジトリで CLI を使えるようにする

展開先では `knowledge-refinery` CLI を別途インストールして使う前提です。`uv tool install` でこのパッケージを入れてください。

```bash
uv tool install /path/to/knowledge-refinery
```

`PyYAML` は CLI の依存に含まれているため、追加で `uv add PyYAML` する必要はありません。

パッケージ更新後にインストール済み CLI を追従させたい場合も、同じ `uv tool install /path/to/knowledge-refinery` を再実行すればよいです。

### 3) 対象リポジトリの `AGENTS.md` または `CLAUDE.md` に追記

対象のガイドファイルには別コマンドで管理ブロックを追記または更新します。

```bash
knowledge-refinery update-agents-md --target /path/to/your-repo --lang jp
knowledge-refinery update-agents-md --target /path/to/your-repo --lang en
knowledge-refinery update-agents-md --target /path/to/your-repo --filename CLAUDE.md --lang jp
```

このコマンドは、展開先の `AGENTS.md` または `CLAUDE.md` に managed block を追加し、既存ブロックがある場合は選んだ言語で更新します。`--target` にファイルパスを直接渡した場合は、そのファイル名を優先します。

### 4) パッケージ更新後に配布物を追従更新

埋め込み template を更新したあとに配布先の skill や shared 配下を追従させたい場合は、更新専用コマンドを使います。

```bash
knowledge-refinery update-template --target /path/to/your-repo
knowledge-refinery update-template --target /path/to/your-repo --skill-destination agent
knowledge-refinery update-agents-md --target /path/to/your-repo --lang jp
```

`update-template` は `apply-template --force` 相当で、既存の `.codex/skills/` または `.agent/skills/` と `.refinery/shared/` を上書き更新します。あわせて `.refinery/template-meta.yaml` も更新し、その時点で使った CLI バージョンを `cli_version` として記録します。

ただし、運用で育てる前提の `.refinery/shared/state.md` は既存ファイルがある場合に保持し、上書きしません。

### 5) skills 配置確認

以下が存在することを確認してください。

- `.codex/skills/refinery-capture/SKILL.md` または `.agent/skills/refinery-capture/SKILL.md`
- `.codex/skills/refinery-curation/SKILL.md` または `.agent/skills/refinery-curation/SKILL.md`
- `.codex/skills/refinery-session/SKILL.md` または `.agent/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-shared/SKILL.md` または `.agent/skills/refinery-shared/SKILL.md`
- `.codex/skills/refinery-repair/SKILL.md` または `.agent/skills/refinery-repair/SKILL.md`
- `.refinery/template-meta.yaml`
- `.refinery/shared/review/AGENTS.md`
- `.refinery/shared/stock/AGENTS.md`

配布される skill の責務は以下です。

- `refinery-session`: セッション開始、マイルストーン管理、review 準備のオーケストレーション
- `refinery-capture`: 作業中の証拠や観測事実を `raw/` へ軽量記録
- `refinery-curation`: `raw/` の証拠を `flow/` の暫定知識へ整理
- `refinery-shared`: review 候補の promote / reject と shared 更新
- `refinery-repair`: front matter や `meta.yaml` の修復

### 6) skills runtime CLI

展開先では、インストール済みの `knowledge-refinery` CLI をそのまま使えます。

```bash
knowledge-refinery skills init-session --task "調査を始める"
knowledge-refinery skills update-session --session-id 20260411T041820Z-l5al2u --status paused --phase analysis
knowledge-refinery skills update-session --session-id 20260411T041820Z-l5al2u --clear-blocked-reason
knowledge-refinery skills search sessions
knowledge-refinery skills search knowledge
knowledge-refinery skills search knowledge --scope flow --session-id 20260411T041820Z-l5al2u
knowledge-refinery skills search knowledge --scope stock --knowledge-type reference
knowledge-refinery skills search knowledge --scope review
knowledge-refinery skills search knowledge --scope stock
knowledge-refinery skills upsert-knowledge --scope flow --session-id 20260411T041820Z-l5al2u --file api-rate-limit-notes.md --title "API rate limit notes" --description "Observed API rate limit behavior" --summary "`429` response handling notes" --knowledge-type constructive --tag tech/api --body-file /tmp/body.md
knowledge-refinery skills search review
knowledge-refinery skills search review --knowledge-type constructive
knowledge-refinery skills search review --session-id 20260411T041820Z-l5al2u
knowledge-refinery skills prepare-review --session-id 20260411T041820Z-l5al2u
knowledge-refinery skills promote-review --knowledge-id api-rate-limit-notes --knowledge-type reference
knowledge-refinery skills refresh-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--reference--api-rate-limit-notes.md
knowledge-refinery skills promote-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--reference--api-rate-limit-notes.md
knowledge-refinery skills reject-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--reference--api-rate-limit-notes.md
```

runtime 系コマンドは `skills` 配下のみをサポートします。

各 CLI の役割は以下です。

- `apply-template`: リポジトリへ refinery テンプレートを配布し、skills を `.codex` または `.agent` に配置しつつ shared フォルダを初期化する
- `update-template`: 既存の配布先に対して template を再適用し、skills と shared フォルダを上書き更新する
- `update-agents-md`: `AGENTS.md` または `CLAUDE.md` の managed block を `jp` または `en` で追加・更新する
- `skills init-session`: `sessions/<session_id>/` 配下の `raw/`, `flow/`, それぞれのローカルルール `AGENTS.md`, `state.md`, `meta.yaml` を作る
- `skills update-session`: 指定した `sessions/<session_id>/meta.yaml` の主要フィールドを安全に更新する。`--clear-*` で nullable 項目を消せる
- `skills search sessions`: `sessions/*/meta.yaml` と `state.md` を検索・一覧する。`--session-id`, `--status`, `--phase`, `--domain` で絞り込める
- `skills search knowledge`: `.refinery` 配下の knowledge Markdown を検索・一覧する。既定では `flow|stock` を対象にし、`--scope raw|flow|review|stock`, `--session-id`, `--tag`, `--knowledge-id`, `--knowledge-type` で絞り込める
- `skills upsert-knowledge`: `raw|flow|stock` の Markdown knowledge file を型付き引数から作成・更新し、YAML front matter を安全に出力して読み取り検証する
- `skills search review`: `shared/review/` の review ファイルを検索・一覧する。`--session-id`, `--tag`, `--knowledge-id`, `--knowledge-type`, `--include-rejected` で絞り込める
- `skills prepare-review`: `flow` 配下の知識ファイルを `shared/review/` へコピーし、`knowledge_id`, `source_sessions`, `derived_from` を正規化する
- `skills refresh-review`: 既存 review ファイルを元の `flow` から再生成する。`--knowledge-id` が type 違いで曖昧な場合は `--knowledge-type` で絞り込める
- `skills promote-review`: 指定した `shared/review/` の知識ファイルを `shared/stock/` へコピーする。既存 stock は上書きせずスキップする。`--knowledge-id` が type 違いで曖昧な場合は `--knowledge-type` で絞り込める
- `skills reject-review`: 指定した review ファイルを `shared/review/rejected/` へ移動する。`--knowledge-id` が type 違いで曖昧な場合は `--knowledge-type` で絞り込める

`skills init-session` はリポジトリ全体の初期化ではなく、セッション単位の作業フォルダ初期化です。

配布される skill / AGENTS では、shared 更新ルールを満たす場合に `shared/stock` や `shared/state.md` を追加のユーザー確認なしで更新してよい運用を前提とします。CLI 自体は引き続き明示コマンドですが、利用者が毎回「promote してよい」と手動指示する前提ではありません。
