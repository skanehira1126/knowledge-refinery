# knowledge-refinery

Codexで得た開発経験を、複数のプロジェクトから再利用できる形で残すためのPluginです。
経験とそこから抽出した原則は、プロダクトrepoとは別のローカル中央vaultに保存します。
vaultは通常のfilesystem directoryであり、履歴を残す場合は別途Gitを初期化して運用します。

```text
Codex Plugin ── MCP ── 中央vault
      │                 ├─ knowledge-tags.yaml（説明を追加した場合）
      │                 ├─ projects/<project-id>/project.yaml
      │                 ├─ projects/<project-id>/{experiences,memory}/
      │                 └─ shared/memory/
      └─ 利用repoの .refinery.yaml でON/OFF
```

## 必要なもの

- CodexまたはChatGPT desktop app
- Python 3.11以上
- `uv`
- Git（中央vaultに履歴を残す場合）

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

# 履歴を残す場合。vault initだけではGit repositoryになりません
git -C "$REFINERY_VAULT" init
```

CLIとMCPはファイルを保存しますが、`git init`、commit、push、backupは自動では行いません。

## repoを登録する（repoごとに1回）

導入したいrepoの中で実行します。

> **注意:** `project-id` は一度登録すると変更できません。未設定repoを既存IDへ登録する操作は、別repoのknowledge混在を防ぐため拒否されます。人間またはエージェントが候補を確認し、入力ミスのない一意な名前であることを確認してから実行してください。

```bash
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project \
  --project-name "My Project" \
  --summary "プロジェクトの目的を一文で記述" \
  --tag backend \
  --technology Python

knowledge-refinery doctor --target "$PROJECT_ROOT"
```

`doctor` に `ok: yes` と表示されたら準備完了です。`project setup` はrepoに
`.refinery.yaml` を作り、中央vaultのproject領域と `project.yaml` を用意します。
`project.yaml` はproject ID、名前、概要、検索用tag、利用技術を保持し、
`refinery_list_projects`、`refinery_get_project_metadata`、
`refinery_update_project_metadata` から参照・更新できます。Knowledge Refineryの
共通ルールも `AGENTS.md` へ追記する場合だけ、setupに `--agents` を付けてください。
doctorはvault schema、書き込み可能性、knowledge文書、ローカルMCP runtimeを検査します。
Codex側のPlugin登録状態はPlugin settingsで確認してください。

`project setup --vault` は、指定したvaultをユーザー全体のactive vaultにも設定します。
現在のactive vaultと異なる場合は、他repoや別taskのMCP検索先も変わるため、切り替えを
確認してから実行してください。設定済みrepoで明示したproject metadataが現在値と異なる場合、
setupの再実行は差分を黙って無視せず拒否します。表示された案内に従い
`project metadata update`を使います。
vault markerとgitignore済みの`.refinery.local.yaml`には同じ不変`vault_id`が保存され、
version管理可能な`.refinery.yaml`へ個人のvault identityを混ぜずに、active vault切替後の
誤接続を拒否します。

データ分析やアプリケーション開発など、作業内容に合わせた追加ルールは
[AGENTS.md追記サンプル](docs/agents-guidance-examples.md)を参照してください。

## 利用モードを選ぶ

Knowledge Refineryには2つの使い方があります。

- **明示呼出モード:** setupを既定のまま実行し、必要なtaskで`$refinery-experience`、
  `$refinery-memory`などを明示して依頼します。
- **自動運用モード:** setupへ`--agents`を付け、managed guidanceをrepoへ追加します。
  通常の開発taskでも、作業開始時の検索と終了前の記録判断をエージェントへ指示します。

「登録したrepoで新しいCodex taskを開くだけ」で運用できるのは自動運用モードです。
明示呼出モードでは、たとえば次のように依頼します。

```text
Knowledge Refineryからこの設計判断に関係するmemoryとexperienceを検索してください。
今回はvaultへ書き込まないでください。
```

setup、記録、memory抽出、診断のコピー可能な依頼例と、書き込み前に確認する操作は
[エージェントへの頼み方](docs/agent-workflow.md)を参照してください。

## 普段の使い方

PluginのSkillsとMCPが、作業開始時の検索、意味のある試行や失敗の記録、複数の経験からの
memory抽出を支援します。検索と診断は読み取りです。Experienceとproject memoryの記録は
明示依頼または自動運用のルールに基づいて行い、shared memoryの新規作成、大幅な書き換え、
削除は候補と影響を提示して利用者が確認してから行います。
ExperienceとmemoryのKnowledge tagは`/`区切りの最大3階層で、上位tagを指定すると
配下tagも検索できます。記録前に`refinery_browse_knowledge_tags`でrootから1階層ずつ
既存tagと説明・利用件数を確認でき、`refinery_search_knowledge_tags`ではtag pathと説明を
語句検索できます。説明は`refinery_update_tag_description`で中央taxonomyへrevision付きで
保存します。詳細は[ナレッジモデルと検索](docs/knowledge-model.md)を参照してください。

状態確認や一時的なON/OFFはCLIから行えます。

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
knowledge-refinery project status --target "$PROJECT_ROOT"
knowledge-refinery project disable --target "$PROJECT_ROOT"
knowledge-refinery project enable --target "$PROJECT_ROOT"
```

`disable` しても中央vaultの記録は削除されません。
disableは既存のmanaged guidanceを削除します。再有効化後も自動運用へ戻す場合は
`project enable --agents`、明示呼出モードで戻す場合は`project enable`を使います。

project metadataを更新する場合は、先に `refinery_get_project_metadata` で取得した
`updated_at` を `refinery_update_project_metadata.expected_updated_at` へ渡します。
変更するfieldだけを指定し、省略したfieldは保持されます。`tags: []` または
`technologies: []` を明示した場合だけ、そのlistを空にします。

既存experienceを更新する場合は、先に `refinery_get_experience` で取得した
`updated_at` を `refinery_record_experience.expected_updated_at` へ渡します。memoryと同様に、
revisionなしまたは古いrevisionでの上書きは拒否されます。

Experience、memory、project metadata、tag説明へsecret、credential、token、個人情報、
顧客データを保存しないでください。logやerror messageは機密値を除去し、vaultをcommitまたは
pushする前に差分を確認します。

## 更新

PluginとCLIを同じリリースへ更新し、新しいtask/sessionを開きます。

```bash
codex plugin marketplace upgrade knowledge-refinery
uv tool upgrade knowledge-refinery
```

## 詳細情報

- [Web版ドキュメント](https://skanehira1126.github.io/knowledge-refinery/)
- [導入手順](docs/getting-started.md)
- [エージェントへの頼み方](docs/agent-workflow.md)
- [ナレッジモデルと検索](docs/knowledge-model.md)
- [CLIリファレンス](docs/cli.md)
- [ナレッジ運用](docs/knowledge-operations.md)
- [仕組みとデータ配置](docs/architecture.md)
- [トラブルシューティング](docs/troubleshooting.md)
- [開発者向けガイド](docs/development.md)

開発時の検証は `bash scripts/validate.sh` でまとめて実行できます。
