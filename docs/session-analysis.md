# セッション解析JSONとCLI

この文書はKnowledge Refineryが定義する解析用JSONの仕様です。Codexログの公開仕様ではありません。
元ログはJSONLのまま保持し、CLIが機械的に整理したJSONを解析Skillが読みます。
CLIはコードを実行せず、Skill遵守・作業の成功・改善先を評価しません。
MCPによるローカルセッション読取は行わず、vaultの設定・接続も不要です。

## 入力と保存

対象は`session_meta`を持つ単一チャットのrollout JSONLです。`codex exec --json`のイベントストリームや
アプリの要約JSONは別形式です。対応形式の判別をせずに混ぜません。

```bash
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/analysis.json
knowledge-refinery session extract /path/to/rollout.jsonl --include-children --output /tmp/tree.json
# 探索場所を指定する場合。複数指定可能
knowledge-refinery session extract /path/to/rollout.jsonl --include-children \
  --sessions-dir /path/to/sessions --sessions-dir /path/to/archived_sessions --output /tmp/tree.json
# 子のログを明示する場合。孫を含めるには途中の親も指定する
knowledge-refinery session extract /path/to/rollout.jsonl --child /path/to/child.jsonl \
  --output /tmp/selected.json
```

`--output`は必須です。本文を切り詰めず、既存ファイル・symlinkへの上書きを拒否し、
新規ファイルをmode 0600で作成します。標準出力は保存先・件数の短いJSONです。
入力は変更しません。保存されたJSONは匿名化済みではなく、公開・Git追跡の対象にしません。

識別できるreasoningレコード、analysis channel、暗号化内容は保存対象外です。
未知の構造も再帰的に既知のreasoningフィールドを除外します。不正JSON内にreasoning等の識別文字列がある
場合は原文全体を保存せず、位置と警告だけ残します。未知の命名や本文に埋め込まれた機密値を自動で
完全に識別する機能ではありません。未解析資料をモデルへ提示する前に内容を確認します。

成功はexit 0。不正JSON・未知構造は位置付きで保存し、warningsを返すため、成功が完全解析を意味しません。
metadataの欠落・親から継承したと確認できないチャットIDの混在、入力ファイルの読取中の変更、競合する同一チャットの複数ログ、
無関係な子ログ、I/O失敗、不正引数はexit 2です。複数ファイルは各ファイルの安定性を確認しますが、
全ファイルの同時刻スナップショットを保証しません。

## スキーマ

`format: knowledge-refinery.session-analysis`、`schema_version: 2`。
開発初期のschema 1から変更しています。旧JSONは再抽出が必要です。
保存時の`--max-chars`は廃止し、表示時だけ指定します。

| フィールド | 内容 |
|---|---|
| `root_chat_id` | 解析対象の親チャット固有ID |
| `chats` | チャット固有ID、共有session ID、親ID、agent path、Codex版、入力パス・SHA-256・bytes・行数 |
| `records` | チャットごとの元行順の記録。チャット間で時刻順に混ぜない |
| `calls` | 重複を除いた呼び出しと、結果・実行イベントへの参照 |
| `relations` | 重複、結果、実行イベント、明示的なプロセス参照の関係 |
| `skill_mentions` | Skill名・本文提供・パス参照の構文上の候補 |
| `child_links` | 起動呼び出し、子metadata、未取得・曖昧さの対応 |
| `warnings` | 対応不明、欠落、未知構造など。チャットと記録IDを含む |

### records

`record_id`は`<chat_id>:L<元行番号>`です。同じログの同じ位置では安定します。
ログの並べ替えや途中への行挿入に対しては安定しません。出典はsourceのSHA-256と併せて確認します。

| フィールド | 内容 |
|---|---|
| `chat_id`, `line`, `timestamp`, `ordinal` | 出典と元の順序情報。時刻の補完や推測はしない |
| `source_metadata` | 外側のmetadataを保持 |
| `ownership`, `ownership_basis` | local / context_onlyと、その帰属の根拠 |
| `kind` | metadata / context / message / call / result / execution / lifecycle / usage / unparsed / excluded |
| `source_type`, `source_subtype` | 元の外側・内側のtype |
| `turn_id`, `turn_id_basis` | 明示IDはexplicit、直前のターン文脈から補った場合はpreceding_context。未確定ならnull |
| `source_ids` | 元のitem IDとcall ID。未取得ならnull |
| `tool` | namespaceがあればnamespace.name、なければ呼び出し名。MCP実行イベントではserver/tool。他のイベントからツール名を推測しない |
| `data` | 既知のpayload。発言のrole・phase、引数・入力・結果、構造化された終了コード・状態などを保持 |
| `unparsed` | 未解析部分の元JSON文字列、理由、追加キーの位置、raw_exact |
| `duplicate_of` | 同じ記録の確実な重複なら代表record ID。それ以外はnull |

