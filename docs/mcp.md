# MCP tools

Pluginはローカルstdio MCPを起動します。repo-scoped toolsには `.refinery.yaml` の `project_id` ではなく、現在repoの絶対パスを `project_path` として渡します。serverが `project_id` と `enabled` を検証します。

| Tool | 用途 | repo gate |
|---|---|---|
| `refinery_list_projects` | active vaultのproject ID一覧 | 管理tool |
| `refinery_info` | MCP package/schema version | 管理tool |
| `refinery_search_experiences` | experienceの構造化/全文検索 | `project_path` |
| `refinery_get_experience` | experience IDまたは`project-id/experience-id`の本文取得 | `project_path` |
| `refinery_record_experience` | experienceの作成・revision付き更新 | `project_path` |
| `refinery_search_memory` | project/shared memory検索 | `project_path` |
| `refinery_get_memory` | scopeとIDを指定したmemory本文取得 | `project_path` |
| `refinery_record_memory` | project/shared memoryの作成・revision付き更新 | `project_path` |
| `refinery_validate` | active vaultのYAMLとprovenance検証 | 管理tool |

## 検索スコープ

デフォルトは現在projectです。`all_projects: true` は判断が汎用化できる場合だけ使います。memory検索ではshared memoryも対象です。

shared memoryの根拠を読むときは `refinery_get_experience(project_path, "project-id/experience-id")` を使います。experienceまたはmemoryを更新するときは、直前の取得結果にある `updated_at` をそれぞれ `refinery_record_experience.expected_updated_at`、`refinery_record_memory.expected_updated_at` へ渡します。不一致は競合として拒否されます。record toolの戻り値にも次回更新用の `updated_at` が含まれます。

検索は破損文書を隔離して正常文書を返します。破損文書のpathと理由は管理tool `refinery_validate` で確認します。IDを指定するget toolは対象ファイルを直接読み、対象自身が不正な場合はエラーを返します。

`refinery_info.version` はMCPを提供するPlugin側packageのversionです。PATH上CLIの `knowledge-refinery doctor --mcp-version VERSION` へ渡し、不一致なら両方を同じreleaseへ更新します。

## 拒否条件

- `.refinery.yaml` がない。
- schemaまたはproject IDが不正。
- `enabled: false`。
- active vaultにproject領域がない。
- memoryのsource experienceが実在しない。
- shared memoryの根拠が2 project未満。
