# MCP tools

Pluginはローカルstdio MCPを起動します。repo-scoped toolsには`.refinery.yaml`の`project_id`ではなく、
現在repoの絶対パスを`project_path`として渡します。serverが`project_id`、`enabled`、project
metadata、repoとactive vaultの`vault_id`一致を検証します。

| Tool | 用途 | repo gate |
|---|---|---|
| `refinery_list_projects` | active vaultのproject metadata一覧 | 管理tool |
| `refinery_info` | MCP package/schema versionとactive vault ID | 管理tool |
| `refinery_get_project_metadata` | 現在repoのproject metadata取得 | `project_path` |
| `refinery_update_project_metadata` | project metadataのrevision付き更新 | `project_path` |
| `refinery_browse_knowledge_tags` | 指定した親tagの直下を説明・利用件数付きで取得 | `project_path` |
| `refinery_search_knowledge_tags` | tag pathと説明を語句検索 | `project_path` |
| `refinery_update_tag_description` | tag説明のrevision付き登録・更新 | `project_path` |
| `refinery_search_experiences` | experienceの構造化/全文検索 | `project_path` |
| `refinery_get_experience` | experience IDまたは`project-id/experience-id`の本文取得 | `project_path` |
| `refinery_record_experience` | experienceの作成・revision付き更新 | `project_path` |
| `refinery_search_memory` | project/shared memory検索 | `project_path` |
| `refinery_get_memory` | scopeとIDを指定したmemory本文取得 | `project_path` |
| `refinery_record_memory` | project/shared memoryの作成・revision付き更新 | `project_path` |
| `refinery_create_handoff` | 引き継ぎsnapshotの作成と旧版のアーカイブ | `project_path` |
| `refinery_list_handoffs` | 引き継ぎmetadataの一覧、作業・archive日時で絞り込み | `project_path` |
| `refinery_get_handoff` | IDを指定した引き継ぎの取得 | `project_path` |
| `refinery_archive_handoff` | revisionを指定した引き継ぎのアーカイブ | `project_path` |
| `refinery_delete_handoff` | revisionを指定したarchived引き継ぎ1件の削除 | `project_path` |
| `refinery_validate` | active vaultのYAMLとprovenance検証 | 管理tool |
| `refinery_deep_search` | Codexによる検証済みvault snapshotの根拠付き検索 | `project_path`、任意公開 |

## Codexによるdeep search

`refinery_deep_search(project_path, question)`は、語句やfieldで絞る通常検索では答えにくい
比較、関連付け、矛盾の整理に生成AIを利用する読み取り専用toolです。knowledgeの作成や更新は
行いません。既定ではMCP tool一覧へ公開されず、次の操作後にMCPを再起動すると公開されます。

```bash
knowledge-refinery deep-search enable --model gpt-5.6-sol --reasoning-effort high
knowledge-refinery deep-search status --json
```

serverは中央vaultそのものをCodexの作業directoryにしません。現在repoを検証した後、全登録projectの
project metadata、schemaと参照が正しいexperience、project/shared memory、tag taxonomyだけを
一時snapshotへ複製します。`AGENTS.md`、Git metadata、product repoのfile、不正文書は含めません。
不正文書は結果の`limitations`へ除外理由として追加します。

Codex Execはsnapshot内でephemeralかつread-onlyで動き、user config、project rules、web検索、
tool shellへの環境変数継承を無効化します。質問はcommand lineではなくstdinで渡します。corpusの全内容をuntrusted evidenceと
扱うdeveloper instructionsを与え、manifestにないsource IDを返した結果はserver側で拒否します。
一時snapshotは成功・失敗・timeoutのいずれでも削除されます。MCPのtool timeoutは300秒、内部の
Codex実行timeoutは240秒です。

modelと任意のreasoning effortはuser configからserver側で読み、MCP呼び出し側からoverrideできません。
設定保存前に`codex debug models`のrefresh済みcatalogへslugと対応effortを照合します。effortが
未設定ならCodexのmodel既定値を使います。結果は`answer`、根拠ID付き
`findings`、`sources`、`contradictions`、`limitations`、設定された`model`を返します。
source IDは`experience:project/id`、`memory:project/id`、
`memory:shared/id`形式です。生成AIによる要約なので、重要な判断ではsource IDを通常のexact getへ
渡して原文を確認してください。

