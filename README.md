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

すでにインストール済みのPluginとCLIを更新する場合は、次を実行します。

```bash
codex plugin marketplace upgrade knowledge-refinery
uv tool upgrade knowledge-refinery
```

CodexのPlugin画面で`knowledge-refinery`を再インストールし、新しいtask/sessionを開きます。

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

新しいtaskを開き、いつもどおり開発を依頼してください。設計判断・原因調査・手法比較など、
過去の知識が役立つ場面で検索し、単純なtypo・書式変更では省略します。再利用できる試行や
有用な失敗は、毎回の確認質問を挟まずexperienceとして保存し、保存結果まで確認します。
検索・診断・提案のみの依頼では書き込みません。

## 主な機能

- 成功、失敗、不採用案をexperienceとして記録する
- experienceから再利用可能なproject memoryとshared memoryを抽出する
- 現在のrepoから、必要に応じて他repoのknowledgeまで検索する
- 任意でCodexを使い、中央vaultの検証済みsnapshotから根拠付きの深い検索を行う
- repoごとに利用を無効化・再有効化する
- 中央vaultを独立したGit repositoryとして履歴管理する
- 特定の作業の状態をhandoffに保存し、新しいチャットで再評価して再開する

## 新しいチャットへ引き継ぐ

`$refinery-handoff`は明示呼び出し専用です。旧チャットで
「`$refinery-handoff`を使って、この作業の引き継ぎを保存してください」と依頼すると、
目的・完了条件・現在の成果物・確認済みの事実・未解決事項を保存し、引き継ぎIDと再開用の依頼文を返します。
新しいチャットでは、保存元の`project_id`と引き継ぎIDを指定して同Skillに再開を依頼します。
参照には保存元repoのローカルパスは不要です。MCPの`refinery_get_handoff(project_id, handoff_id)`で
取得でき、`refinery_list_handoffs(project_id=...)`でprojectを絞るか、省略してactive vaultの全projectを
一覧できます。CLIも`handoff get <ID> --project-id <project-id>`と`handoff list`に対応します。

handoffはprojectごとの専用領域に保存され、通常のexperience／memory検索やdeep searchには
含まれません。読み込みでは消費せず、新版への置き換えや明示された終了でアーカイブします。
自動期限・自動削除はなく、削除は指定したアーカイブ済みの資料だけを対象にします。
作成・再開・整理の手順とCLI例は[引き継ぎガイド](docs/handoffs.md)を参照してください。

機能の使い分け、保存前の確認境界、データ構造は
[Web版ドキュメント](https://skanehira1126.github.io/knowledge-refinery/)で説明しています。

## 詳細情報

- [導入とオプション](docs/getting-started.md)
- [エージェントへの頼み方](docs/agent-workflow.md)
- [利用repoのAGENTS.md追記サンプル](docs/agents-guidance-examples.md)
- [ナレッジモデルと検索](docs/knowledge-model.md)
- [repoの有効・無効](docs/project-lifecycle.md)
- [ナレッジ運用](docs/knowledge-operations.md)
- [CLIリファレンス](docs/cli.md)
- [MCP toolsとdeep search](docs/mcp.md)
- [仕組みとデータ配置](docs/architecture.md)
- [トラブルシューティング](docs/troubleshooting.md)

開発時の検証は`bash scripts/validate.sh`でまとめて実行できます。
