---
name: refinery-capture
description: 作業中に得た観測事実や証拠を raw レイヤーへ軽量に記録する skill。コマンド結果、調査メモ、ユーザ発話、エラー観測を append-only で残すときに使う。
---

# refinery-capture skill

## Purpose

`raw/` を証拠保管レイヤーとして運用しやすくする。
後段の `refinery-curation` で再利用できるよう、観測事実を軽く・早く・壊さずに残す。

## Applicability

- 作業中に新しい観測事実、証拠、失敗例、環境条件を得たとき
- あとで見返す可能性があるコマンド結果やユーザ発話を残したいとき
- コンテキスト切り替え前に「今見えている事実」を失わず記録したいとき

## Workflow

1. 更新対象の `session_id` を確認し、必要なら `knowledge-refinery knowledge search --scope raw --session-id "<session_id>"` で既存の raw トピックを把握する。
2. 同じ topic の raw ファイルがあれば追記し、なければ `knowledge-refinery knowledge upsert --scope raw ...` で新規 Markdown ファイルを追加する。
3. 本文には観測事実をそのまま残す。例: コマンド、ファイルパス、エラーメッセージ、時刻、入力条件、ユーザ発話。
4. 解釈や仮説を書く必要がある場合は、事実と混ざらないように明示する。統合判断は `refinery-curation` に委ねる。
5. 記録の結果として目的・進捗・次アクションが変わるなら、`refinery-session` に戻って `state.md` の最小更新を行う。

## Preferred commands

- `knowledge-refinery session search`
- `knowledge-refinery knowledge search --session-id "<session_id>" --scope raw`
- `knowledge-refinery knowledge upsert --scope raw --session-id "<session_id>" --file "<file>.md" --title "<title>" --description "<description>" --body-file "<body_file>"`

## Guardrails

- `raw/` は append-only を基本とし、過去の証拠を結論に合わせて書き換えない。
- 矛盾する証拠が出ても削除せず、別エントリとして追記する。
- `raw` は証拠層であり、結論や昇格判断を先取りしない。
- 1 ファイル 1 トピックを基本とし、トピックが分かれたらファイルも分ける。
- front matter を新規作成または更新するときは、手書き YAML ではなく `knowledge-refinery knowledge upsert` を優先する。
- CLI を使えず手動で front matter を直す場合だけ、文字列値を原則ダブルクォートし、特に `title`, `description`, `summary` にバッククォート、コロン、角括弧、改行を含む場合は必ず引用する。
- 新規作成または front matter 更新後は `knowledge-refinery knowledge search --session-id "<session_id>" --scope raw` で読み取り確認する。

## Raw file format

- `raw` の知識ファイルは最低でも `title` と `description` を持たせる。
- `summary` は任意だが、将来の検索性向上に役立つなら追加してよい。
- 本文は時系列の箇条書きや短い観測ログを推奨する。
- 必要に応じて `tags` や `confidence` を追加してよい。
- `raw` の `tags` は必須ではない。局所検索に効く場合だけ `artifact/...` や `tech/...` を 1-2 個程度付ければ十分。
