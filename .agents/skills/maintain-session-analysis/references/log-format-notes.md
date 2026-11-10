# Codexログ形式の調査記録

確認日: 2026-11-07。ここは調査メモであり、確定した抽出CLIの仕様書ではない。

## 公式資料で確認したこと

[Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
は、`codex exec --json` の標準出力をJSONLとして保存し、`item.completed` イベントの
`item.type`、`status`、`exit_code`、`command` などを評価に使う例を示している。

この資料は以下のローカルrollout構造の完全な定義ではない。同じJSONLでも、
`codex exec --json` とローカルrolloutを同一スキーマとして扱わない。

## ローカルログで観測したこと

同日の開発チャットに対応するローカルrollout 1件について、記録種別とフィールド名を確認した。
本文は転載していない。追加確認した親・子ログのcli_versionは `0.167.0-alpha.3.2` であり、
過去・将来の全バージョンへの一般化はできない。未出現の種類が存在しないとも判断しない。

各行がJSONオブジェクトで、外側に `timestamp`、`type`、`payload`、`ordinal` を持つ。
一部の行には外側の `metadata` もある。

| 外側のtype | 観測した情報 |
|---|---|
| `session_meta` | ID、cwd、cli_versionなどのセッション情報 |
| `turn_context` | turn_id、モデル、権限、作業環境など |
| `response_item` | 発言、ツール呼び出しと結果、reasoningなど |
| `event_msg` | task_started、task_complete、item_completedなど |
| `token_usage_record` | ターン・セッションに関する利用量 |
| `world_state` | full、state |

`response_item` の `function_call` / `custom_tool_call` と対応するoutputには `call_id` がある。
前者は `arguments`、後者は `input` に入力を持つ。発言は `message` として記録され、
`role`、`content` に加えて `phase: commentary` / `phase: final_answer` が観測された。

`event_msg.item_completed` には開始・終了時刻、turn_id、itemなどがあり、item内で次を観測した。

| item.type | 主なフィールド |
|---|---|
| `CommandExecution` | command、cwd、aggregated_output、exit_code、process_id、status、duration |
| `McpToolCall` | arguments、result、server、tool、status、duration |
| `FileChange` | changes、status、stdout、stderr |
| `UserMessage` | content、id、client_id |
| `AgentMessage` | content、id、phase |
| `Reasoning` | raw_content、summary_text、id |
| `Extension` | action、kind、query、results、id |

reasoning本文・暗号化内容は抽出対象に含めない。

## 親子の対応と引き継がれた履歴（追加観測）

親のspawn_agent結果のtask_nameと、子metadataのsource.subagent.thread_spawn.agent_pathが一致した。
子のparent_thread_idは親のchat IDと一致する。子自身のidは固有だが、session_idは親と共通だった。
IDを混同せず、チャット単位で記録・集計する。

子ログは先頭の子metadataに続いて親metadataと過去履歴を含んでいた。metadataには
subagent_history_start_ordinalがあり、そのordinalに一致する記録は子自身のthread_idを持つ
thread_settings_appliedだった。子の実行を始める位置として両方が一致することを確認した。
この境界以前の履歴を子の実行件数へ加算してはいけない。境界が取れない形式は未確認として扱う。

item_completedのSubAgentActivityにはagent_path、agent_thread_id、id、kind、model、reasoning_effortがあった。
SubAgentActivity／Extensionの一部ではitem.idと親の呼び出しcall_idが一致した。
CommandExecution等では一致しない例もあるため、全イベントを類似した呼び出しへ統合しない。

## 現在の実装契約

[解析JSONとCLIの仕様](../../../../docs/session-analysis.md)を正本とする。
以下はKnowledge Refineryのschema 2の契約であり、Codexの外部仕様ではない。

- 全文保存と表示を分離し、extractは新規JSONファイルへ保存。search/showは範囲・表示文字数を制限する。
- records、calls、relations、skill_mentions、child_links、warningsを分離する。
- 未知形式・追加キーはunparsedへ保存。既知のreasoning・暗号化内容は除外する。
- call IDと明示item IDで一意に対応する場合だけ接続し、曖昧な対応を推測で統合しない。
- 呼び出し数と補足イベント数、Skill参照の種類を区別する。遵守や意味的な成功は自動判定しない。
- 親子の共有session IDを同一chat IDとして扱わない。継承・帰属不明の履歴はcontext_onlyとして保存し、
  子の呼び出し集計へ混ぜない。検索ではinclude-contextで確認できる。
- 元JSONLは変更せず、解析JSONも匿名化済みとは扱わない。

架空ログで全文保存、検索・前後表示、集計、明示IDによる重複、曖昧な対応、未知形式、
親子・孫の探索、継承履歴の除外、上書き拒否を検証している。
同版の子ログ1件でも191記録を保持し、141記録をcontext_only、子自身の呼び出しを4件と抽出した。
親と併せた取得でもchild_linksがmatchedになることを確認した。これは限定した実ログ検証であり、
全形式の対応や実モデルによるレポート品質評価を意味しない。生ログと個人IDはこの記録へ転載していない。

## 次に確認する事項

- 対応するCodex版と、公開資料で保証された範囲。
- response_itemとitem_completedのID対応、重複・補完関係、片方だけ存在する場合。
- ネストしたツール呼び出し、非同期処理、子セッションの識別方法。
- 開始・終了・中断・承認待ち・再開を示す記録と、取得途中の扱い。
- 圧縮・再開・ログ形式の変化で欠ける情報と未知フィールドの扱い。
- 未対応形式の追加時にschema 2の契約で保存・表示・集計が整合するか。
- 継承履歴の開始位置が異なる表現で記録される版の対応。境界が不明なら件数に混ぜない。

## 解析用の形式についての方針

元ログはJSONLのまま保持し、CLIで機械的に整理した解析用JSONを出力する。
解析用JSONでも元行番号とIDを保持して根拠へ戻れるようにする。
CSVやYAMLへの置換は現在の対象に含めない。具体的な出力スキーマは上記の仕様文書で管理する。
