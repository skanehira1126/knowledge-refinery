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
| `refinery_validate` | active vaultのYAMLとprovenance検証 | 管理tool |

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

tagを選ぶときは、最初に`refinery_browse_knowledge_tags`の`parent_tag`を省略してrootを取得し、
返された`has_children`を見ながら必要な枝だけを1階層ずつ辿ります。各tagには説明、直指定の
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
