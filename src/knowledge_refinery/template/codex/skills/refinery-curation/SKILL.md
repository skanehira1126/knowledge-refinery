---
name: refinery-curation
description: raw レイヤーの証拠を flow レイヤーの暫定知識へ整理する skill。マイルストーンごとに観測事実を統合し、summary 付きの知識へ再構成するときに使う。
---

# refinery-curation skill

## Purpose

`raw/` に蓄積した証拠を、再利用しやすい `flow/` の暫定知識へ整理する。
証拠の束をそのまま複製するのではなく、要点・解釈・未解決点を統合して残す。

## Applicability

- タスクが一区切りつき、`raw/` を整理して `flow/` に上げたいとき
- 同じ topic に関する raw が増え、要約や仮説を保ちたくなったとき
- review 生成前に session の暫定知識を整えたいとき

## Workflow

1. 更新対象の `session_id` を確認し、`knowledge-refinery skills search knowledge --session-id "<session_id>" --scope raw` と `--scope flow` で関連 topic を把握する。
2. 対象 topic の raw ファイルを読み、観測事実を論点ごとに整理する。
3. `flow/` に Markdown 知識ファイルを追加または更新し、少なくとも `title`, `description`, `summary` を埋める。
4. 同じ topic の flow ファイルが既にある場合は、raw の断片を追記するのではなく、最新の統合結果として再構成してよい。
5. 不確実性、反証、未解決の論点は消さずに残し、必要なら `confidence` や本文で明示する。
6. `flow/` の更新により次アクションや review 準備状況が変わる場合は、`refinery-session` に戻って `state.md` や review 手順を更新する。

## Preferred commands

- `knowledge-refinery skills search knowledge --session-id "<session_id>" --scope raw`
- `knowledge-refinery skills search knowledge --session-id "<session_id>" --scope flow`

## Guardrails

- `raw` は元証拠なので、結論に合わせて改変しない。
- `flow` は暫定知識の統合結果として更新してよいが、証拠の出所が不明になる要約は避ける。
- 反対証拠や未確定事項を消さず、暫定性を保つ。
- `flow` から直接 `shared/stock` へ昇格せず、review は `refinery-session` と `refinery-shared` の手順で扱う。

## Flow file format

- `flow` の知識ファイルは最低でも `title`, `description`, `summary` を持たせる。
- `knowledge_id` は任意だが、後続 review で安定運用したい topic では早めに付けてよい。
- `source_sessions`, `tags`, `confidence` は必要に応じて追加してよい。
- `tags` は重複防止と再利用検索のため、原則 2-4 個付ける。少なくとも `domain/...` または `artifact/...` を 1 つ含め、必要なら `task/...`, `tech/...`, `issue/...` を追加する。
- 本文には要点、根拠となる観測、未解決点を短く整理する。
