# knowledge-refinery

Codexで得た開発経験を、複数のプロジェクトから再利用できる形で残すためのPluginです。
経験とそこから抽出した原則は、プロダクトrepoとは別の中央vaultに保存します。

```text
Codex Plugin ── MCP ── 中央vault
      │                 ├─ projects/<project-id>/
      │                 └─ shared/memory/
      └─ 利用repoの .refinery.yaml でON/OFF
```

## 必要なもの

- CodexまたはChatGPT desktop app
- Python 3.11以上
- `uv`
- Git（中央vaultの履歴管理に推奨）

## インストール（ユーザーごとに1回）

Pluginをmarketplaceへ追加します。

```bash
codex plugin marketplace add skanehira1126/knowledge-refinery
```

Codexの `/plugins`、IDEのPlugin settings、またはdesktop appのPlugin directoryで
`knowledge-refinery` をインストールします。続けて、Skillsが使うCLIを追加します。

```bash
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
```

Pluginを有効にするため、新しいtask/sessionを開いてください。

## 中央vaultを作る（ユーザーごとに1回）

中央vaultは、利用するプロダクトrepoと同一または親子関係にならない場所へ作成してください。

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
knowledge-refinery vault init --root "$REFINERY_VAULT"

# 履歴を残す場合（推奨）
git -C "$REFINERY_VAULT" init
```

CLIとMCPはファイルを保存しますが、Gitのcommitやpushは自動では行いません。

## repoを登録する（repoごとに1回）

導入したいrepoの中で実行します。`project-id` は他のrepoと重複しない、変更しない名前にしてください。

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project

knowledge-refinery doctor --target "$PROJECT_ROOT"
```

`doctor` に `ok: yes` と表示されたら準備完了です。`project setup` はrepoに
`.refinery.yaml` とmanaged AGENTS blockを作り、中央vaultにプロジェクト領域を用意します。

## 普段の使い方

登録したrepoで新しいCodex taskを開くだけです。PluginのSkillsとMCPが、作業開始時の検索、
意味のある試行や失敗の記録、複数の経験からのmemory抽出を支援します。

状態確認や一時的なON/OFFはCLIから行えます。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
knowledge-refinery project status --target "$PROJECT_ROOT"
knowledge-refinery project disable --target "$PROJECT_ROOT"
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

`disable` しても中央vaultの記録は削除されません。

## 更新

PluginとCLIを同じリリースへ更新し、新しいtask/sessionを開きます。

```bash
codex plugin marketplace upgrade knowledge-refinery
uv tool upgrade knowledge-refinery
```

## 詳細情報

- [Web版ドキュメント](https://skanehira1126.github.io/knowledge-refinery/)
- [導入手順](docs/getting-started.md)
- [CLIリファレンス](docs/cli.md)
- [仕組みとデータ配置](docs/architecture.md)
- [トラブルシューティング](docs/troubleshooting.md)
- [開発者向けガイド](docs/development.md)

開発時の検証は `bash scripts/validate.sh` でまとめて実行できます。
