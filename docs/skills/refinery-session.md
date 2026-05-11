# refinery-session

`refinery-session` はセッション運用全体の orchestrator です。
`raw` や `flow` の書き方そのものではなく、どのタイミングで `refinery-capture`、`refinery-curation`、`refinery-shared` を使うかを決めます。

## 主な責務

- `session_id` の新規作成または再利用を判断する
- `state.md` の更新タイミングを管理する
- review 作成前に未整理の `raw` や `flow` を点検し、必要なら `knowledge_type` も揃える
- `knowledge-refinery review prepare` / `knowledge-refinery review refresh` を実行して `refinery-shared` に引き渡す

## 向いている場面

- 依頼を受けて session を開始するとき
- 作業中に「次は capture か curation か」を判断したいとき
- 依頼終了前に review 準備まで完了したいとき
