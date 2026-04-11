# knowledge-refinery

複数リポジトリに導入するための **refinery テンプレート配布リポジトリ** です。
このリポジトリ自身では refinery を運用せず、`src/knowledge_refinery/template/` 配下の配布物を管理します。

今回のテンプレートは、利用時に必要な以下2点を最優先で揃える構成です。

1. `skills` の配置
2. `AGENTS.md` への管理ブロック追記

## テンプレート構成

```text
src/
  knowledge_refinery/
    cli.py
    template/
      codex/
        skills/
          refinery-session/
            SKILL.md
          refinery-shared/
            SKILL.md
      refinery/
        shared/
          review/
            AGENTS.md
            README.md
            rejected/
              AGENTS.md
              README.md
          state.md
          stock/
            AGENTS.md
            README.md
```

## 知識ファイル形式

refinery で扱う知識ファイルは、`raw/`, `flow/`, `shared/review/`, `shared/stock/` を問わず、原則 Markdown (`.md`) で管理します。

- 1ファイル1トピックを基本とする
- 各ファイルの先頭に YAML front matter を付ける
- `flow` では最低でも `title`, `description`, `summary` を持たせる
- `review` / `stock` では最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を持たせる
- 必要に応じて `tags` や `confidence` を追加する
- ディレクトリ単位の運用ルールは各ディレクトリの `AGENTS.md` に置く
- `flow -> review -> stock` の系譜は `derived_from` で辿る

例:

```yaml
---
title: API Rate Limit Notes
description: 429 応答条件の観測メモ
summary: 429 応答条件の要約
knowledge_id: api-rate-limit-notes
source_sessions:
  - 20260411T041820Z-l5al2u
derived_from:
  - .refinery/sessions/20260411T041820Z-l5al2u/flow/api-rate-limit-notes.md
tags:
  - api
  - rate-limit
confidence: medium
---
```

この方針により、`list-headers` で front matter を横断的に拾い、LLM が多数ファイルを俯瞰しやすい形を保つ。

## CLI の使い方

CLI は `argparse` ベースの `knowledge_refinery.cli` で実装しており、パッケージをインストールすると `knowledge-refinery` コマンドが使えます。

```bash
uv tool install /path/to/knowledge-refinery
knowledge-refinery --help
```

開発中はインストールせずに、リポジトリ直下でそのまま次のようにも実行できます。

```bash
uv run knowledge-refinery --help
```

`pyproject.toml` の依存に `PyYAML` を含めているため、このパッケージをインストールして CLI を使う場合は別途 `PyYAML` を追加する必要はありません。

## 導入手順

### 1) テンプレートを対象リポジトリへコピー

```bash
uv run knowledge-refinery apply-template --target /path/to/your-repo
```

`apply-template` は package に埋め込まれた template 資産から以下をまとめて配置します。

- `.codex/skills/` 配下の skill 配布
- `.refinery/shared/` の初期配置

### 2) 対象リポジトリで CLI を使えるようにする

展開先では `knowledge-refinery` CLI を別途インストールして使う前提です。`uv tool install` でこのパッケージを入れてください。

```bash
uv tool install /path/to/knowledge-refinery
```

`PyYAML` は CLI の依存に含まれているため、追加で `uv add PyYAML` する必要はありません。

### 3) 対象リポジトリの `AGENTS.md` に追記

`AGENTS.md` には別コマンドで管理ブロックを追記または更新します。

```bash
knowledge-refinery update-agents-md --target /path/to/your-repo --lang jp
knowledge-refinery update-agents-md --target /path/to/your-repo --lang en
```

このコマンドは、展開先の `AGENTS.md` に managed block を追加し、既存ブロックがある場合は選んだ言語で更新します。

### 4) skills 配置確認

以下が存在することを確認してください。

- `.codex/skills/refinery-session/SKILL.md`
- `.codex/skills/refinery-shared/SKILL.md`
- `.refinery/shared/review/AGENTS.md`
- `.refinery/shared/stock/AGENTS.md`

### 5) セッション操作 CLI

展開先では、インストール済みの `knowledge-refinery` CLI をそのまま使えます。

```bash
knowledge-refinery init-session --task "調査を始める"
knowledge-refinery list-sessions
knowledge-refinery list-headers
knowledge-refinery list-headers --scope flow --session-id 20260411T041820Z-l5al2u
knowledge-refinery list-headers --scope review
knowledge-refinery list-headers --scope stock
knowledge-refinery list-review
knowledge-refinery list-review --session-id 20260411T041820Z-l5al2u
knowledge-refinery prepare-review --session-id 20260411T041820Z-l5al2u
knowledge-refinery refresh-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--api-rate-limit-notes.md
knowledge-refinery promote-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--api-rate-limit-notes.md
knowledge-refinery reject-review --review-file .refinery/shared/review/20260411T041820Z-l5al2u--api-rate-limit-notes.md
```

各 CLI の役割は以下です。

- `apply-template`: リポジトリへ refinery テンプレートを配布し、skills と shared フォルダを初期化する
- `update-agents-md`: `AGENTS.md` の managed block を `jp` または `en` で追加・更新する
- `init-session`: `sessions/<session_id>/` 配下の `raw/`, `flow/`, それぞれのローカルルール `AGENTS.md`, `state.md`, `meta.yaml` を作る
- `list-sessions`: `sessions/*/meta.yaml` を一覧する
- `list-headers`: `.refinery` 配下の Markdown YAML front matter を一覧する。`--scope raw|flow|review|stock` と `--session-id` で絞り込める
- `list-review`: `shared/review/` の active review ファイルを一覧する。`--session-id` で `source_sessions` ベースに絞り込める
- `prepare-review`: `flow` 配下の知識ファイルを `shared/review/` へコピーし、`knowledge_id`, `source_sessions`, `derived_from` を正規化する
- `refresh-review`: 既存 review ファイルを元の `flow` から再生成する
- `promote-review`: 指定した `shared/review/` の知識ファイルを `shared/stock/` へコピーする
- `reject-review`: 指定した review ファイルを `shared/review/rejected/` へ移動する

`init-session` はリポジトリ全体の初期化ではなく、セッション単位の作業フォルダ初期化です。
