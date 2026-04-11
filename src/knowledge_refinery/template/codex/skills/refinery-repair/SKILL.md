---
name: refinery-repair
description: 不正な front matter や meta.yaml を修復し、refinery CLI で再び読める状態へ戻す skill。YAML の型や lineage を壊さずに整備するときに使う。
---

# refinery-repair skill

## Purpose

refinery 管理下の Markdown / YAML ファイルを、CLI が再び安全に読める状態へ戻す。

## When to use

- `knowledge-refinery list-headers` や `list-review` が front matter エラーで落ちたとき
- `knowledge-refinery list-sessions` が `meta.yaml` の不正で読めないとき
- `prepare-review`, `refresh-review`, `promote-review` 実行前に knowledge file の形式を整えたいとき

## Workflow

1. 失敗した CLI とエラーファイルを特定する。
2. 対象ファイルを開き、YAML と本文のどこが壊れているか確認する。
3. front matter または `meta.yaml` を YAML として正しい形に修正する。
4. `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` などの必須項目を運用レイヤーに応じて確認する。
5. 配列・`null`・真偽値・数値を文字列化せず、既存の意味を保ったまま整える。
6. `knowledge-refinery list-headers`, `list-review`, `list-sessions` など該当 CLI で再検証する。

## Preferred commands

- `knowledge-refinery list-headers --root .refinery`
- `knowledge-refinery list-review --root .refinery`
- `knowledge-refinery list-sessions --root .refinery`

## Guardrails

- 壊れた YAML を直すためでも、内容の意味まで勝手に書き換えない。
- `derived_from` や `source_sessions` は、既存情報やパスから妥当に復元できる場合だけ補う。
- `knowledge_id` を修正するときは、既存 review / stock との衝突有無を確認する。
- 配布テンプレートの修正が必要なら、対象リポジトリではなく `knowledge-refinery` 側の template を先に直す。
- 修復後は必ず CLI で読み取り確認し、traceback が消えたことを確認する。

## Repair rules

- Markdown knowledge file は先頭を YAML front matter で始める。
- `flow` は最低でも `title`, `description`, `summary` を持たせる。
- `review` / `stock` は最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を持たせる。
- `meta.yaml` は mapping をトップレベルに置き、既存キーの型を維持する。
