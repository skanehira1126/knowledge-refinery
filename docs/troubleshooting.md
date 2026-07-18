# トラブルシューティング

定期棚卸しと復旧の標準手順は[ナレッジ運用](knowledge-operations.md)も参照してください。

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

`doctor` の `mcp_runtime: ok` はローカルserver moduleが起動可能であることを示しますが、Codex側でPluginがinstall/enabledかは判定しません。MCPが表示されない場合は必ずPlugin settingsも確認します。

## CLIが見つからない

```bash
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
uv tool dir --bin
```

`uv tool dir --bin` の出力がPATHに含まれることを確認します。

## validationエラー

`knowledge-refinery doctor --target "$PROJECT_ROOT" --json`のvalidation errors、または
`refinery_validate`の`path`と`error`を確認します。shared memoryではqualified source、
distinct project数、参照experienceの存在を優先的に確認します。

検索は不正文書を隔離して正常文書を返すため、検索結果が少ない場合も `refinery_validate` を実行してください。exact getで対象文書自体が不正な場合は、その場でエラーになります。

エージェントへ復旧を依頼する場合は`$refinery-maintenance`を使い、対象path、Git差分、
修正案を先に報告させます。knowledge文書の削除やmemoryの大幅な書き換えは、利用者が確認する
まで実行しません。

## disabledなのにdoctorが成功する

`enabled: false`は意図的なhealthy opt-outです。doctorはdisabled自体を破損として扱いません。
`project.state: disabled`の間、repo-scoped MCP toolsが検索・書き込みを拒否するのは正常です。
再有効化は利用者が明示的に望んだ場合だけ行います。

明示呼出モードで再開する場合:

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

managed guidanceも復帰して自動運用モードへ戻す場合:

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT" --agents
```

## setup再実行でmetadata差分を拒否された

設定済みrepoでは、setupへ明示したname、summary、tag、technologyを黙って無視しません。
現在値と異なる場合は、現在revisionを取得してmetadata updateを使います。

```bash
knowledge-refinery project metadata show --target "$PROJECT_ROOT" --json
knowledge-refinery project metadata update \
  --target "$PROJECT_ROOT" \
  --summary "更新後の概要" \
  --expected-updated-at "取得したupdated_at"
```

## 意図せずactive vaultを切り替えた

`vault init`、`vault configure`、`project setup --vault`、明示的な`project enable --vault`は
ユーザー全体のactive vaultを更新します。元のvaultへ戻します。

```bash
knowledge-refinery vault configure --root "/absolute/path/to/original-vault"
```

切り替え後は、対象repoごとに`project status`を実行して`active_vault`と
`vault_match`を確認します。

## repoとactive vaultのIDが一致しない

`project status --json`の`configured_vault_id`と`active_vault_id`が異なる場合、そのrepoは
別vaultへbindされています。同じ`project_id`がactive vaultにあってもMCPは接続しません。
意図したvaultへ`vault configure`で戻してください。別vaultへ付け替える操作はknowledge混在に
つながるため、`.refinery.local.yaml`を手編集しません。

## 旧設定にvault IDがない {#legacy-vault-id}

旧versionのmarkerまたはrepoの`.refinery.local.yaml`に`vault_id`がない場合、statusはreadyに
なりません。新しいcloneでもlocal fileは意図的に引き継がれません。対象vaultとrepoの対応を
確認したうえで、次を明示実行して同じIDへbindします。

```bash
knowledge-refinery vault init --root "$REFINERY_VAULT"
knowledge-refinery project setup --target "$PROJECT_ROOT" --vault "$REFINERY_VAULT"
```

disabled repoはsetupで暗黙enableしないため、利用者が再開を明示した場合だけ2行目を
`project enable --target "$PROJECT_ROOT" --vault "$REFINERY_VAULT"`へ置き換えます。
