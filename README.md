# knowledge-refinery

複数リポジトリに導入するための **refinery テンプレート配布リポジトリ** です。

今回のテンプレートは、利用時に必要な以下2点を最優先で揃える構成です。

1. `skills` の配置
2. `AGENTS.md` への追記テンプレート

## テンプレート構成

```text
template/
  AGENTS.append.md
  .codex/
    skills/
      refinery-session/
        SKILL.md
        scripts/
          init_session.py
          list_headers.py
      refinery-shared/
        SKILL.md
  .refinery/
    shared/
      state.md
      stock/README.md
```

## 導入手順

### 1) テンプレートを対象リポジトリへコピー

```bash
python3 scripts/apply_template.py --target /path/to/your-repo
```

### 2) 対象リポジトリの `AGENTS.md` に追記

`template/AGENTS.append.md` の内容を、対象リポジトリの `AGENTS.md` に追記してください。

### 3) skills 配置確認

以下が存在することを確認してください。

- `.codex/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-session/scripts/init_session.py`
- `.codex/skills/refinery-session/scripts/list_headers.py`
- `.codex/skills/refinery-shared/SKILL.md`

## 補助スクリプト

- `scripts/apply_template.py`: `template/` の配布適用
- `.codex/skills/refinery-session/scripts/init_session.py`: `sessions/<session_id>/` 初期化
- `.codex/skills/refinery-session/scripts/list_headers.py`: `.refinery/` 配下の front matter 一覧化
