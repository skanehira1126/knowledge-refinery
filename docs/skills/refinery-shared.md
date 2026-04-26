# refinery-shared

`refinery-shared` は `shared/review` から `shared/stock` への昇格判断を担当する skill です。
review 候補の promote / reject と `shared/state.md` の更新を行います。

## 主な責務

- review 候補が shared に上げる価値を持つか判断する
- `knowledge-refinery skills promote-review` / `knowledge-refinery skills reject-review` を使い分ける
- `knowledge_id` が type 違いで曖昧な review は `--knowledge-type` で絞り込む
- `reference` と `constructive` で stock の書き方を変える
- shared 側の現在地を必要最小限で更新する
- `shared/stock` を手動更新する場合は `knowledge-refinery skills upsert-knowledge --scope stock` を優先し、更新後に `knowledge-refinery skills search knowledge --scope stock` で読み取り確認する

## 向いている場面

- review 準備が終わって昇格判断に入りたいとき
- stable な知識だけを `shared/stock` に残したいとき