引数・結果の文字列は元の表現を保持し、コードとして実行しません。
非テキスト要素、入れ子の結果や環境情報などはJSONとして保持します。
未知のレコード種類・不正な既知レコードは`kind: unparsed`、`data: null`です。
既知envelopeの追加キーは既知部分を解析したうえで元JSONを`unparsed`へ保存します。
既知の引数・結果・content等の内部は不透明なデータとして保持し、独自の意味解析はしません。

`unparsed.raw_text`は原則として改行区切りを除く元の1行です。reasoning等を除去した場合は
除去後のJSON文字列となり`raw_exact: false`です。不正JSONは元文字列と警告を保持しますが、
除外対象を含むと判断した場合は`raw_text: null`です。通常の表示・本文検索では未解析原文を展開しません。

### 呼び出しと重複

各callには解析用`id`（request record ID + `:call`）、元の`call_id`、`chat_id`、`tool`、
`request_record`、`result_records`、`execution_records`、`link_status`を持たせます。

- 同一チャットのcall IDが一致し、呼出し種類とoutput種類が対応し、結果が呼出し後にある場合に接続します。
- 同じcall IDの呼出しが複数ある場合は曖昧とし、結果を推測で接続しません。
- 補足イベントは明示call ID、またはitem IDが呼出しのitem ID／call IDと一意に一致する場合だけ接続します。
  複数のIDが別々の呼出しを指す場合は曖昧とします。
- 時刻や本文が似ているだけでは統合しません。未対応の実行イベントと結果も保持します。
- 重複は同一チャット・同一ターン・同一item ID・同一種類・同一内容で確認します。
  発言の2表現はrole・phase・テキストが同じ場合に対応します。元記録は削除しません。
- call IDだけが同じ、またはコマンドだけが同じ場合は重複扱いにしません。再試行は別の呼出しです。
- ラッパー内のコードに書かれただけのツール呼出しを解析して実行回数に追加しません。
- exec_command/write_stdinの構造化された入出力に同じsession_idがある場合はprocess_referenceを付けます。
  非構造化テキストからIDを推測せず、この関係だけで完了や成功を判定しません。

link_statusはmatched / missing_result / ambiguousです。結果の存在は処理成功を意味しません。
重複でない複数結果は保持します。イベント側にだけ現れる処理は呼出し数と別に集計します。

### Skill参照

| kind | 検出する構文 |
|---|---|
| `named_reference` | `$skill` / `$plugin:skill` の文字列 |
| `body_provided` | `<skill>...<name>...</name>...</skill>` の本文提供形式 |
| `catalog_entry` | `- name: ... (file: ...)` の一覧形式と、一覧内のSkillパス |
| `read_candidate` | 呼出しの入力・実行イベントの入力にある `.../<skill>/SKILL.md` |
| `path_reference` | それ以外の発言内のSkillパス |

記録ID・skill名・qualified_name・pluginを保持します。1記録内の同名・同種の反復は1参照です。
引用・コード例なども候補になり得ます。名前の言及は実際の呼び出し・読込成功を証明しません。
CLIは遵守や適用を評価せず、Skillが出典と結果を読んで区別します。

### サブエージェント

チャット固有IDは`session_meta.id`です。`session_meta.session_id`が親子で同じ場合も別チャットとして保持します。
子の`source.subagent.thread_spawn.parent_thread_id`と`agent_path`を使って親子を接続します。
親のspawn_agent結果のtask_name／agent_idが子のagent_path／chat IDに一致すれば、起動元callも接続します。

child_linksのstatusはmatched / metadata_only / not_loaded / ambiguousです。
子ログがなくても親の起動記録を残し、子の呼出し数を0回と断定しません。
metadataで親子関係が確認でき、起動元だけ不明ならmetadata_onlyです。

