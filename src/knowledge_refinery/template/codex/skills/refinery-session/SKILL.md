---
name: refinery-session
description: セッション運用（capture/curation）を標準化する skill。セッション開始、raw/flow/state の更新、review 準備を CLI ベースで行うときに使う。
---

# refinery-session skill

## Purpose

セッション運用（capture/curation）を標準化する。

## Workflow

1. `knowledge-refinery init-session --task "<task>"` でセッションを作成する。
2. `raw/` に Markdown 知識ファイルを追加し、証拠材を追記する（append-only を維持する）。
3. `flow/` に Markdown 知識ファイルを追加し、暫定知識を整理する。
4. `knowledge-refinery prepare-review` で `flow` から `shared/review` へ review 用スナップショットをコピーする。
5. `shared` へ昇格すべき候補があれば `refinery-shared` の手順に進み、`shared/stock` と `shared/state.md` を更新する。
6. `state.md` を最小更新する（目的・進捗・次アクション）。

## Preferred commands

- `knowledge-refinery init-session --task "<task>"`
- `knowledge-refinery list-sessions`
- `knowledge-refinery list-headers`
- `knowledge-refinery prepare-review`

## Guardrails

- `shared/` を直接更新しない。
- promotion が必要になったら `refinery-shared` の手順で処理し、追加のユーザー確認待ちは不要とする。
- `sessions/*/meta.yaml` を更新するときは `PyYAML` を利用する。
- `raw/` と `flow/` の知識ファイルは原則 `.md` とし、先頭に YAML front matter を付ける。
- `flow -> review` は move ではなく copy で扱う。
- skill や shared の配布物を更新するときは手動コピーではなく `knowledge-refinery update-template --target <repo>` を使う。

## Knowledge file format

- 知識ファイルは 1 ファイル 1 トピックを基本とする。
- `flow` の知識ファイルは最低でも `title`, `description`, `summary` を記載する。
- `knowledge_id` は省略可能だが、未指定時はファイル名から導出される。
- `source_sessions` は省略可能だが、review 生成時に session_id が補完される。
- 必要に応じて `tags` や `confidence` を追加してよい。

## meta.yaml 更新規約

- `sessions/*/meta.yaml` は YAML として扱い、文字列置換ベースで更新しない。
- 既存フィールドの意味・型互換（`null`, list, scalar）を維持する。
- 更新後は `knowledge-refinery list-sessions` で読み取り確認し、必要なら差分説明に型変更有無を明記する。


## meta.yaml 形式

- `meta.yaml` を唯一のセッションメタデータ形式として扱う。
- JSON 形式との併用はしない。
