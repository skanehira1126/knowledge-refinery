## refinery 利用ルール

このリポジトリでは refinery を利用して作業記録を管理する。

- セッション開始時は `scripts/init_session.py` で `sessions/<session_id>/` を作成する。
- 作業中の証拠は `raw/`、暫定知識は `flow/`、現在地は `state.md` に記録する。
- `shared/stock` は安定知識のみを格納する。
- shared 領域の更新はユーザーの明示指示がある場合のみ行う。

### skill 配置

- `.codex/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-shared/SKILL.md`
