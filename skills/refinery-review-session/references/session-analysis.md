# セッション解析CLI早見表

引数を選ぶときと、CLI出力を解釈するときに使う。
利用可能な引数は `knowledge-refinery session <list|extract|search|show|stats> --help` で確認する。

## コマンドと対象範囲

| コマンド | 入力 | 役割 |
| --- | --- | --- |
| `list` | ローカルログのディレクトリ | 更新日時の範囲から親チャットの候補を直近順に選ぶ |
| `extract` | 起点チャットのrollout JSONL | 子孫ログを探索し、本文と対応関係を解析JSONに保存する |
| `search` | 解析JSON | 条件に合う記録を探す |
| `show` | 解析JSON | IDで選んだ記録と、その前後・関連記録を読む |
| `stats` | 解析JSON | 呼び出し・ツール・チャット別の件数や警告を確認する |

extract/search/show/statsは既定で子孫を含める。`extract`はログを探索・保存し、他3コマンドは
保存済みJSONから対象を選ぶ。対象範囲と表示量は別で、search/showは必要な分だけ返す。

| 指定 | search/show/statsの対象 |
| --- | --- |
| 指定なし | rootと保存済みの子孫 |
| `--exclude-children` | rootだけ |
| `--chat-id ID` | 指定チャットとその子孫 |
| `--chat-id ID --exclude-children` | 指定チャットだけ |

## 引数の早見表

### list

| 引数 | 役割・既定値 |
| --- | --- |
| `--project PATH` | 対象の登録済みGit作業ディレクトリ。既定は現在のディレクトリ |
| `--updated-since DATE` | 更新日時の下限。この時刻を含む。省略すると下限なし |
| `--updated-before DATE` | 更新日時の上限。この時刻を含まない。省略すると上限なし |
| `--sessions-dir DIR` | ログの探索先。複数指定可能。既定のCODEX_HOME/sessionsを置き換える |
| `--limit N` | 一度に返すチャット数。既定20、正の整数 |
| `--offset N` | 直近順の一覧で飛ばす件数。既定0、0以上 |

対象のGitルートに有効な `.refinery.yaml` が必要。未登録・無効ならエラーになる。
同じGit共通ディレクトリのworktreeを含め、削除済みworktree・cwd不明・Git外・別cloneは除く。
対象worktreeに設定がなければ登録済みの作業ツリーを `--project` に指定する。
出力のproject_id・project_root・git_common_dirで対象を確認する。

日時指定にはタイムゾーンが必須。日付のみはUTCの0時、日本時間は `+09:00` を付ける。
更新の基準はファイルmtimeで、コピー・復元でも変わる。終了状態は別途確認する。
一覧は親チャット単位。`chats[].path` をextractへ渡し、複数の `paths` があれば対象を確認する。
`total`・`next_offset` で続きを、`skipped_files` で取得できなかった件数を確認する。
limitは返却数を制限するが、ファイル情報と先頭metadataの走査数は制限しない。

```bash
# 日本時間11月7日の更新分から直近3件を選ぶ
knowledge-refinery session list \
  --updated-since 2026-11-07T00:00:00+09:00 \
  --updated-before 2026-11-08T00:00:00+09:00 --limit 3
```

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

## 出力を読む際の判断

| 確認する出力 | 読み方・次の操作 |
| --- | --- |
| extractの保存結果 | 本文は保存JSONにある。exit 0でもwarningsを確認する |
| `next_offset` | 続きがあれば、その値をoffsetに指定する |
| `truncated` | max-charsを増やして該当記録を読む。保存本文は切り詰められない |
| showの `neighbors` / `related` | 同一チャット内の前後 / 離れた結果や補足イベント。起点の検索条件では絞られない |
| `related_truncated` | call IDやitem IDでsearchし、関連結果を補う |
| `calls` / `execution_events` | 呼び出し要求 / 補足イベント。合算しない。検索ヒットも実行回数ではない |
| `with_result` / `link_status: matched` | 結果との対応あり。成功は結果の内容から判断する |
| `missing_result` / `ambiguous` | 結果未取得 / 対応不確定。失敗とは断定しない。集計は重なる場合がある |
| `process_reference` | 同じプロセスへの参照。完了の証明ではない |
| `child_links: not_loaded / ambiguous` | 子の未取得 / 対応不確定。子の実行0回とは扱わない |
| `child_links: metadata_only` | 親子関係は確認済み、起動元は不明 |
| `ownership: context_only` | 継承・帰属不明の履歴。通常の検索・実行集計から除外。必要時はinclude-contextで読む |
| `ownership_unresolved` | 子自身の開始境界が不明。子の実行件数を断定しない |
| `turn_id_basis: preceding_context` | 直前の文脈から補ったID。明示IDと区別する |
| `unparsed` | 必要箇所だけinclude-unparsedで読む。raw_exactがfalseなら除外処理後の原文 |

Skill参照の種類は次のとおり。いずれも出典と結果を読み、取得成功・遵守を別に評価する。

| kind | 検出対象 |
| --- | --- |
| `named_reference` | 名前の言及 |
| `body_provided` | 本文提供の形式 |
| `catalog_entry` | 一覧への掲載 |
| `read_candidate` | 読取候補のコマンド等 |
| `path_reference` | その他のパス言及 |

根拠にはrecord_id（chat IDと元行番号）や元のcall/item/turn IDを使う。
同じ位置でもログが変わり得るため、出典のパス・SHA-256も確認する。
未読・未取得・対応不明を「実行されなかった」に置き換えない。
