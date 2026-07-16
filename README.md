# knowledge-refinery

複数プロジェクトの開発経験を、プロダクトGitと独立したローカル中央vaultへ保存するCodex Pluginです。PluginがSkillsとstdio MCPサーバーをグローバルに提供し、利用repoごとの `.refinery.yaml` で有効・無効を制御します。

```text
Global Codex Plugin → local MCP → central refinery Git
                                    ├─ projects/<project_id>/{experiences,evidence,memory}
                                    └─ shared/memory

Product repo → .refinery.yaml (project_id + enabled)
```

## 必要条件

- CodexまたはChatGPT desktop app
- `uv`
- Git（中央vaultの履歴管理に推奨）

## Pluginをインストール

リモートmarketplaceとして追加する場合:

```bash
codex plugin marketplace add skanehira1126/knowledge-refinery
```

開発checkoutをそのまま使う場合:

```bash
PLUGIN_ROOT="$(pwd -P)"  # knowledge-refinery checkoutのrootで実行
codex plugin marketplace add "$PLUGIN_ROOT"
```

Codexの `/plugins` またはdesktop appのPlugin directoryから `knowledge-refinery` をinstallし、新しいtaskを開いてください。PluginのMCPは配布済み `uv.lock` に従って依存関係を解決します。

Skillが定型作業に使うCLIもユーザー環境へ1度installします。

```bash
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
```

開発checkoutでは、同じ `PLUGIN_ROOT` を使って `uv tool install --editable "$PLUGIN_ROOT"` を実行します。

## 初期設定

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"  # 導入対象repoで実行
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"  # 任意の保存先へ変更可能

knowledge-refinery vault init --root "$REFINERY_VAULT"
git -C "$REFINERY_VAULT" init

knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project

knowledge-refinery doctor --target "$PROJECT_ROOT"
```

`project setup` は次のrepo設定とmanaged AGENTS blockを作成します。`.refinery` symlinkは必須ではなく、人間向けの閲覧が必要な場合だけ `--link` で作成します。

```yaml
schema_version: 2
project_id: my-project
enabled: true
```

## repo単位のオン・オフ

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
knowledge-refinery project disable --target "$PROJECT_ROOT"
knowledge-refinery project enable --target "$PROJECT_ROOT"
knowledge-refinery project status --target "$PROJECT_ROOT" --json
```

OFFでは `.refinery.yaml` を `enabled: false` のまま残し、managed AGENTS blockと任意symlinkのみ解除します。中央vaultのknowledgeは削除しません。MCPも `project_path` から設定を再読み込みし、disabled repoの操作を拒否します。

## 運用契約

- repo-scoped MCP toolsには現在repoの絶対パスを `project_path` として渡す。
- `enabled: false` は正常なopt-outであり、検索・記録要求から暗黙に再有効化しない。
- meaningfulな検証・比較・不採用判断・失敗は `refinery-experience` Skillで一つのexperienceにする。
- project memoryは同一projectの実在experienceを根拠にする。
- shared memoryは `project-id/experience-id` 形式の根拠を2件以上、2 project以上から指定する。
- shared memoryの作成前は `refinery_get_experience` で全根拠を読み、作成後は `refinery_get_memory` で読み戻す。
- 既存memoryの更新は読み取り時の `updated_at` を `expected_updated_at` として渡し、競合上書きを防ぐ。
- `refinery_info.version` を `knowledge-refinery doctor --mcp-version` へ渡し、不一致ならPlugin/CLIを同じreleaseへ更新する。
- プロダクトrepoとrefinery repoのcommit/PRを混ぜない。

managed blockのsource of truthは `src/knowledge_refinery/data/agents.jp.md` と `agents.en.md` です。

## 利用repoのAGENTS.mdサンプル

`project setup` / `project enable` が次の方針をmanaged blockとして同期します。

```markdown
## Knowledge Refinery

このリポジトリでは、開発中に得た再利用可能な経験をKnowledge Refineryで管理する。

- `.refinery.yaml` が `enabled: true` の場合だけ利用し、repo-scoped MCP toolsには現在repoの絶対パスを `project_path` として渡す。
- `enabled: false` は意図的なOFFとして扱い、検索や記録の依頼だけを理由に再有効化しない。再有効化は利用者の明示依頼または確認がある場合だけ行う。
- 作業開始時、判断に影響しそうな既存memoryとexperienceを検索する。
- meaningfulな検証、比較、不採用判断、失敗から知見を得た場合は `refinery-experience` skillを使う。
- experienceは目的、試したこと、分かったこと、微妙だった点、次の可能性を一つの記録にまとめる。
- 実装へ採用しなかったことや、evidenceがuntrackedであることを理由に記録を捨てない。
- evidenceを保存するためだけにプロダクトrepoへcommitしない。
- 複数experienceから繰り返し使える原則を抽出するときは `refinery-memory` skillを使う。
- project固有の原則はproject memory、複数projectで支持される原則だけをshared memoryへ保存する。
- 作業終了前に、今回の作業から記録すべきexperienceがないか確認する。
- 日次棚卸しでは `refinery-maintenance` skillを使う。
- プロダクトrepoとrefinery repoの変更を同じcommitやPRへ混ぜない。
```

## ドキュメント

Material for MkDocsでローカル表示できます。

```bash
uv run --extra docs mkdocs serve
```

詳細は [`docs/`](docs/index.md) の導入、CLI/MCPリファレンス、schema、Git運用、troubleshootingを参照してください。

## 開発検証

```bash
bash scripts/validate.sh
```
