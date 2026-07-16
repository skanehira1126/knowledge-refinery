# repoの有効・無効

repo側のsource of truthは `.refinery.yaml` です。

`project_id` は登録後に変更しません。未設定repoからvault内の既存IDへ接続しようとすると、別repoのknowledge混在を防ぐためsetupは拒否されます。同じproduct repoのcloneでは、version管理された既存 `.refinery.yaml` を引き継ぎます。

以下の例は対象repoのrootで実行し、その絶対パスを一度だけ取得します。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

```yaml
schema_version: 2
project_id: my-project
enabled: true
```

## 無効化

```bash
knowledge-refinery project disable --target "$PROJECT_ROOT"
```

無効化は可逆的です。`enabled: false` を保持し、managed AGENTS blockと任意の `.refinery` symlinkを解除しますが、中央vaultのproject領域は削除しません。repo-scoped MCP toolsは `project_path` から設定を読み、無効repoの検索・書き込みを拒否します。

disabledは故障ではなく利用者が選んだ正常なopt-outです。Skillやエージェントは、検索・記録依頼を満たすためだけに暗黙でenableしてはいけません。再有効化は利用者が明示的に依頼または確認した場合だけ行います。

## 再有効化

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

active vault以外を明示するときは `--vault` を付けます。閲覧symlinkも復帰する場合は `--link` を付けます。

## 状態確認

```bash
knowledge-refinery project status --target "$PROJECT_ROOT"
knowledge-refinery project status --target "$PROJECT_ROOT" --json
```

JSONの `state`、`ready`、`enabled`、`active_vault`、`vault_registered`、`managed_guidance`、`link_state` をautomationの安定契約として使えます。
