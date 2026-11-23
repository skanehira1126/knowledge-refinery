# CLIリファレンス

## vault

```text
knowledge-refinery vault init --root PATH [--force]
knowledge-refinery vault configure --root PATH
knowledge-refinery vault status [--target PATH] [--json]
```

`init` はmarkerと基本layoutを作成し、active vaultも更新します。`configure` は既存vaultをactiveにします。
vaultはfilesystem directoryであり、どちらも`git init`、commit、push、backupを実行しません。
`init`はvaultの`.gitignore`へ`/.obsidian/`を追加し、既存のignore設定は保持します。
active vaultはユーザー全体で1つなので、切り替えると他repoや別taskのMCP検索先も変わります。
`vault init --force`は不変`vault_id`を保持しますが、vault直下のmanaged README/AGENTS templateを
file単位で上書きします。local editsとGit差分を確認したうえで明示的に使います。

`status`は開いたvault（`--target`省略時は現在directory）のmarkerとactive vaultを照合する
読み取り専用の保守入口です。成功時はexit 0で`ready: true`、packageの`version`、
`vault_context: {vault_path, vault_id, project_id: null}`を返します。不正なmarker、ID欠落、
active vaultとのpath不一致はexit 2です。project登録やactive vaultの変更は行いません。
保守の検索・更新には[MCPのvault context](mcp.md#vault-maintenance)を使います。
既存のexperience／memory／tag CLIは引き続きrepo-scopedです。

## context

Codex・Claude Codeへ渡す短いMarkdownを、projectと配信先ごとに確認できます。配信先はイベント名と、
ツール実行前後の場合はツール名をスラッシュでつないで指定します。

| 配信先 | 届くタイミング | 載せる内容の例 |
|---|---|---|
| `UserPromptSubmit` | ユーザーが入力するたび | どの依頼の解釈にも関わる用語の意味 |
| `PreToolUse/Bash`、`PreToolUse/apply_patch` | 該当ツールの実行前 | 編集対象の生成元や、コマンドの入力に必要な前提 |
| `PostToolUse/Bash`、`PostToolUse/apply_patch` | 該当ツールの実行後 | コマンド結果の単位や、編集後の検証に使うデータ |
| `SubagentStart` | サブエージェントの開始時 | 委任先が調べる範囲と、参照先projectが持つ仕様 |

Claude Code の編集には `PreToolUse/Edit`、`PostToolUse/Edit`、ファイル書き込みには
`PreToolUse/Write`、`PostToolUse/Write` を使用します。各配信先は独立しています。
本文は中央vaultの `projects/<project_id>/context/<配信先>.md` に保存します。

```bash
knowledge-refinery context list
knowledge-refinery context show PreToolUse/Bash
knowledge-refinery context show PreToolUse/Bash --json
```

`list` は全配信先とrevisionを表示し、未設定の欄は `-` になります。`list --json` と
`show TARGET --json` は未設定のrevisionを `null` で返します。`show TARGET` は本文だけを表示します。
エージェントはMCPで本文を作成・更新・解除します。[hook本文のMCP操作](mcp.md#hook-context)

参照コマンドは現在地または `--project PATH` から同じrepo内の設定を探し、active vaultとの
紐付けを検証します。中央vaultを直接開いた保守では、`--vault "$VAULT_ROOT" --project-id "$PROJECT_ID"`
で登録済みprojectを指定できます。

新規開始・圧縮後は固定のCLIコマンド `context guidance-hook` がrepoの `.refinery.yaml` を確認し、
有効ならパッケージ同梱の日本語の運用指示を返します。MCP接続やactive vaultの設定は不要です。
表のイベントではホストの `mcp_tool` hookが作業ディレクトリと配信先を `refinery_deliver_context`
に渡します。サーバーがrepoとvaultの紐付けを照合し、該当する本文を追加contextとして返します。
未登録・無効なrepoや本文が空の配信先では、追加contextは入りません。

旧版で保存した `SessionStart/<source>` の本文は自動配信されません。以前の配信先を
`context show` または `refinery_get_context` に指定して内容を確認し、必要に応じて
該当する配信先へ移せます。旧本文の解除には `refinery_update_context` に現在のrevisionと `body: null` を渡します。

Codex CLIの `/hooks` で各hookを個別に信頼・無効化できます。デスクトップアプリでは `Settings → Hooks` で信頼状態を確認できます。`context list` と `show` はproject本文を対象にします。根拠を確認して本文を整える手順は
[refinery-curate-context](skills/refinery-curate-context.md)、イベントの入出力は
[Codex Hooks](https://learn.chatgpt.com/docs/hooks)を参照してください。

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

`project enable`で両方のhookが有効なrepoを再び配信対象にします。`--agents`はファイルへの追記に使います。
`project disable`は既存managed blockを削除し、block外の利用者記述と
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
```

主なupsert optionは`--status`、`--experience-id`、`--tag`、`--evidence`、
`--related-experience`、`--supersedes`、`--confidence`、`--body`、`--body-file`、
`--expected-updated-at`です。更新時の省略optionは現在値を保持します。listのclearは
`--clear-tags`、`--clear-evidence`、`--clear-related-experiences`、`--clear-supersedes`、
confidenceのclearは`--clear-confidence`を使います。filenameはIDから一意に生成されます。
CLIのevidenceは`file:path`、`untracked:path`、`git:commit:path`、`mlflow:uri`、`url:uri`、
`external:uri`を受けます。`experience get`はheader・body・vault相対pathをJSONで返します。

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
knowledge-refinery memory search [TERMS...] --project PATH [--include-archived] [filters]
knowledge-refinery memory archive MEMORY_ID --project PATH --reason TEXT --expected-updated-at TIMESTAMP [--superseded-by REF] [--shared]
```

project memoryのsourceは現在projectのexperience ID、`--shared` で作るshared memoryのsourceは `project-id/experience-id` 形式を少なくと2件、2 projectから指定します。

memoryのfilenameはIDから一意に生成されます。既存memoryを更新する場合は、`memory get`または
MCPの`refinery_get_memory`から取得したrevisionを`--expected-updated-at`へ渡します。
省略したsource/tag/confidenceは保持し、`--clear-tags`と`--clear-confidence`だけが明示clearです。
revisionなしの上書きとstale revisionは拒否されます。

`archive`は理由と任意の後継参照を旧memoryに保存し、更新したheaderをJSONで返します。後継の指定形式は[保存形式](schema.md#memory-archive)を参照してください。通常の`search`はactiveだけを返し、`--include-archived`では各行に状態も表示します。`get`はアーカイブ後も元のIDで本文とheaderを返します。

## 安定出力

automationは `project status --json` と `doctor --json` を使ってください。未設定、不正、または有効だが利用準備が整っていないproject statusはnon-zeroを返します。意図的なdisabledは正常状態として0を返します。
doctorのJSONでは、全体の`ok`だけでなく`project.state`とvalidation errorsも確認してください。

## handoff

引き継ぎ専用のcommand群です。通常のexperience／memory検索には含めません。
すべてJSONを返します。作成・アーカイブ・削除は`--project`（別名`--target`、既定は`.`）を受けます。
一覧・取得は`--project-id`でactive vaultを直接参照でき、ローカルrepoは不要です。
従来の`--project`も指定できますが、`--project-id`との併用はできません。

| Command | 引数 |
|---|---|
| `handoff create` | 必須: `--title`, `--goal`, `--done-when`と、非空の`--body`または`--body-file`。任意: `--id`, `--task-id`, `--supersedes`, `--expected-updated-at` |
| `handoff list` | 任意: `--project-id`または`--project`、`--include-archived`, `--task-id`, `--archived-before` |
| `handoff get <ID>` | 必須: `--project-id`または`--project`と、正確な引き継ぎID |
| `handoff archive <ID>` | 必須: `--expected-updated-at` |
| `handoff delete <ID>` | 必須: `--expected-updated-at`。archivedのみ削除可能 |

listは既定でactiveだけを作成日時の新しい順に返し、本文を含みません。
project指定の省略時は、現在repoに関係なくactive vaultの全projectを対象にします。
`--archived-before`はtimezone付きISO日時を受け、`--include-archived`が必須です。
その日時より前にアーカイブされた資料だけを候補として返し、削除はしません。
置き換え時のrevision、返却値、例は[引き継ぎガイド](handoffs.md)と
[MCPリファレンス](mcp.md#handoff-tools)を参照してください。

## issue

issueはactive vault全体で独立管理します。作業directoryによる暗黙のproject絞り込みはなく、
`--project`にはローカルパスではなく登録済みのproject IDを渡します。
project未所属・複数projectへの所属のどちらも可能です。
必要なら`REFINERY_VAULT`で操作先の既存vaultを明示できます。

```text
knowledge-refinery issue create --title TEXT [--description TEXT] [--done-when TEXT] [--project ID ...] [--tag TEXT ...] [--json]
knowledge-refinery issue list [--project ID] [--status STATUS] [--tag TEXT] [--json]
knowledge-refinery issue show ISSUE_ID [--json]
knowledge-refinery issue update ISSUE_ID --expected-revision N [--title TEXT] [--description TEXT] [--done-when TEXT] [--status STATUS] [--reason TEXT] [--add-project ID ...] [--remove-project ID ...] [--add-tag TEXT ...] [--remove-tag TEXT ...] [--json]
knowledge-refinery issue tag list [--project ID] [--json]
knowledge-refinery issue tag rename OLD NEW [--json]
knowledge-refinery issue tag remove TAG [--json]
```

作成結果の`id`（`issue-`に続く32桁のhex）を以降の操作に使用します。
`create`の初期状態は`backlog`、初期`revision`は`1`です。
`list`は更新日時の降順で返し、複数のfilterはAND条件です。完了・取消済みも含めます。
`list`は履歴を省略し、`show`は全変更履歴を返します。
出力は既定でも整形済みJSONで、`--json`は1行のJSONを返します。

状態は`backlog / ready / in_progress / blocked / done / cancelled`です。
任意の状態への変更・再開が可能ですが、変更には`--reason`が必要です。
`done`には空でない`done_when`も必要で、`--reason`に完了・検証の根拠を記載します。
CLIがテストや完了条件の充足を自動判定するわけではありません。

更新は`show`または`list`が返した最新の`revision`を`--expected-revision`に渡します。
競合時は終了コード`2`と`issue_revision_conflict`を返すので、読み直してから変更を再判断します。
指定していないfieldは保持し、`--description ""`で説明を空にできます。
`--add-project`・`--add-tag`は追加、`--remove-project`・`--remove-tag`は紐付け解除です。
同じ値の追加と解除を同時指定することはできません。

```bash
knowledge-refinery issue create --title "検索精度の改善" --project example \
  --tag 検索 --done-when "比較試験で改善を確認できる" --json
# 作成結果のidをISSUE_IDへ設定する
knowledge-refinery issue update "$ISSUE_ID" --expected-revision 1 \
  --status in_progress --reason "比較試験に着手" --json
knowledge-refinery issue list --project example --status in_progress --json
knowledge-refinery issue show "$ISSUE_ID" --json
```

タグは大文字・小文字を区別し、日本語も使えます。前後の空白と重複を除いて保存します。
`issue tag list`は現在使われているタグとissue件数を返します。
`rename`は全project・全状態のissueを対象とし、変更先が既存タグなら統合します。
`remove`は全issueからタグを解除しますが、issue本体と過去の変更履歴は削除しません。
どちらも変更されたissueのrevisionが増え、応答の`affected_issues`で対象IDを確認できます。
全体への操作なので、特定issueだけ変更する場合は`issue update`を使います。
未使用タグの登録や説明管理は提供しません。既存の`tag browse/search/describe`は
experience／memory用であり、issueタグには影響しません。

## session

ローカルのCodexログから解析JSONを作り、必要な記録を検索・表示します。出力はJSONです。
listは有効なRefinery登録設定を必要とします。ID・パス指定での抽出と解析JSONの操作は登録不要です。
MCP接続は不要です。レポート作成を依頼する場合は
[refinery-review-session](skills/refinery-review-session.md)を使ってください。

| コマンド | 入力 | 用途 |
| --- | --- | --- |
| `list` | ローカルログとタイトル索引 | タイトルや更新日時から対象チャットを選ぶ |
| `extract` | `/status` のセッションID、またはrollout JSONL | 本文と対応関係を解析JSONに保存する |
| `search` | 解析JSON | 条件に合う記録を探す |
| `show` | 解析JSON | 特定記録の前後と関連結果を読む |
| `stats` | 解析JSON | 呼び出し数・ツール別件数・警告を確認する |

### list：対象を選ぶ

```bash
knowledge-refinery session list \
  --title 'レビュー' \
  --updated-since 2026-11-07T00:00:00+09:00 \
  --updated-before 2026-11-08T00:00:00+09:00 --limit 3
```

現在の登録済みGitプロジェクトから、タイトルに「レビュー」を含み、日本時間11月7日に更新されたログを直近3件まで返します。
更新の基準はログファイルのmtimeです。
終了済みかどうかは別途確認してください。

| 引数 | 内容 | 既定 |
| --- | --- | --- |
| `--project PATH` | 対象の登録済みGit作業ディレクトリ | 現在のディレクトリ |
| `--title TEXT` | タイトルの部分一致。大文字・小文字を区別しない | 絞り込みなし |
| `--updated-since DATE` | 下限以上 | 下限なし |
| `--updated-before DATE` | 上限未満 | 上限なし |
| `--sessions-dir DIR` | 探索先を置き換える。複数指定可 | `CODEX_HOME/sessions` |
| `--limit N` | 返すチャット数。正の整数 | 20 |
| `--offset N` | 飛ばすチャット数。0以上 | 0 |

対象は現在のリポジトリと、その存在するworktreeです。
削除済みworktreeや所属を確認できないログは含めません。同じremoteの別cloneも別リポジトリとして扱います。

選んだ作業ツリーのルートには、有効な `.refinery.yaml` が必要です。
設定のないworktreeから実行する場合は、登録済みの作業ツリーを `--project` に指定してください。
未登録・無効の場合は、登録・有効化してから実行してください。

`CODEX_HOME` 未設定時は `~/.codex`。アーカイブは `--sessions-dir` で指定した場合だけ探します。
日付だけの指定はUTCの0時です。日時には `Z` または `+09:00` などのタイムゾーンが必要です。

タイトルは `CODEX_HOME/session_index.jsonl` の `thread_name` を使います。タイトルを取得できないチャットは
一覧で `title: null` になり、`--title` の一致対象から外れます。
`chats[].path` をextractへ渡します。同じチャットの複数ログがある場合は `paths` に並ぶため、対象を確認してください。
一覧は親チャット単位です。`total` と `next_offset` で続きの有無を、`skipped_files` で読取できなかった件数を確認できます。
limitは返却数の指定で、ファイル情報と先頭metadataの走査数は制限しません。

### extract：解析JSONを保存する

```bash
knowledge-refinery session extract --session-id SESSION_ID --output /tmp/analysis.json
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/analysis.json
```

| 引数 | 内容 |
| --- | --- |
| `--session-id ID` | Codexの `/status` に表示される共有セッションID |
| `path` | 起点チャットのrollout JSONL。`--session-id` とどちらか一方を指定 |
| `--output PATH` | 新規JSONの保存先。必須 |
| `--exclude-children` | 子孫を探さず、対象チャットだけ保存する |
| `--sessions-dir DIR` | IDでの親ログ・子孫ログの探索先を置き換える。複数指定可。既定は `CODEX_HOME/sessions` |

`--session-id` はログ先頭の `session_meta.payload.session_id` が完全一致する親ログを選びます。
親ログが見つからない場合や複数ある場合はエラーになります。ログのパスが分かる場合は直接指定できます。
既定では親子関係を確認できた子孫も、固有の `chat_id` を保持して保存します。
アーカイブを含めるには通常ログとアーカイブのディレクトリを `--sessions-dir` で指定します。
ID指定で親だけを保存するときも探索先を指定できます。パス指定で親だけを保存するときは `--sessions-dir` を省きます。
入力は変更せず、既存ファイル・symlinkへの上書きは拒否します。保存先はmode 0600で作成します。
本文は保存時に切り詰めません。解析JSONは匿名化されないため、公開・Git追跡の対象にしないでください。

### search / show / stats：保存したJSONを読む

```bash
knowledge-refinery session stats /tmp/analysis.json
knowledge-refinery session search /tmp/analysis.json --kind call --limit 10
knowledge-refinery session show /tmp/analysis.json --call-id call-001 --before 2 --after 2
```

3コマンドとも位置引数に解析JSONのパスを指定します。

| 指定 | 対象範囲 |
| --- | --- |
| 指定なし | rootと保存済みの子孫 |
| `--exclude-children` | rootだけ |
| `--chat-id ID` | 指定チャットとその子孫 |
| `--chat-id ID --exclude-children` | 指定チャットだけ |

searchとshowには次の絞り込み・表示引数があります。

| 引数 | 内容 |
| --- | --- |
| `--record-id ID` | 解析用記録ID。`<chat_id>:L<元行番号>` |
| `--call-id ID` / `--item-id ID` / `--turn-id ID` | 元ログの各ID |
| `--tool NAME` | ツール名の完全一致 |
| `--skill NAME` | Skill名または `plugin:skill` の完全一致 |
| `--skill-kind KIND` | Skill参照の種類。`--skill` が必要 |
| `--kind KIND` | call、result、messageなどの記録種別 |
| `--where PATH=VALUE` | 記録内の項目の値で完全一致。複数指定はAND |
| `--text TEXT` | 既定は大文字・小文字を区別する固定文字列の部分一致 |
| `--text-field PATH` | `--text` の対象を記録内の1項目に限定する |
| `--regex` | `--text` をPythonの正規表現として部分一致検索する |
| `--limit N` | 返す記録数。既定20、正の整数 |
| `--offset N` | 飛ばす件数。既定0、0以上 |
| `--max-chars N` | 各previewの文字数。既定2000、正の整数 |
| `--include-unparsed` | 未解析原文を検索・表示する |
| `--include-duplicates` | 重複記録も検索する |
| `--include-context` | 継承・帰属不明の記録も検索する |

ID指定は4種類のうち1つだけ使え、showでは必須です。他の条件はANDです。
show専用の `--before N`・`--after N` は、それぞれ前後0〜100記録を指定します。既定は0です。

たとえば、終了コードが1で、コマンドに `pytest` または `unittest` を含む実行記録は次のように探せます。

```bash
knowledge-refinery session search /tmp/analysis.json --kind execution \
  --where data.item.exit_code=1 --text-field data.item.command \
  --text '\b(pytest|unittest)\b' --regex
```

`PATH` は `records` の各記録を起点に、オブジェクトのキーを `.` でつなぎます。
項目が欠けている記録は条件に一致しません。`--where` の値には文字列・数値・`true`・`false`・`null` を使えます。
たとえば `--where data.item.exit_code=1` は数値、`--where 'data.item.process_id="1"'` は文字列を指定します。

`--text-field` は文字列をそのまま、文字列の配列を半角スペースで連結し、その他の値をJSON表記で検索します。
上の例ではコマンドの引数配列も検索でき、出力にだけ名前がある記録は除外されます。
本文は `--max-chars` で表示を切り詰める前に照合します。`unparsed` 配下を指定するには `--include-unparsed` が必要です。
不正な正規表現は終了コード2、有効な式で一致がなければ終了コード0で `total` が0になります。

`next_offset` で続きを取得し、previewの `truncated` が真なら `--max-chars` を増やします。
showの `related_truncated` が真なら、該当call IDやitem IDでsearchして関連結果を補います。
前後・関連記録は検索条件で絞られず、前後記録にはlimitも適用されません。
件数・状態・出力項目の意味は[解析JSONリファレンス](session-analysis.md)を参照してください。

### 終了コード

| コード | 意味・対応 |
| --- | --- |
| 0 | 処理成功。extractのwarningsとlistのskipped_filesも確認する |
| 2 | 引数・I/O・入力形式などのエラー。stderrの原因を解消して再実行する |

extractはmetadata欠落・競合する同一チャットのログ・読取中の更新をエラーにします。
不正JSONや未知の記録をwarnings付きで保存する場合もあるため、exit 0だけで完全取得とは判断しません。
