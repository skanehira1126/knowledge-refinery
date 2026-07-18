# 導入

## 1. Pluginを追加

=== "GitHub"

    ```bash
    codex plugin marketplace add skanehira1126/knowledge-refinery
    ```

=== "ローカルcheckout"

    ```bash
    PLUGIN_ROOT="$(pwd -P)"  # knowledge-refinery checkoutのrootで実行
    codex plugin marketplace add "$PLUGIN_ROOT"
    ```

Codex CLIの `/plugins`、IDEのPlugin settings、またはdesktop appのPlugin directoryで `knowledge-refinery` をinstallします。install後は新しいtask/sessionを開いてください。

## 2. CLIを追加

Skillがproject lifecycleを常に同じ手順で操作できるよう、CLIをPATHへinstallします。

=== "GitHub"

    ```bash
    uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
    ```

=== "開発checkout"

    ```bash
    PLUGIN_ROOT="$(pwd -P)"  # knowledge-refinery checkoutのrootで実行
    uv tool install --editable "$PLUGIN_ROOT"
    ```

## 3. 中央vaultを初期化

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"  # 任意の保存先へ変更可能
knowledge-refinery vault init --root "$REFINERY_VAULT"

# Git履歴を残す場合に明示実行
git -C "$REFINERY_VAULT" init
```

`vault init` はfilesystem上にvault markerと必要なディレクトリを作成し、そのvaultを
ローカルMCPのactive vaultにします。Git repositoryの初期化、commit、push、backupは
自動実行しません。Git履歴が必要な場合だけ、上の`git init`も実行します。

既存vaultへ切り替えるときは次を使います。active vaultはユーザー全体で1つのため、
切り替えると他repoや別taskのMCP検索先も変わります。

```bash
knowledge-refinery vault configure --root "$REFINERY_VAULT"
```

## 4. repoを登録

`project-id`は登録後に変更できません。エージェントへsetupを依頼する場合も、候補IDと
active vaultの切り替え有無を先に提示させ、確認してから実行します。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"  # 導入対象repoで実行
knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project \
  --project-name "My Project" \
  --summary "プロジェクトの目的を一文で記述" \
  --tag backend \
  --technology Python
```

`project-id`は小文字、数字、hyphenの安定したslugにします。省略時はrepository directory名から
候補をslug化しますが、不変IDなのでエージェント任せにせず確認することを推奨します。このコマンドは
`.refinery.yaml`と中央vaultのproject領域、`project.yaml`を整備し、`--vault`で指定した
vaultをactive vaultへ設定します。project metadataには名前、概要、検索用tag、利用技術が入り、
cross-project検索の範囲判断に使われます。vault markerとgitignore済みの
`.refinery.local.yaml`には同じ不変`vault_id`が保存され、version管理可能な`.refinery.yaml`へ
個人のvault identityを混ぜずに誤接続を拒否します。デフォルトでは`AGENTS.md`を作成・変更しません。

設定済みrepoでsetupを再実行し、明示した名前、概要、tag、technologyが現在値と異なる場合は、
指定値を黙って無視せずエラーになります。案内に従って、現在revisionを取得してから
`project metadata update`を使います。

Knowledge Refineryの共通ルールを`AGENTS.md`に追記し、自動運用モードにする場合は
`--agents`を指定します。既存の内容は保持され、管理対象のblockだけが追加または更新されます。

```bash
knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project \
  --agents
```

作業領域に固有のルールも追加したい場合は、[AGENTS.md追記サンプル](agents-guidance-examples.md)から必要なものを選んでください。

`--agents`を指定しない明示呼出モードでは、通常の開発taskが自動的にKnowledge Refineryを
使うとは限りません。必要なときにSkill名または目的を明示します。2つのモードと依頼例は
[エージェントへの頼み方](agent-workflow.md)を参照してください。

```text
$refinery-projectを使って、このrepoをKnowledge Refineryへ登録してください。
変更できないproject IDとactive vaultの切り替えを先に確認し、AGENTS.mdは変更しないでください。
```

## 5. 検証

```bash
knowledge-refinery project status --target "$PROJECT_ROOT" --json
knowledge-refinery doctor --target "$PROJECT_ROOT"
```

`doctor`の`ok: yes`を確認します。doctorはvault schema、書き込み可能性、knowledge文書、
ローカルMCP runtime、project登録を検査します。意図的にdisabledにしたrepoはhealthy opt-outとして
扱われ、repo-scoped toolsは利用できないことが`project.state`に表示されます。Codex側のPlugin
登録確認はPlugin settingsで行います。

MCP接続後は `refinery_info` の `version` を `MCP_VERSION` に設定し、doctorへ渡して一致を確認します。

```bash
knowledge-refinery doctor --target "$PROJECT_ROOT" --mcp-version "$MCP_VERSION"
```

一致しない場合はPluginとCLIの片方だけが更新されています。両方を同じreleaseへ揃えてから書き込みを開始します。

## 6. 最初のtask

自動運用モードでは新しいtaskを開いて通常の開発依頼を開始できます。明示呼出モードでは、
たとえば次のように読み取りだけを依頼します。

```text
Knowledge Refineryから今回の判断に関係するmemoryとexperienceを検索してください。
今回はvaultへ書き込まないでください。
```

Experienceやmemoryへはsecret、credential、token、個人情報、顧客データを保存しません。
logやerror messageは機密値を除去します。CLIとMCPはvault Gitを自動commitしないため、
記録後はvaultの差分を確認し、product repoとは別のcommitにします。
