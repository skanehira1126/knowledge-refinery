---
name: refinery-shared
description: shared レイヤー（state/stock）更新時の判断と記録を標準化する skill。session の知識を shared に昇格するか判断し、CLI ベースで shared/state.md と shared/stock を更新するときに使う。
---

# refinery-shared skill

## Purpose

shared レイヤー（state/stock）更新時の判断と記録を標準化する。

## Workflow

1. session の `flow` / `state` と `shared/review` を確認する。
2. `knowledge-refinery list-review` で review キューを確認する。
3. 必要に応じて `knowledge-refinery refresh-review ...` で review を最新の flow に追従させる。
4. review 済みの候補を `knowledge-refinery promote-review ...` で `shared/stock` へコピーする。
5. 不採用の候補は `knowledge-refinery reject-review ...` で review キューから外す。
6. 必要最小限の現在地を `shared/state.md` に反映する。
7. 変更理由をコミットメッセージに明記する。

## Guardrails

- shared 更新はユーザー明示指示がある場合のみ実施する。
- 未検証の内容を `stock` に入れない。
- `shared/stock` の知識ファイルは原則 `.md` とし、先頭に YAML front matter を付ける。
- `review -> stock` は move ではなく copy で扱う。
