# 解析JSONリファレンス

`knowledge-refinery session` の出力を読むためのリファレンスです。
コマンドと引数は[CLIリファレンス](cli.md#session)、レビューの依頼方法は
[refinery-review-session](skills/refinery-review-session.md)を参照してください。

## listの出力

| 項目 | 意味 |
| --- | --- |
| `chats` | 更新日時の降順で並ぶ親チャットの候補 |
| `chats[].chat_id` / `cwd` | チャットID / ログmetadataの作業ディレクトリ |
| `chats[].updated_at` | 最新ログのmtime。UTC。会話の最終イベント時刻や終了状態ではない |
| `chats[].path` / `paths` | 最新ログのパス / 同一チャットIDの全パス |
| `updated_since` / `updated_before` | 下限以上・上限未満の日時。未指定はnull |
| `total` / `next_offset` | 条件に一致したチャット数 / 続きを取得するoffset。続きがなければnull |
| `scanned_files` / `skipped_files` | 走査したファイル数 / 読取不可・metadata不正等で除外した数 |

同一チャットの複数ログは最新mtimeで1候補にまとめてから期間で絞ります。
mtimeはコピー・復元でも変わります。レビュー済みかどうかは記録しません。

## extractが保存するJSON

`format: knowledge-refinery.session-analysis`、`schema_version: 2`。
入力は `session_meta` を持つrollout JSONLです。`codex exec --json` やアプリの要約JSONは対象外です。
対応しないschemaの解析JSONは、元ログから再抽出してください。

| 項目 | 内容 |
| --- | --- |
| `root_chat_id` | 起点チャットの固有ID |
| `chats` | 固有ID・共有session ID・親ID・agent path・Codex版・出典 |
| `chats[].source` | 入力パス・SHA-256・bytes・行数 |
| `records` | チャットごとの元行順の記録 |
| `calls` | 重複を除いた呼び出し要求と、結果・実行イベントへの参照 |
| `relations` | 重複・結果・実行イベント・プロセス参照の関係 |
| `skill_mentions` | Skill名・本文提供・読込候補などの参照 |
| `child_links` | 起動呼び出しと子チャットの対応 |
| `warnings` | 対応不明・欠落・未知構造など。該当チャット・記録への参照を含む |

標準出力は保存先と件数の要約です。本文は保存したJSONにあります。

### records：記録と出典

| 項目 | 内容 |
| --- | --- |
| `record_id` | `<chat_id>:L<元行番号>`。出典のSHA-256と併せて識別する |
| `chat_id`, `line`, `timestamp`, `ordinal` | 出典・元の日時・順序 |
| `source_type`, `source_subtype`, `source_metadata` | 元の種類と外側のmetadata |
| `kind` | metadata / context / message / call / result / execution / lifecycle / usage / unparsed / excluded |
| `turn_id`, `turn_id_basis` | ターンIDと根拠。explicitは明示、preceding_contextは直前の文脈から補完 |
| `source_ids` | 元のitem ID・call ID。未取得ならnull |
| `tool` | 呼び出し名またはnamespace.name。MCP実行イベントはserver/tool |
| `data` | 発言・引数・結果などの既知payload。元の表現を保持 |
| `unparsed` | 未解析部分の原文・理由・追加キーの位置・raw_exact |
| `duplicate_of` | 確実な重複の代表record ID。重複でなければnull |
| `ownership`, `ownership_basis` | local / context_onlyと、その帰属の根拠 |

未知種類や不正な既知レコードは `kind: unparsed`、`data: null`。
既知envelopeの追加キーがある場合は、既知部分を解析しつつ原文もunparsedへ保持します。
`unparsed.raw_text` は原則として元の1行ですが、除外処理で変わった場合は `raw_exact: false` です。

識別できるreasoning・analysis channel・暗号化内容は保存対象外です。
不正JSONにそれらの識別文字列がある場合は原文を残さず、位置と警告を残します。
その他の秘密値まで匿名化する機能ではありません。未解析原文は通常の表示・本文検索では展開しません。

### calls / relations：対応付けと重複

callは解析用 `id`（request record ID + `:call`）、元のcall_id、chat_id、tool、
request_record、result_records、execution_records、link_statusを持ちます。

| 判定 | 条件 |
| --- | --- |
| 呼び出しと結果 | 同一チャットでcall IDと種類が対応し、結果が要求の後にある |
| 補足イベント | call ID、またはitem IDが呼び出しのIDへ一意に対応する |
| 重複 | 同一チャット・ターン・item ID・種類・内容。発言の2表現はrole・phase・テキストで照合 |
| process_reference | exec_command / write_stdinの構造化入出力に同じsession_idがある |

複数候補へ対応するIDは曖昧として残します。時刻や本文の類似だけでは結び付けません。
重複の元記録も保存し、再試行や重複でない複数結果は別記録として保持します。

| link_status | 意味 |
| --- | --- |
| `matched` | 結果との対応あり。処理成功を意味しない |
| `missing_result` | 対応する結果を取得できていない |
| `ambiguous` | 対応先が一意に決まらない |

### child_links / ownership：親子と継承履歴

チャット固有IDは `session_meta.id`。共有session_idが同じでも別チャットとして扱います。
子metadataのparent_thread_idとagent_pathで親子を確認し、親の起動結果のtask_name / agent_idが
子のagent_path / chat IDと一致すれば起動元callも結び付けます。

| child_linksのstatus | 意味 |
| --- | --- |
| `matched` | 親子関係と起動元の対応あり |
| `metadata_only` | metadataで親子を確認。起動元は不明 |
| `not_loaded` | 子ログ未取得 |
| `ambiguous` | 対応不確定 |

子に継承された親・祖先の履歴は `context_only` として保存し、子の実行件数から除外します。
境界にはsubagent_history_start_ordinalを使い、なければ子自身のthread_idを持つ最初の記録を使います。
境界不明なら先頭metadata以外をcontext_onlyにし、`ownership_unresolved` を返します。
未取得・帰属不明を「実行0回」と解釈しないでください。

子孫の探索では各JSONLの先頭metadataを使います。先頭metadataのないログや読取不可のログは発見できません。
同一chat IDの内容が異なるログはエラー、一致する複製は統合して `duplicate_source` 警告を残します。

### skill_mentions：Skill参照

| kind | 検出対象 |
| --- | --- |
| `named_reference` | `$skill` / `$plugin:skill` |
| `body_provided` | `<skill>...<name>...</name>...</skill>` |
| `catalog_entry` | Skill一覧の項目・パス |
| `read_candidate` | 呼び出し・実行イベントの入力にあるSkillパス |
| `path_reference` | その他の発言内のSkillパス |

record ID、skill名、qualified_name、pluginを保持します。同じ記録内の同名・同種は1参照です。
引用やコード例も一致するため、参照だけで本文取得・利用成功・遵守とは判断できません。

## search / showの出力

| 項目 | 意味 |
| --- | --- |
| `chat_ids` | 対象チャット |
| `records`, `total`, `next_offset` | 一致した記録のページ、総数、次のoffset |
| `preview`, `preview_chars`, `truncated` | 表示本文、切詰め前の文字数、切詰めの有無 |
| `neighbors`（show） | 起点記録と同じチャット内の前後 |
| `related`（show） | 離れた位置にある対応結果・補足イベントなど |
| `related_total`, `related_truncated`（show） | 関連記録の総数と表示省略の有無 |
| `child_links`（show） | 起点記録に対応する子チャット情報 |

## statsの件数

| 項目 | 数えるもの |
| --- | --- |
| `calls` | 重複を除いた呼び出し要求。ツール別・チャット別にも返す |
| `with_result` / `missing_result` | 結果のある要求 / 結果のない要求 |
| `ambiguous` | 対応が曖昧な要求。missing_resultと重なる場合がある |
| `execution_events` / `unlinked_execution_events` | 補足イベント / 要求に結び付かない補足イベント |
| `skill_references` | Skill別・種類別の参照記録数 |
| `records`, `duplicate_records`, `context_only_records` | 全記録、重複、継承・帰属不明の記録数 |
| `unparsed_records`, `warning_count`, `warnings_by_code` | 未解析部分のある記録数と警告件数 |

callsとexecution_eventsは別の単位です。検索ヒットやラッパー内のコードを実行回数へ加算しません。
with_resultは成功数、skill_referencesは利用成功数ではありません。
