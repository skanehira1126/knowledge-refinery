# repoの有効・無効

repo側のsource of truthは `.refinery.yaml` です。
projectの説明情報は中央vaultの `projects/<project_id>/project.yaml` をsource of truthとします。

`project_id` は登録後に変更しません。未設定repoからvault内の既存IDへ接続しようとすると、別repoのknowledge混在を防ぐためsetupは拒否されます。同じproduct repoのcloneでは、version管理された既存 `.refinery.yaml` を引き継ぎます。

未設定repoをエージェントに登録させる場合は、immutableなproject ID候補を先に提示させ、
利用者が確認してからsetupします。`project setup --vault`は指定vaultをユーザー全体のactive
vaultにも設定するため、現在値と異なる場合は他repoや別taskへの影響も確認します。

以下の例は対象repoのrootで実行し、その絶対パスを一度だけ取得します。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

```yaml
schema_version: 2
project_id: my-project
enabled: true
```

version管理しない`.refinery.local.yaml`には中央vault markerの不変`vault_id`を保存します。
setupはこのlocal fileを`.gitignore`へ追加します。local bindingとactive vaultが一致しない場合は
`vault_match: false`となり、同じ`project_id`が存在してもreadyにはなりません。cloneは
version管理されたproject IDを引き継ぎ、各利用者が明示setupして自分のvaultへlocal bindします。

## 無効化

```bash
knowledge-refinery project disable --target "$PROJECT_ROOT"
```

無効化は可逆的です。`enabled: false`を保持し、既存のmanaged AGENTS blockと任意の
`.refinery` symlinkを解除しますが、中央vaultのproject領域は削除しません。repo-scoped MCP
toolsは`project_path`から設定を読み、無効repoの検索・書き込みを拒否します。managed block
以外の利用者記述は保持します。

disabledは故障ではなく利用者が選んだ正常なopt-outです。Skillやエージェントは、検索・記録依頼を満たすためだけに暗黙でenableしてはいけません。再有効化は利用者が明示的に依頼または確認した場合だけ行います。

## 再有効化

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

上のコマンドは明示呼出モードで再開し、managed guidanceを追加しません。自動運用モードへ
戻す場合だけ`--agents`を付けます。

```bash
knowledge-refinery project enable --target "$PROJECT_ROOT" --agents
```

active vault以外を明示するときは`--vault`を付けます。この指定はユーザー全体のactive vaultを
切り替えるため、影響を確認してから実行します。閲覧symlinkも復帰する場合は`--link`を付けます。

## 状態確認

```bash
knowledge-refinery project status --target "$PROJECT_ROOT"
knowledge-refinery project status --target "$PROJECT_ROOT" --json
```

JSONの`state`、`ready_for_tools`、`enabled`、`active_vault`、`configured_vault_id`、
`active_vault_id`、`vault_match`、`vault_registered`、`managed_guidance`、`link_state`を
automationの安定契約として使えます。
`project_metadata` には検証済みmetadata、`project_metadata_error` には読めない場合の理由が入ります。

disabledはhealthy opt-outなので`project status`はexit 0です。doctorもdisabled自体を破損として
扱いませんが、`enabled: false`の間はrepo-scoped toolsを利用できません。

## setupとmetadata更新

`project setup`は新規登録と不足layoutの整備に使います。設定済みrepoで、明示したname、
summary、tag、technologyが現在metadataと異なる場合、setupは差分を黙って無視せず拒否します。
metadataを変更する場合は`project metadata show`で`updated_at`を取得し、
`project metadata update --expected-updated-at ...`を使います。
