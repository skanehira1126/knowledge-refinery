---
name: refinery-stock
description: shared/stock の陳腐化候補を棚卸しし、ユーザと相談しながら削除または更新を進める skill。stock 反映済みで個別性の高い flow knowledge を整理し、検索ノイズを下げたいときにも使う。
---

# refinery-stock skill

## Purpose

`shared/stock` を「現時点で再利用価値がある安定知識」に保つ。
削除可否を機械的に決めず、候補を探索してユーザと会話しながら整理する。

## Applicability

- `shared/stock` に古い知識や重複知識が溜まり、棚卸ししたいとき
- 現在のテンプレート、運用方針、実装と食い違う stock を見直したいとき
- stock へ反映済みで、かつ個別性が高い `flow` を削除して検索ノイズを下げたいとき

## Workflow

1. `knowledge-refinery knowledge search --scope stock` で stock 一覧を確認し、`title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` を手掛かりに候補を洗い出す。
2. 候補ごとに実ファイルを開き、本文、`derived_from`, `source_sessions` を確認して、何が obsolete なのかを具体化する。
3. 必要に応じて現行の template / AGENTS / skill / 実装を確認し、stock が今の運用と矛盾していないかを見る。
4. 候補を「削除推奨」「更新推奨」「維持」のいずれかで整理し、理由を短く添えてユーザへ提示する。
5. ユーザ合意を得た候補だけを削除または更新する。削除は一括ではなく、理由ごとにまとめて確認してよい。
6. stock を整理した結果、同じ知識が `flow` にも残っており、しかも session 固有で再利用価値が低い場合は、その `flow` も削除候補としてユーザに確認する。
7. 変更後は `knowledge-refinery knowledge search --scope stock` や `--scope flow` で再確認し、検索ノイズが下がっているかを確認する。

## Preferred commands

- `knowledge-refinery knowledge search --scope stock`
- `knowledge-refinery knowledge search --scope stock --knowledge-type reference`
- `knowledge-refinery knowledge search --scope stock --knowledge-type constructive`
- `knowledge-refinery knowledge search --scope flow`

## Obsolete signals

- 現行の template / skill / AGENTS / 実装と矛盾している
- 安定知識ではなく、特定 session や特定時点に閉じた事情が中心になっている
- 同じ内容が別の stock に正規化済みで、重複になっている
- 一般化して残すより、`raw` / `flow` の文脈付き記録としてだけ価値がある
- 「以前は正しかったが今は運用が変わった」ため、誤誘導のほうが大きい

## Flow cleanup policy

- `flow` は進行中の暫定知識を置く working set とみなし、archive としては使わない。
- stock 反映済みで、かつ session 固有の補助情報しか持たない `flow` は、検索性維持のため削除を優先する。
- まだ未解決論点、反証、次アクションが残っている `flow` は消さない。
- 現状の CLI には `flow` knowledge 単位の canonical な status 管理と検索除外がないため、検索ノイズ対策として ad-hoc な `status` を増やす前に削除で対処する。

## Guardrails

- `shared/stock` の削除はユーザ確認なしに行わない。
- obsolete 判定は「古い」だけでなく、「今も再利用価値があるか」で判断する。
- 内容はまだ有効だが表現だけ古い場合は、削除より更新を優先する。
- `knowledge_id` を変えると既存参照が崩れるため、削除や分割が必要な理由が明確な場合だけ変更する。
- `flow` の検索ノイズ問題を status で解くなら、将来の CLI / schema 変更として扱う。現行運用の knowledge file に非 canonical な状態管理を前提追加しない。
