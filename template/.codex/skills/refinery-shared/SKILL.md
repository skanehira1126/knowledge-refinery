---
name: refinery-shared
description: shared レイヤー（state/stock）更新時の判断と記録を標準化する skill。session の知識を shared に昇格するか判断し、shared/state.md と shared/stock を更新するときに使う。
---

# refinery-shared skill

## Purpose

shared レイヤー（state/stock）更新時の判断と記録を標準化する。

## Workflow

1. session の `flow` / `state` を確認する。
2. 安定知識のみ `shared/stock` へ昇格する。
3. 必要最小限の現在地を `shared/state.md` に反映する。
4. 変更理由をコミットメッセージに明記する。

## Guardrails

- shared 更新はユーザー明示指示がある場合のみ実施する。
- 未検証の内容を `stock` に入れない。
