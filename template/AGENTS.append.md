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

### meta.json 更新規約

- `sessions/*/meta.json` は JSON として正しく保つ（手書き置換で壊さない）。
- 更新時は既存キーを維持し、意図しない削除・型変更を避ける。
- `null` / `[]` / 文字列などの型を崩さない。
- 更新後は `list_sessions.py` など JSON 読み取りツールで確認する。


### meta.json 形式

- `meta.json` を唯一のセッションメタデータ形式として管理する。
- 非 JSON 形式（YAML 等）の併用はしない。
