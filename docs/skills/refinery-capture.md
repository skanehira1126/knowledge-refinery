# refinery-capture

`refinery-capture` は `raw/` の証拠保管を担当する skill です。
コマンド結果、ユーザ発話、観測事実、エラー、環境条件などを append-only で軽く残します。

## 主な責務

- 作業中に得られた事実を失わず `raw/` に残す
- 同じ topic の raw を追記ベースで育てる
- 解釈と観測を混同しないようにする
- front matter の新規作成・更新は `knowledge-refinery skills upsert-knowledge --scope raw` を優先し、更新後に `knowledge-refinery skills search knowledge --scope raw` で読み取り確認する

## 向いている場面

- いま見えている事実をすぐ保存したいとき
- 後で `flow` に上げる前の材料を残したいとき
