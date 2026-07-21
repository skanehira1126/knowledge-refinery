# CLIリファレンス

## vault

```text
knowledge-refinery vault init --root PATH [--force]
knowledge-refinery vault configure --root PATH
```

`init` はmarkerと基本layoutを作成し、active vaultも更新します。`configure` は既存vaultをactiveにします。
vaultはfilesystem directoryであり、どちらも`git init`、commit、push、backupを実行しません。
active vaultはユーザー全体で1つなので、切り替えると他repoや別taskのMCP検索先も変わります。
`vault init --force`は不変`vault_id`を保持しますが、vault直下のmanaged README/AGENTS templateを
file単位で上書きします。local editsとGit差分を確認したうえで明示的に使います。

## project lifecycle

```text
knowledge-refinery project setup --target PATH --vault PATH [--project-id SLUG] [--project-name TEXT] [--summary TEXT] [--tag TEXT] [--technology TEXT] [--link] [--agents] [--lang jp|en] [--filename AGENTS.md|CLAUDE.md]
knowledge-refinery project enable --target PATH [--vault PATH] [--link] [--agents] [--lang jp|en] [--filename AGENTS.md|CLAUDE.md]
knowledge-refinery project disable --target PATH
knowledge-refinery project status --target PATH [--json]
knowledge-refinery project metadata show --target PATH [--json]
knowledge-refinery project metadata update --target PATH [--name TEXT] [--summary TEXT] [--tag TEXT | --clear-tags] [--technology TEXT | --clear-technologies] --expected-updated-at TIMESTAMP [--json]
knowledge-refinery doctor --target PATH [--mcp-version VERSION] [--json]
knowledge-refinery tag browse --project PATH [--parent TAG] [--all-projects]
knowledge-refinery tag search TERMS... --project PATH [--all-projects]
knowledge-refinery tag describe --project PATH --tag TAG --description TEXT [--expected-updated-at TIMESTAMP]
```

`project setup`は中央vaultへ`project.yaml`を必ず作成します。名前、概要、検索用tag、利用技術は
setup optionで指定できます。project IDを省略するとrepository directory名をlowercase slug化し、
空白、dot、underscore等をhyphenへ揃えます。slugを生成できない名前では`--project-id`を要求します。
デフォルトではrepository guidanceを変更しません。`--agents`を指定した場合だけ、`--filename`で
選んだfileへmanaged blockを追記します。既定は`AGENTS.md`、言語は`jp`です。未設定repoから
既存の`project-id`への登録は、別repoのdata混在を防ぐため拒否されます。

`project-id`は登録後に変更できません。未設定repoでは候補を確認してから実行します。
setupの`--vault`は指定vaultをactive vaultにも設定します。現在値と異なる場合はユーザー全体の
検索先が変わります。設定済みrepoで明示metadataが現在値と異なる場合、setupは差分を拒否し、
`project metadata update`を案内します。
新規setupはvault markerとgitignore済み`.refinery.local.yaml`へ同じ不変`vault_id`を保存します。
version管理可能な`.refinery.yaml`には個人のvault identityを入れません。statusの
`configured_vault_id`、`active_vault_id`、`vault_match`で誤接続を機械的に検出できます。

`project enable`は既定ではmanaged guidanceを追加しません。自動運用モードへ戻す場合だけ
`--agents`を指定します。`project disable`は既存managed blockを削除し、block外の利用者記述と
中央vaultのknowledgeを保持します。

metadata更新は `show` の `updated_at` を `update --expected-updated-at` に渡します。指定したfieldだけを更新し、省略fieldは保持します。tagまたはtechnologyを空にする場合は `--clear-tags`、`--clear-technologies` を明示します。revisionなし、古いrevision、変更fieldなしの更新は拒否されます。tagはlowercase kebab-caseで指定します。

`doctor` はactive vaultのschema、書き込み可能性、全knowledge文書、ローカルMCP runtime、project登録を検査します。MCP接続後は `refinery_info.version` を `doctor --mcp-version` へ渡すと、PATH上CLIと実際に接続されたPlugin内MCPのrelease driftも機械的に検出します。Codex側のPlugin登録状態そのものはCLI単独では確認できません。

disabledはhealthy opt-outとして扱うため、disabledであることだけを理由にdoctor全体を失敗させません。
`doctor --json`はvalidationで見つかった各文書の`path`と`error`を含みます。

