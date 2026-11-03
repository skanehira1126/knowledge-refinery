# refinery-issue

Knowledge Refineryのissue（課題・TODO）をCLIで管理するSkillです。目的から選択されるほか、
`$refinery-issue`を指定して呼び出せます。

```text
Knowledge Refineryに「検索精度の改善」を課題として登録してください。
project exampleに紐付け、完了条件は「比較試験で改善を確認できる」としてください。
```

```text
$refinery-issueを使って、project exampleの進行中issueを一覧してください。
今回は更新しないでください。
```

issueはactive vault全体で独立管理し、ローカルrepoの登録・有効化は不要です。
project指定には登録済みIDを使い、未所属・複数projectへの紐付けにも対応します。
一覧の絞り込みは明示的に行い、作業directoryからは推定しません。

更新前に現在のrevisionを取得し、競合時は再取得して変更内容を見直します。
状態変更には理由が必要で、完了には完了条件と検証根拠を記録します。保存後は対象を読み戻して確認します。
タグの一括改名・解除は全project・全状態に及ぶため、対象を確認し、依頼の範囲内で実施します。

GitHub Issues、experience／memoryの記録、チャットの引き継ぎは別の機能です。
ナレッジの自動運用設定はissueの自動作成・更新を許可しません。
操作の詳細は[CLIリファレンス](../cli.md#issue)を参照してください。
配布する指示の正は`skills/refinery-issue/SKILL.md`です。