## 検索スコープ

デフォルトは現在projectです。まず現在project memoryとshared memory、次に現在project experienceを
検索します。ローカルの結果で足りない場合は、`refinery_list_projects`から選んだ
`project_ids`でbounded searchします。対象を合理的に限定できない場合だけ`all_projects: true`で
vault全体へ広げます。`project_ids`と`all_projects: true`は併用できず、併用時はエラーです。
memory検索ではどのproject scopeでもshared memoryを対象にします。

検索結果は共通して`project_id`、`id`、`title`、`kind`、`summary`、`status`、`scope`、
`confidence`、`tags`、`recorded_at`、`updated_at`、`path`を返し、対象外fieldはnullです。
Experienceの`summary`にはpurposeが入り、memoryだけが`scope`を持ちます。Memoryのexact getでは
pathを解析せず、`scope: project`なら結果の`project_id`を渡し、`scope: shared`なら
`project_id`を省略します。Shared memoryの更新では`shared: true`を維持します。

`statuses`は`completed`、`inconclusive`、`abandoned`、`superseded`、`confidences`は
`low`、`medium`、`high`、memoryの`scopes`は`project`、`shared`、`evidence_types`は
`file`、`git`、`mlflow`、`url`、`external`だけを受け付けます。未対応値やtypoは0件ではなく
入力エラーを返します。

Experienceとmemoryのtagは`/`区切りの最大3階層です。`tags: [domain/ml]`は
`domain/ml`と`domain/ml/feature-selection`の両方に一致します。複数tagはAND条件です。

tagは`refinery_search_knowledge_tags`の語句検索、または`refinery_browse_knowledge_tags`の階層参照で
意味を確認し、適切な既存tagを再利用します。確認済みのtagは、関連taxonomyが変わらなければ
再検索する必要はありません。階層を探索するときは`parent_tag`を省略してrootから始めるか、
既知の親tagを指定し、`has_children`を見ながら必要な枝を辿ります。各tagには説明、直指定の
`direct_count`、子孫を含む`document_count`、文書種別ごとの件数が含まれます。既定では現在
projectとshared memoryを集計し、`all_projects: true`で全projectへ広げます。

`refinery_search_knowledge_tags`の`terms`はtag pathと説明に対する大文字小文字を区別しない
AND検索です。taxonomyに定義済みの未使用tagと、文書で使用済みだが説明が未定義のtagを
どちらも返します。後者は`description: null`、`defined: false`です。

説明を保存するときはbrowseまたはsearchの`taxonomy_updated_at`を
`refinery_update_tag_description.expected_updated_at`へ渡します。taxonomyファイルがまだない
場合だけ省略できます。説明の更新はtagのrenameや文書側tagの変更を行いません。

shared memoryの根拠を読むときは `refinery_get_experience(project_path, "project-id/experience-id")` を使います。experienceまたはmemoryを更新するときは、直前の取得結果にある `updated_at` をそれぞれ `refinery_record_experience.expected_updated_at`、`refinery_record_memory.expected_updated_at` へ渡します。不一致は競合として拒否されます。record toolの戻り値にも次回更新用の `updated_at` が含まれます。

record toolの更新では、optional fieldの省略は現在値を保持します。空listを明示したfieldだけを
clearし、confidenceは`clear_confidence: true`でclearします。createとupdateのどちらでも、
secret、credential、access token、PII（個人情報）、顧客data、未redactの機密logを渡してはいけません。

Experience作成前に、内容を表す安定したlowercase slugを`experience_id`へ指定します。createの
responseが得られず結果が不明な場合は、そのIDをexact getし、必要ならID検索してから、存在しない
ことを確認した場合だけretryします。自動生成IDのまま同じcreateをblind retryしません。

