# 開発・リリース

## 検証

```bash
bash scripts/validate.sh
```

このscriptは次を実行します。

- Ruff、Mypy、Pytest（tox）
- `mkdocs build --strict`
- Plugin manifest validator
- 4つの配布Skill validator

`CODEX_HOME` が未設定の場合は `~/.codex` を使います。

## lock更新

dependencyを変更したときは次を実行し、`uv.lock` をcommit対象に含めます。

```bash
uv lock
uv run --frozen tox
```

## Plugin更新の確認

```bash
codex plugin marketplace upgrade knowledge-refinery
```

CLIのリリース更新は `uv tool upgrade knowledge-refinery` で行います。開発checkoutへ再接続するときは、そのrootで `PLUGIN_ROOT="$(pwd -P)"` を設定し、`uv tool install --force --editable "$PLUGIN_ROOT"` を実行します。

ローカルmarketplaceで反映を確認する場合も、Pluginを再installして新しいtaskを開きます。manifest、MCP tool名・引数・戻り値、YAML schemaを変更した場合はREADME、Skills、docs、テストを同時に更新します。
