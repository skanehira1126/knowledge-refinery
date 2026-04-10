# refinery-shared skill

## Purpose

shared レイヤー（state/stock）更新時の判断と記録を標準化する。

## Workflow

1. session の `flow` / `state` を確認
2. 安定知識のみ `shared/stock` へ昇格
3. 必要最小限の現在地を `shared/state.md` に反映
4. 変更理由をコミットメッセージに明記

## Guardrails

- shared 更新はユーザー明示指示がある場合のみ
- 未検証の内容を `stock` に入れない
