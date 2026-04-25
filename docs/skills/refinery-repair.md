# refinery-repair

`refinery-repair` は運用中に壊れた YAML / front matter を直す補助 skill です。
通常フローの中核ではなく、CLI が読めなくなったときの復旧用です。

## 主な責務

- `meta.yaml` の型崩れや不正 YAML を修復する
- knowledge file の front matter を CLI が読める形へ戻す
- `derived_from`, `source_sessions`, `knowledge_id`, `knowledge_type` などの項目を整える

## 向いている場面

- `knowledge-refinery skills search knowledge`, `knowledge-refinery skills search review`, `knowledge-refinery skills search sessions` が壊れたファイルのせいで失敗するとき
- review / stock 操作の前に形式修復が必要なとき
