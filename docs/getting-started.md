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
git -C "$REFINERY_VAULT" init
```

`vault init` はvault markerと必要なディレクトリを作成し、そのvaultをローカルMCPのactive vaultにします。既存vaultへ切り替えるときは次を使います。

```bash
knowledge-refinery vault configure --root "$REFINERY_VAULT"
```

## 4. repoを登録

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

`project-id` は小文字、数字、hyphenの安定したslugにします。このコマンドは `.refinery.yaml` と中央vaultのproject領域、`project.yaml` を冪等に整備します。project metadataには名前、概要、検索用tag、利用技術が入り、cross-project検索の範囲判断に使われます。デフォルトでは `AGENTS.md` を作成・変更しません。

Knowledge Refineryの共通ルールを `AGENTS.md` に追記する場合は `--agents` を指定します。既存の内容は保持され、管理対象のblockだけが追加または更新されます。

```bash
knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project \
  --agents
```

作業領域に固有のルールも追加したい場合は、[AGENTS.md追記サンプル](agents-guidance-examples.md)から必要なものを選んでください。

## 5. 検証

```bash
knowledge-refinery project status --target "$PROJECT_ROOT" --json
knowledge-refinery doctor --target "$PROJECT_ROOT"
```

`doctor` の `ok: yes` を確認し、新しいCodex taskで使用を開始します。doctorはvault schema、書き込み可能性、knowledge文書、ローカルMCP runtime、project登録を検査します。Codex側のPlugin登録確認はPlugin settingsで行います。

MCP接続後は `refinery_info` の `version` を `MCP_VERSION` に設定し、doctorへ渡して一致を確認します。

```bash
knowledge-refinery doctor --target "$PROJECT_ROOT" --mcp-version "$MCP_VERSION"
```

一致しない場合はPluginとCLIの片方だけが更新されています。両方を同じreleaseへ揃えてから書き込みを開始します。
