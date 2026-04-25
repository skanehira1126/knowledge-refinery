---
name: refinery-session
description: セッション運用全体を標準化する orchestrator skill。会話セッション開始、マイルストーン単位の知識整理、依頼終了時の review 準備と shared 連携を進行管理するときに使う。
---

# refinery-session skill

## Purpose

会話セッションに紐づく知識ストアのライフサイクルを管理する。
記録内容そのものは `refinery-capture` と `refinery-curation` に委ね、この skill は「いつ何を実施するか」を揃える。

## Applicability

- session の新規作成 / 再利用を判断するとき
- `raw/`, `flow/`, `state.md`, `shared/review` をどのタイミングで更新するか整理したいとき
- 依頼完了前に review 準備と `refinery-shared` への引き渡しを行うとき

## Workflow

### Session start

1. 対象の会話に対応する `session_id` が未作成なら、`knowledge-refinery skills init-session --task "<task>"` でセッション知識ストアを作成する。
2. 既存 session がある場合は、その `session_id` を確認して以後の更新対象として扱う。
3. 初回入力時はまず `knowledge-refinery skills search knowledge --scope stock` で既知の安定知識を確認し、その後必要に応じて `knowledge-refinery skills search knowledge --session-id "<session_id>" --scope flow` で未昇格の関連知識を確認する。

### During work

1. ユーザに依頼された作業を進める。
2. 新しい観測事実や証拠が出たら `refinery-capture` の手順で `raw/` に残す。
3. 目的・進捗・次アクションに変化があれば、session に紐づく `state.md` を最小更新する。

### After task milestone

1. 個別タスクを完了した後など、整理が必要なタイミングで `raw/` を横断的に確認する。
2. 整理が必要なら `refinery-curation` の手順で `raw/` を `flow/` の暫定知識へ統合する。
3. `flow/` を更新したら、必要に応じて `state.md` を更新する。
4. `flow` や `stock` に似た topic がないかを `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` で確認し、重複記録を避ける。
5. `raw/` から `flow/` への知識整理が重い場合は、ユーザが明示的に求めたときに限りサブエージェントへ委譲してよい。

### Before closing the request

1. ユーザの依頼を完了したら、未整理の `raw/` が残っていないか確認し、必要なら `refinery-curation` を再度適用する。
2. review 用スナップショットが未作成なら `knowledge-refinery skills prepare-review` で `flow` から `shared/review` へコピーする。
3. 既存の review 用スナップショットを最新の `flow` に置き換える必要がある場合は、`knowledge-refinery skills search review --session-id "<session_id>"` で対象を特定して `knowledge-refinery skills refresh-review --review-file "<review_file>"` を実行する。
4. review 準備ができたら `refinery-shared` の手順へ進み、promotion / rejection を判断する。
5. session に紐づく `state.md` を更新し、依頼完了時点の現在地を残す。

## Preferred commands

- `knowledge-refinery skills init-session --task "<task>"`
- `knowledge-refinery skills update-session --session-id "<session_id>" --next-action "<next_action>"`
- `knowledge-refinery skills search sessions`
- `knowledge-refinery skills search knowledge --session-id "<session_id>" --scope flow`
- `knowledge-refinery skills search review --session-id "<session_id>"`
- `knowledge-refinery skills search knowledge --scope stock`
- `knowledge-refinery skills prepare-review`
- `knowledge-refinery skills refresh-review --review-file "<review_file>"`

## Guardrails

- `shared/` を直接更新しない。
- `raw` の書き方は `refinery-capture`、`flow` の書き方は `refinery-curation` に委ねる。
- promotion が必要になったら `refinery-shared` の手順で処理し、追加のユーザー確認待ちは不要とする。
- `sessions/*/meta.yaml` を更新するときは、まず `knowledge-refinery skills update-session` を使う。
- `flow -> review` は move ではなく copy で扱う。
- 同じ session の review は追記ではなく再生成で更新する。

## meta.yaml 更新規約

- `sessions/*/meta.yaml` は YAML として扱い、文字列置換ベースで更新しない。
- 既存フィールドの意味・型互換（`null`, list, scalar）を維持する。
- 更新後は `knowledge-refinery skills search sessions` で読み取り確認し、必要なら差分説明に型変更有無を明記する。

## meta.yaml 形式

- `meta.yaml` を唯一のセッションメタデータ形式として扱う。
- JSON 形式との併用はしない。
