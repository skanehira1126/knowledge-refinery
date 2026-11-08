# 解析JSONの読み方

`knowledge-refinery session` が保存した解析JSONを解釈するときに使う。
利用可能な引数は `knowledge-refinery session <extract|search|show|stats> --help` で確認する。

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

## 検索と続きを読む操作

- 検索は既定でrootのlocal記録が対象。`--chat-id` で対象を選び、
  `--include-children` で取得済み子孫を含める。検索時に子ログを読み足すことはない。
- ツール名は完全一致、Skillは短い名前または `plugin:skill` の完全一致。
  本文は大文字・小文字を区別する部分一致で、指定したfilterはAND条件。
- `--record-id` は解析用記録ID、`--call-id`・`--item-id`・`--turn-id` は元ログのIDを指定する。
  showにはこのうち1つが必要。
- `limit` 既定20、`offset` 既定0。`total` と `next_offset` を確認して続きを取得する。
  `max-chars` 既定2000はpreviewの制限で、保存済み本文は切り詰めない。
- showの `neighbors` は同一チャット内の前後、`related` は離れた結果や補足イベント。
  `--before`・`--after` はそれぞれ0〜100記録。
  `related_truncated` が真なら `related_total` を確認し、call IDやitem IDでsearchして補う。
- 重複記録は `--include-duplicates`、継承・帰属不明の記録は `--include-context` で含める。
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
