## refinery 利用ルール

このリポジトリでは refinery を利用して作業記録を管理する。

- セッション開始時は `python3 .codex/skills/refinery-session/scripts/init_session.py --task "..."` を利用する。
- 作業中の証拠は `raw/`、暫定知識は `flow/`、現在地は `state.md` に記録する。
- `shared/stock` は安定知識のみを格納する。
- shared 領域の更新はユーザーの明示指示がある場合のみ行う。

### skill 配置

- `.codex/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-session/scripts/init_session.py`
- `.codex/skills/refinery-session/scripts/list_headers.py`
- `.codex/skills/refinery-session/scripts/list_sessions.py`
- `.codex/skills/refinery-shared/SKILL.md`

### meta.yaml 更新規約

- `sessions/*/meta.yaml` は YAML として正しく保つ（キー:値の手書き置換で壊さない）。
- 更新時は既存キーを維持し、意図しない削除・型変更を避ける。
- 文字列は必要に応じて YAML クオートを使い、`null` / `[]` などの型を崩さない。
- 更新後は `list_sessions.py` など YAML パーサー利用ツールで読み取り確認する。
