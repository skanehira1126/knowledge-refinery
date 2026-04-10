# refinery-session skill

## Purpose

セッション運用（capture/curation）を標準化する。

## Workflow

1. `python3 scripts/init_session.py --task "<task>"` でセッション作成
2. `raw/` に証拠材を追記（append-only）
3. `flow/` に暫定知識を整理
4. `state.md` を最小更新（目的・進捗・次アクション）

## Guardrails

- `shared/` を直接更新しない
- promotion が必要な場合はユーザー明示を待つ