## repo path option

既存のcanonical optionは、project lifecycleとdoctorでは`--target`、experience、memory、tagでは
`--project`です。移行やエージェント実行時の取り違えを避けるため、repo-scoped commandは
どちらの名前もaliasとして受け付けます。例:

```bash
knowledge-refinery project status --project "$PROJECT_ROOT"
knowledge-refinery experience search --target "$PROJECT_ROOT" "timeout"
```

## experience

```text
knowledge-refinery experience upsert --project PATH --title TEXT --purpose TEXT [options]
knowledge-refinery experience get SOURCE --project PATH
knowledge-refinery experience search [TERMS...] --project PATH [filters]
knowledge-refinery experience delete ID --project PATH --expected-updated-at REV [--confirm]
```

主なupsert optionは`--status`、`--experience-id`、`--tag`、`--evidence`、
`--related-experience`、`--supersedes`、`--confidence`、`--body`、`--body-file`、
`--expected-updated-at`です。更新時の省略optionは現在値を保持します。listのclearは
`--clear-tags`、`--clear-evidence`、`--clear-related-experiences`、`--clear-supersedes`、
confidenceのclearは`--clear-confidence`を使います。filenameはIDから一意に生成されます。
CLIのevidenceは`file:path`、`untracked:path`、`git:commit:path`、`mlflow:uri`、`url:uri`、
`external:uri`を受けます。`experience get`はheader・body・vault相対pathをJSONで返します。
`experience delete`は`--confirm`なしではdry-runです。revisionが一致し、memoryや他experienceからの
参照がなく、vault内knowledgeをvalidationできる場合だけ`--confirm`付き実行が削除します。

Experienceとmemoryの`--tag`は`/`区切りの最大3階層です。searchで`--tag domain/ml`を
指定すると、`domain/ml`と`domain/ml/feature-selection`の両方に一致します。

`tag browse`は`--parent`直下だけを説明・利用件数付きのJSONで返します。`--parent`を省略して
rootから開始し、必要な枝を順に辿ります。`tag search`はtag pathと説明をAND条件で検索します。
どちらも既定では現在projectとshared memoryを集計し、`--all-projects`で全projectへ広げます。

`tag describe`は説明を中央vaultのtaxonomyへ保存します。最初の登録後は`tag browse`または
`tag search`が返した`taxonomy_updated_at`を`--expected-updated-at`へ指定します。

既存experienceを更新する場合は、直前に取得したheaderの `updated_at` を `--expected-updated-at` へ渡します。revisionなしの上書きとstale revisionは拒否されます。

## memory

```text
knowledge-refinery memory upsert --project PATH --title TEXT --summary TEXT --source-experience ID [options]
knowledge-refinery memory get MEMORY_ID --project PATH [--scope project|shared] [--project-id ID]
knowledge-refinery memory search [TERMS...] --project PATH [filters]
knowledge-refinery memory delete MEMORY_ID --project PATH --expected-updated-at REV [--confirm]
```

project memoryのsourceは現在projectのexperience ID、`--shared` で作るshared memoryのsourceは `project-id/experience-id` 形式を少なくと2件、2 projectから指定します。

memoryのfilenameはIDから一意に生成されます。既存memoryを更新する場合は、`memory get`または
MCPの`refinery_get_memory`から取得したrevisionを`--expected-updated-at`へ渡します。
省略したsource/tag/confidenceは保持し、`--clear-tags`と`--clear-confidence`だけが明示clearです。
revisionなしの上書きとstale revisionは拒否されます。

Memoryの`--status`は`active`、`superseded`、`retracted`です。後継へ置き換える場合は、後継を
activeで先に作成し、旧memoryへ`--status superseded --superseded-by NEW_ID`を指定します。
通常の`memory search`はactiveだけを返し、`--status superseded`または`--status retracted`を
明示すると廃止済みを検索できます。`memory delete`も既定はdry-runで、他memoryの
`superseded_by`から参照されている場合は削除しません。

## 安定出力

automationは `project status --json` と `doctor --json` を使ってください。未設定、不正、または有効だが利用準備が整っていないproject statusはnon-zeroを返します。意図的なdisabledは正常状態として0を返します。
doctorのJSONでは、全体の`ok`だけでなく`project.state`とvalidation errorsも確認してください。
