---
name: refinery-shared
description: shared レイヤー（state/stock）更新時の判断と記録を標準化する skill。session の知識を shared に昇格するか判断し、CLI ベースで shared/state.md と shared/stock を更新するときに使う。
---

# refinery-shared skill

## Purpose

shared レイヤー（state/stock）更新時の判断と記録を標準化する。

## Applicability

- `refinery-session` が review 準備まで終えたあとに、shared へ昇格するか判断するとき
- `shared/review` の候補を promote / reject し、`shared/state.md` を更新するとき

## Workflow

1. `refinery-session` / `refinery-curation` が用意した session の `flow` / `state` と `shared/review` を確認する。
2. `knowledge-refinery skills search review` で review キューを確認する。
3. 必要に応じて `knowledge-refinery skills refresh-review ...` で review を最新の flow に追従させる。
4. review から stock へ上げる前に、`shared/stock` を `title`, `summary`, `knowledge_id`, `knowledge_type`, `tags` で確認し、既存 stock を更新するか新規作成するか判断する。
5. review 済みの候補を `knowledge-refinery skills promote-review ...` で `shared/stock` へコピーする。`knowledge_id` が type 違いで曖昧な場合は `--knowledge-type reference|constructive` を併用する。
6. 不採用の候補は `knowledge-refinery skills reject-review ...` で review キューから外す。`knowledge_id` が type 違いで曖昧な場合は `--knowledge-type reference|constructive` を併用する。
7. 必要最小限の現在地を `shared/state.md` に反映する。
8. 変更理由をコミットメッセージに明記する。

## Guardrails

- shared 更新条件を満たす場合は、追加のユーザー確認なしで `shared/state.md` と `shared/stock` を更新してよい。
- 未検証の内容を `stock` に入れない。
- `shared/stock` の知識ファイルは原則 `.md` とし、先頭に YAML front matter を付ける。
- `shared/stock` を手動で新規作成または front matter 更新するときは、手書き YAML ではなく `knowledge-refinery skills upsert-knowledge --scope stock ...` を優先する。
- CLI を使えず手動で front matter を直す場合だけ、文字列値を原則ダブルクォートし、特に `title`, `description`, `summary` にバッククォート、コロン、角括弧、改行を含む場合は必ず引用する。
- `reference` は重複排除と正規化を優先し、lookup しやすい短い記述に保つ。
- `constructive` は why, 適用条件, 反例, 破綻条件を削りすぎない。
- `stock` は再利用検索の主対象なので、`tags` を維持し、必要なら `domain/...`, `artifact/...`, `task/...`, `tech/...`, `issue/...` の taxonomy に揃える。
- `review -> stock` は move ではなく copy で扱う。
- `shared/stock` を手動で新規作成または front matter 更新した後は `knowledge-refinery skills search knowledge --scope stock` で読み取り確認する。
- skill や shared の配布物を更新するときは手動コピーではなく `knowledge-refinery update-template --target <repo>` を使う。既存の `shared/state.md` は更新時に保持される。
