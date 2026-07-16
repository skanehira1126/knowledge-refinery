# トラブルシューティング

まず対象repoのrootで絶対パスを取得し、機械可読の診断を実行します。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
knowledge-refinery doctor --target "$PROJECT_ROOT" --json
```

## active vaultがない

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"  # 実際のvault保存先へ変更
knowledge-refinery vault configure --root "$REFINERY_VAULT"
```

markerがない場合は `vault init` を実行します。

## repoがdisabled

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

OFFのまま使うことはできません。MCPもserver側で拒否します。disabledは正常なopt-outなので、利用者が明示的に再有効化を望んだ場合だけこのコマンドを実行します。

## PluginとCLIのversionが違う

`refinery_info.version` を `MCP_VERSION` に設定し、`knowledge-refinery doctor --target "$PROJECT_ROOT" --mcp-version "$MCP_VERSION"` へ渡します。不一致ならmarketplaceをupgradeしてPluginを再installし、CLIも `uv tool upgrade knowledge-refinery` で同じreleaseへ更新します。更新後は新しいtask/sessionを開きます。

## `vault_registered: false`

active vaultが正しいか確認し、初回登録なら `project setup`、既存設定の復帰なら `project enable --vault ...` を実行します。

## MCPが表示されない

1. Pluginがinstall/enabledか確認する。
2. `uv` がPATHにあるか `doctor` で確認する。
3. marketplaceをupgradeし、Pluginを再installする。
4. 新しいtask/sessionを開く。

```bash
codex plugin marketplace upgrade knowledge-refinery
```

## CLIが見つからない

```bash
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
uv tool dir --bin
```

`uv tool dir --bin` の出力がPATHに含まれることを確認します。

## validationエラー

`refinery_validate` の `path` と `error` を確認します。shared memoryではqualified source、distinct project数、参照experienceの存在を優先的に確認します。
