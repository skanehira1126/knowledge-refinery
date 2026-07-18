# knowledge-refinery

Codexで得た開発経験を、複数のプロジェクトから再利用できる形で残すためのPluginです。
試行や失敗をexperienceとして記録し、そこから抽出した原則をmemoryとして、プロダクトrepoとは
別のローカル中央vaultへ保存します。

## はじめる

必要なものは、CodexまたはChatGPT desktop app、Python 3.11以上、`uv`です。

まずPluginとCLIをインストールします。

```bash
codex plugin marketplace add skanehira1126/knowledge-refinery
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
```

CodexのPlugin画面で`knowledge-refinery`をインストールし、新しいtask/sessionを開きます。

次に、knowledgeの保存先となる中央vaultを一度だけ作ります。

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
knowledge-refinery vault init --root "$REFINERY_VAULT"
```

Knowledge Refineryを使いたいrepoで、次を実行します。

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --agents

knowledge-refinery doctor --target "$PROJECT_ROOT"
```

project IDと表示名はrepoのdirectory名から自動設定されます。`--agents`は、通常の開発taskでも
Knowledge Refineryを利用するための管理対象ルールをrepoの`AGENTS.md`へ追加します。
`doctor`に`ok: yes`と表示されたら準備完了です。

新しいtaskを開き、いつもどおり開発を依頼してください。必要なknowledgeの検索と、作業後に
残す価値があるexperienceの記録判断をPluginが支援します。

## 主な機能

- 成功、失敗、不採用案をexperienceとして記録する
- experienceから再利用可能なproject memoryとshared memoryを抽出する
- 現在のrepoから、必要に応じて他repoのknowledgeまで検索する
- repoごとに利用を無効化・再有効化する
- 中央vaultを独立したGit repositoryとして履歴管理する

機能の使い分け、保存前の確認境界、データ構造は
[Web版ドキュメント](https://skanehira1126.github.io/knowledge-refinery/)で説明しています。

## 詳細情報

- [導入とオプション](docs/getting-started.md)
- [エージェントへの頼み方](docs/agent-workflow.md)
- [ナレッジモデルと検索](docs/knowledge-model.md)
- [repoの有効・無効](docs/project-lifecycle.md)
- [ナレッジ運用](docs/knowledge-operations.md)
- [CLIリファレンス](docs/cli.md)
- [仕組みとデータ配置](docs/architecture.md)
- [トラブルシューティング](docs/troubleshooting.md)

開発時の検証は`bash scripts/validate.sh`でまとめて実行できます。