自動探索は`--include-children`を指定したときだけ行います。既定はCODEX_HOME（未設定なら~/.codex）の
sessionsとarchived_sessionsで、各JSONLの先頭metadataだけ読み、親IDで子孫を絞ってから本文を読みます。
先頭行がmetadataでないファイルや読取不可の候補は発見できないため、探索の完全性は保証しません。
`--child`による明示入力も使えます。複数の異なるログが同一chat IDを持つ場合は、自動選択せずエラーにします。
一致する複製は1チャットにまとめ、duplicate_source警告を残します。

### 子に引き継がれた親の履歴

子のログには先頭の子metadataに続いて親・祖先のmetadataと過去の履歴が含まれる場合があります。
metadataの親IDの連鎖で祖先と確認できるものだけ受け入れます。単なる混在は拒否します。
`subagent_history_start_ordinal`と各記録のordinalがある場合は、それを子自身の開始位置に使います。
利用できない場合は、子自身のthread_idを持つ最初の記録以降を明示境界として使います。

それ以前の記録は`ownership: context_only`で保持し、呼出し・実行イベント・Skill参照の集計から除外します。
前置された指示などの帰属まで断定する分類ではありません。境界が確認できなければ、先頭metadata以外を
context_onlyとしてownership_unresolved警告を返します。0件を「子が実行していない」と解釈しません。
検索も既定でlocalだけ、`--include-context`で継承・帰属不明の記録を含めます。

## 検索・前後表示

```bash
knowledge-refinery session search /tmp/analysis.json --tool exec_command
knowledge-refinery session search /tmp/analysis.json --skill refinery-experience --skill-kind read_candidate
knowledge-refinery session search /tmp/analysis.json --text timeout --limit 10 --offset 0
knowledge-refinery session show /tmp/analysis.json --call-id call-001 --before 2 --after 2
knowledge-refinery session show /tmp/analysis.json --record-id 'chat-id:L12' --max-chars 8000
knowledge-refinery session search /tmp/tree.json --chat-id child-id --include-children --kind call
knowledge-refinery session search /tmp/analysis.json --kind unparsed --include-unparsed
```

既定の対象はrootだけ。`--chat-id`で別チャット、`--include-children`で取得済み子孫も対象にします。
未取得の子ログを検索時に読み足しません。record/call/item/turn IDは専用optionで区別し、複数ヒットを隠しません。
ツール名（namespaceを含む）は完全一致、Skillは短い名前またはplugin:skillの完全一致です。本文は大文字・小文字を区別する部分一致。
指定したfilterはAND条件です。重複記録は既定で検索対象外、`--include-duplicates`で含めます。

searchは記録単位で返します。呼び出しと補足イベントは別記録であり、ヒット件数はツール実行回数ではありません。
showにはrecord/call/item/turn IDのどれか1つが必須です。neighborsは同一チャット内だけの原順序の前後、
relatedは離れた位置の結果・補足イベントなどです。起動記録に対応するchild_linksも返します。

limit既定20、offset既定0、max-chars既定2000で、previewだけを短縮します。total・next_offsetでページを辿れます。
前後範囲はそれぞれ0〜100記録。relatedもlimit件までで、related_totalとrelated_truncatedを返します。
関連記録の続きを読む場合は該当call IDやitem IDでsearchします。
`--include-unparsed`は未解析原文を明示的に検索・表示する指定であり、機密除去を保証する指定ではありません。

## 集計

```bash
knowledge-refinery session stats /tmp/analysis.json
knowledge-refinery session stats /tmp/tree.json --include-children
knowledge-refinery session stats /tmp/tree.json --chat-id child-id --include-children
```

callsは重複を除いた呼出し要求の数です。ツール別にcalls・with_result・missing_result・ambiguous、
チャット別にcallsを返します。ambiguousはmissing_resultと重なる場合があります。
結果の内容から成功率を計算しません。

execution_eventsとunlinked_execution_eventsは補足イベントの別集計で、callsへ加算しません。
親の起動1回と子の内部呼出し5回は、全体では6回、親だけなら1回です。
親に届いた子の報告を子の呼出しとして再計上しません。
Skillは種類別の参照記録数であり、利用回数・遵守回数と呼びません。
child_links・warning_count・unparsed_recordsも確認し、取得範囲と限界をレポートに残します。
