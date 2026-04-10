---
name: refinery-session
description: セッション運用（capture/curation）を標準化する skill。セッション開始、raw/flow/state の更新、session 配下の補助スクリプト利用が必要なときに使う。
---

# refinery-session skill

## Purpose

セッション運用（capture/curation）を標準化する。

## Workflow

1. `python3 scripts/init_session.py --task "<task>"` でセッションを作成する。
2. `raw/` に証拠材を追記する（append-only を維持する）。
3. `flow/` に暫定知識を整理する。
4. `state.md` を最小更新する（目的・進捗・次アクション）。

## Skill local scripts

- `scripts/init_session.py`
- `scripts/list_headers.py`

この skill 配下に配置した script を優先利用する。

## Guardrails

- `shared/` を直接更新しない。
- promotion が必要な場合はユーザー明示を待つ。
