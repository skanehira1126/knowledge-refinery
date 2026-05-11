## refinery 利用ルール

このリポジトリでは refinery を利用して作業記録を管理する。

- セッション開始時は `knowledge-refinery session init --task "..."` を利用する。
- 作業中の証拠は `raw/`、暫定知識は `flow/`、現在地は `state.md` に記録する。
- `shared/stock` は安定知識のみを格納する。
- `shared/experiences` は `shared/stock` から手動で抽出した短い経験則を格納し、`shared/experiences/EXPERIENCES.md` で参照範囲を管理する。
- `shared/review` は `flow` からコピーした review 用スナップショットを格納する。
- `shared/review/rejected` は review キューから外した rejected ファイルを保管する。
- `flow` を更新したセッションでは、作業終了前に `knowledge-refinery review prepare` または `knowledge-refinery review refresh` で review スナップショットを整え、`knowledge-refinery review search` などで review キューを確認し、昇格候補があれば `refinery-shared` の手順で promote / reject を判断する。
- 知識ファイルは原則 Markdown (`.md`) で管理し、検索性のため各ファイルの先頭に YAML front matter を付ける。
- ディレクトリ単位のローカル運用ルールは各ディレクトリの `AGENTS.md` に置く。
- shared 領域はルールを満たす更新であれば自律的に更新してよい。
- `sessions/*/meta.yaml` の更新は `knowledge-refinery session update` を優先し、直接編集が必要な場合だけ YAML の型を保って扱う。

### 知識ファイル形式

- `raw/`, `flow/`, `shared/review/`, `shared/stock/` の知識ファイルは原則 `.md` とする。
- 各知識ファイルは 1 ファイル 1 トピックを基本とする。
- `flow` の知識ファイルは最低でも `title`, `description`, `summary` を入れる。
- `review` / `stock` の知識ファイルは最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を入れる。
- 必要に応じて `tags` や `confidence` などを YAML として追加してよい。
- `tags` は検索軸を揃えるために `domain/...`, `artifact/...`, `task/...`, `tech/...`, `issue/...` のような prefix 付き taxonomy を推奨する。
- `raw` では `tags` は任意だが、`flow` と `stock` では 2-4 個程度の tag を付け、少なくとも `domain/...` または `artifact/...` を含めるのを推奨する。
- front matter は YAML として正しく保ち、配列や真偽値を文字列化で壊さない。
- `flow -> review` と `review -> stock` はいずれもコピーで扱い、系譜は `derived_from` で辿れるようにする。

```yaml
---
title: API Rate Limit Notes
description: 429 応答条件の観測メモ
summary: 429 応答条件の要約
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

### 利用する skill

- セッション開始、知識化タイミングの判断、review 準備までは `refinery-session` を使う。
- 作業中の観測事実や証拠を `raw/` へ軽量記録するときは `refinery-capture` を使う。
- マイルストーンごとに `raw/` を `flow/` の暫定知識へ整理するときは `refinery-curation` を使う。
- `flow` を更新したセッションの終了前に review キューを確認し、昇格候補の promote / reject 判断は `refinery-shared` を使う。
- `shared/stock` から短い経験則を抽出し、`shared/experiences` や `EXPERIENCES.md` を更新するときは `refinery-experiences` を使う。
- front matter や `meta.yaml` が壊れて CLI が読めないときの修復は `refinery-repair` を使う。
- パッケージ更新後に配布済み skill や shared テンプレートを追従させる場合は、`knowledge-refinery update-template --target .` を使い、その後 `knowledge-refinery update-agents-md --target . --lang jp|en` で管理ブロックも更新する。既存の `shared/state.md` と `shared/experiences/EXPERIENCES.md` は update-template では上書きしない。

### meta.yaml 更新規約

- `sessions/*/meta.yaml` は YAML として正しく保つ。
- 更新時は既存キーを維持し、意図しない削除・型変更を避ける。
- `null` / `[]` / 文字列などの型を崩さない。
- 更新後は `knowledge-refinery session search` や `knowledge-refinery knowledge search` などの検索 CLI で確認する。

### meta.yaml 形式

- `meta.yaml` を唯一のセッションメタデータ形式として管理する。
- JSON 形式との併用はしない。
