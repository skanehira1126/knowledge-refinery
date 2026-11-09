# セッション解析CLIとJSONの読み方

`knowledge-refinery session` が保存した解析JSONを解釈するときに使う。
利用可能な引数は `knowledge-refinery session <extract|search|show|stats> --help` で確認する。

## コマンドと対象範囲

| コマンド | 入力 | 役割 |
| --- | --- | --- |
| `extract` | 起点チャットのrollout JSONL | 子孫ログを探索し、本文と対応関係を解析JSONに保存する |
| `search` | 解析JSON | 条件に合う記録を探す |
| `show` | 解析JSON | IDで選んだ記録と、その前後・関連記録を読む |
| `stats` | 解析JSON | 呼び出し・ツール・チャット別の件数や警告を確認する |

4コマンドとも既定で子孫を含める。`extract`はログを探索・保存し、他3コマンドは
保存済みJSONから対象を選ぶ。対象範囲と表示量は別で、search/showは必要な分だけ返す。

| 指定 | search/show/statsの対象 |
| --- | --- |
| 指定なし | rootと保存済みの子孫 |
| `--exclude-children` | rootだけ |
| `--chat-id ID` | 指定チャットとその子孫 |
| `--chat-id ID --exclude-children` | 指定チャットだけ |

## 引数の早見表

### extract

| 引数 | 役割・既定値 |
| --- | --- |
| `path` | 起点チャットのrollout JSONL。位置引数で必須 |
| `--output PATH` | 新規解析JSONの保存先。必須。既存ファイルは上書きしない |
| `--exclude-children` | 子孫を探索せず、起点チャットだけ保存する |
| `--sessions-dir DIR` | 子孫ログの探索先。複数指定可能。既定の探索先を置き換える |

探索先の既定は `CODEX_HOME/sessions`（CODEX_HOME未設定なら `~/.codex/sessions`）。
アーカイブや別の場所は `--sessions-dir` で明示する。通常ログとアーカイブを両方探す場合は
両方のディレクトリを指定する。`--sessions-dir` と `--exclude-children` は併用できない。
探索対象はmetadataで親子関係を確認できた子孫で、無関係なチャットは含めない。

### search / show / stats 共通

| 引数 | 役割・既定値 |
| --- | --- |
| `path` | extractで保存した解析JSON。位置引数で必須 |
| `--chat-id ID` | 対象の起点チャット。既定はroot |
| `--exclude-children` | 起点のチャットだけを対象にする |

### search / show の絞り込みと表示

| 引数 | 用途 |
| --- | --- |
| `--record-id ID` | 解析用記録IDで選ぶ。`<chat_id>:L<元行番号>` |
| `--call-id ID` | 元ログの呼び出しIDで要求・結果を探す |
| `--item-id ID` | 元ログのitem IDで選ぶ |
| `--turn-id ID` | ターンIDで選ぶ |
| `--tool NAME` | ツール名の完全一致 |
| `--skill NAME` | Skill名またはplugin:skillの完全一致 |
| `--skill-kind KIND` | Skill参照の種類を絞る。`--skill`が必要 |
| `--kind KIND` | call / result / message / executionなどの記録種別 |
| `--text TEXT` | 大文字・小文字を区別する部分一致 |
| `--limit N` | 返す記録数。既定20、正の整数 |
| `--offset N` | 先頭から飛ばす件数。既定0、0以上 |
| `--max-chars N` | 各previewの文字数。既定2000、正の整数 |
| `--include-unparsed` | 未解析原文を検索・表示する |
| `--include-duplicates` | 重複と判断した記録も検索する |
| `--include-context` | 継承された親の履歴・帰属不明の記録も検索する |

4種類のID指定は同時に使えない。showではいずれか1つが必須。
他の絞り込み条件はANDで、一致した記録が表示の起点になる。
show専用の `--before N` と `--after N` はそれぞれ同一チャット内の前後の記録数で、
既定0、範囲0〜100。離れた対応結果などは別の `related` に返る。
`--limit` はshowの関連記録にも適用されるが、前後記録の総数を制限するものではない。

## 基本的な読み進め方

```bash
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/analysis.json
knowledge-refinery session stats /tmp/analysis.json
knowledge-refinery session search /tmp/analysis.json --kind call --limit 10
knowledge-refinery session show /tmp/analysis.json --call-id call-001 --before 2 --after 2
# 指定チャットだけ集計する
knowledge-refinery session stats /tmp/analysis.json --chat-id child-id --exclude-children
```

## 保存結果と根拠

入力は `session_meta` を持つrollout JSONL。解析JSONの形式は
`format: knowledge-refinery.session-analysis`、`schema_version: 2`。
extractの標準出力は保存結果の要約で、本文は指定した新規ファイルに保存される。
exit 0でもwarningsがあれば完全に解析できたとは限らない。

| フィールド | 分析での用途 |
| --- | --- |
| `root_chat_id`, `chats` | 対象チャット、親子関係、入力パス・SHA-256などの出典を確認する |
| `records` | 元行順の記録。`record_id` は `<chat_id>:L<元行番号>` |
| `calls` | 呼び出し要求と `result_records`・`execution_records` の対応を読む |
| `relations` | 重複、結果、実行イベント、プロセス参照を辿る |
| `skill_mentions` | Skill名・本文提供・読込候補を探す |
| `child_links`, `warnings` | 未取得・曖昧な対応・帰属不明を確認する |

recordsの `data` に既知の本文・引数・結果、`unparsed` に未解析部分がある。
`turn_id_basis: preceding_context` は直前の文脈から補ったIDで、明示IDとは区別する。
`duplicate_of` は確実な重複の代表記録を指す。元記録自体は残る。
`unparsed.raw_exact: false` は除外対象の除去等により原文と一致しないことを示す。
識別できるreasoning本文・暗号化内容は除外されるが、匿名化を保証するものではない。

## 続きを読む操作

検索結果の `total` と `next_offset` を確認し、次のoffsetを指定して続きを取得する。
`truncated` が真なら `--max-chars` を増やして該当記録を読む。保存済み本文は切り詰めない。

showの `neighbors` は同一チャット内の前後、`related` は離れた結果や補足イベント。
`related_truncated` が真なら `related_total` を確認し、call IDやitem IDでsearchして補う。
前後・関連記録は文脈を読むための追加出力で、起点に指定した検索条件では絞り込まれない。
未解析原文は内容を確認したうえで `--include-unparsed` で検索・表示する。

## 件数と状態の解釈

`calls` は重複を除いた呼び出し要求の数。`execution_events` は補足イベントで、
両者を足して実行回数にしない。検索ヒットも記録数であり実行回数ではない。
ラッパー内のコードに書かれた呼び出しは独立した実行として数えない。

callの `link_status` は `matched` / `missing_result` / `ambiguous`。
結果の存在や `with_result` は成功を意味しない。`ambiguous` と `missing_result` の集計は
重なる場合がある。`process_reference` も同じプロセスへの参照であり完了の証明ではない。

Skill参照は `named_reference`（名前）、`body_provided`（本文提供）、
`catalog_entry`（一覧）、`read_candidate`（読取候補）、`path_reference`（パス言及）。
参照件数から利用成功や遵守を判定しない。

child_linksの `matched` は起動元との対応あり、`metadata_only` はmetadataだけで親子を確認、
`not_loaded` は子ログ未取得、`ambiguous` は対応不確定。
子へ継承された記録は `ownership: context_only` として通常の検索・集計から除かれる。
`ownership_unresolved` があれば、0件を「子が何も実行しなかった」と解釈しない。
