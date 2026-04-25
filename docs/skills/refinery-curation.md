# refinery-curation

`refinery-curation` は `raw/` から `flow/` への整理を担当する skill です。
証拠をそのまま複製するのではなく、要点、解釈、未解決点を暫定知識として再構成します。

## 主な責務

- 関連する raw を横断して topic ごとに整理する
- `flow` に `title`, `description`, `summary` を持つ知識を作る
- 必要に応じて `knowledge_type: reference|constructive` を付ける
- 不確実性や反証を落とさずに暫定知識として保つ

## 向いている場面

- タスクが一区切りついたとき
- review 生成前に session の暫定知識を整えたいとき
