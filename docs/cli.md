# CLIリファレンス

## vault

```text
knowledge-refinery vault init --root PATH [--force]
knowledge-refinery vault configure --root PATH
```

`init` はmarkerと基本layoutを作成し、active vaultも更新します。`configure` は既存vaultをactiveにします。

## project lifecycle

```text
knowledge-refinery project setup --target PATH --vault PATH [--project-id SLUG] [--link] [--agents] [--lang jp|en] [--filename AGENTS.md|CLAUDE.md]
knowledge-refinery project enable --target PATH [--vault PATH] [--link] [--lang jp|en]
knowledge-refinery project disable --target PATH
knowledge-refinery project status --target PATH [--json]
knowledge-refinery doctor --target PATH [--mcp-version VERSION] [--json]
```

`project setup` はデフォルトではrepository guidanceを変更しません。`--agents` を指定した場合だけ、`--filename` で選んだファイルへmanaged blockを追記します。既定のファイルは `AGENTS.md`、言語は `jp` です。

MCP接続後は `refinery_info.version` を `doctor --mcp-version` へ渡すと、PATH上CLIとPlugin内MCPのrelease driftも機械的に検出します。

## experience

```text
knowledge-refinery experience upsert --project PATH --title TEXT --purpose TEXT [options]
knowledge-refinery experience search [TERMS...] --project PATH [filters]
```

主なupsert optionは `--status`、`--experience-id`、`--tag`、`--evidence`、`--related-experience`、`--supersedes`、`--confidence`、`--body`、`--body-file` です。filenameはIDから一意に生成されます。CLIのevidenceは `file:path`、`untracked:path`、`git:commit:path`、`mlflow:uri`、`url:uri`、`external:uri` を受けます。

## memory

```text
knowledge-refinery memory upsert --project PATH --title TEXT --summary TEXT --source-experience ID [options]
knowledge-refinery memory search [TERMS...] --project PATH [filters]
```

project memoryのsourceは現在projectのexperience ID、`--shared` で作るshared memoryのsourceは `project-id/experience-id` 形式を少なくと2件、2 projectから指定します。

memoryのfilenameはIDから一意に生成されます。既存memoryを更新する場合は、MCPの `refinery_get_memory` または対象headerから取得したrevisionを `--expected-updated-at` へ渡します。revisionなしの上書きとstale revisionは拒否されます。

## 安定出力

automationは `project status --json` と `doctor --json` を使ってください。エラーはstderrとnon-zero exit codeで返ります。