Experienceのstatusとexperience/memoryのconfidenceは
[決定表](knowledge-model.md#status-confidence)に従います。Project memoryは原則2件以上の
反復または相補的なsourceを使います。明示依頼による1 sourceの例外はscopeと限界を明記し、
confidenceをhighにできません。Shared memoryの新規作成・昇格は、2 project以上のschema条件に加え、
候補、scope、限界、反例、confidence、source IDを提示して利用者の明示承認を得る必要があります。

project metadataを更新するときは、`refinery_get_project_metadata` または
`refinery_list_projects` が返した現在の `updated_at` を
`refinery_update_project_metadata.expected_updated_at` に渡します。変更fieldだけを指定し、
省略fieldは保持されます。`tags: []` または `technologies: []` は該当listの明示clearです。
tagはlowercase kebab-caseで目的・領域を表し、技術名は `technologies` だけに保存します。
名前、概要、tag、利用技術にはsecret、ローカル絶対path、未確認の推測を保存しません。

検索とtag集計は破損文書を隔離して正常文書を返します。破損したtaxonomyや文書のpathと理由は管理tool `refinery_validate` で確認します。IDを指定するget toolは対象ファイルを直接読み、対象自身が不正な場合はエラーを返します。

`refinery_info.version` はMCPを提供するPlugin側packageのversionです。PATH上CLIの `knowledge-refinery doctor --mcp-version VERSION` へ渡し、不一致なら両方を同じreleaseへ更新します。

## 拒否条件

- `.refinery.yaml` がない。
- schemaまたはproject IDが不正。
- `enabled: false`。
- active vaultにproject領域がない。
- project metadataが不正。
- memoryのsource experienceが実在しない。
- shared memoryの根拠が2 project未満。

## 引き継ぎ専用tools {#handoff-tools}

handoffは通常のナレッジ検索から分離し、現在projectに限定して操作します。
各toolは`project_path`から有効状態・vault binding・project metadataを検証します。
`refinery_info`は`handoff_schema_version: 1`も返します。

| Tool | 必須引数 | 任意引数 |
|---|---|---|
| `refinery_create_handoff` | `project_path`, `title`, `goal`, `done_when`, `body` | `handoff_id`, `task_id`, `supersedes`, `expected_updated_at` |
| `refinery_list_handoffs` | `project_path` | `include_archived=false`, `task_id`, `archived_before` |
| `refinery_get_handoff` | `project_path`, `handoff_id` | なし |
| `refinery_archive_handoff` | `project_path`, `handoff_id`, `expected_updated_at` | なし |
| `refinery_delete_handoff` | `project_path`, `handoff_id`, `expected_updated_at` | なし |

create/get/archiveは`{header, body, path}`を返し、pathはvault相対です。listは作成日時の新しい順に
`{header, path}`の配列を返し、本文は返しません。`task_id`は完全一致で絞り込みます。
`archived_before`はtimezone付きISO日時の排他的上限で、`include_archived: true`と併用すると
その日時より前にアーカイブした資料だけを返します。通常の一覧はactiveのみです。

createは既存IDを上書きしません。IDを省略すると生成しますが、応答不明時の照合のためSkillでは
保存前にIDを選びます。同じ作業にactive資料がある場合は`supersedes`でそのIDを指定し、
旧版の`header.updated_at`を`expected_updated_at`として渡します。`task_id`は旧版から継承します。
旧版指定なしの`expected_updated_at`、異なるtaskへの置き換え、archived資料の置き換えは拒否します。

archiveは本文を保持し、既にarchivedなら同じrevisionへの呼び出しは変更しません。
deleteはarchived資料だけを受け付け、`{deleted: true, project_id, handoff_id, path}`を返します。
古いrevision、未知のID、不正なschema、symlinkによる保存領域の転送は拒否します。
削除済みIDへの再実行は成功扱いにせず、存在確認して結果を判断します。

`refinery_validate`はhandoffのschema・配置・同じtaskのactive重複も検証します。
詳細と強制終了時の確認方法は[引き継ぎガイド](handoffs.md)を参照してください。
