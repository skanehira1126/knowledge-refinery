# refinery-curate-context

`$refinery-curate-context` は、ある場面で知らないと判断が変わるprojectの前提を、
そのhookで読める数行のMarkdownにまとめます。たとえば注文の集計なら「明細単位なので
注文IDは複数行に現れる」、他projectとの依存関係なら「注文schemaは `sales-core` が定義し、
このprojectは日別集計で参照する」と、対象と意味が分かるように書きます。

```text
$refinery-curate-contextを使って、売上集計の新規チャットに必要な前提を候補だけ出してください。
$refinery-curate-contextを使って、注文schemaの管理元を確認し、編集前に届く本文を更新してください。
```

候補の依頼では、配信先、文案、根拠のIDや参照先を返します。更新時はprojectのmemory・
experienceや実際のschema・実装を確認し、該当する本文だけに反映します。共通のタグは
関連先を探す手がかりとして使い、依存方向や契約の管理元は資料で確認します。

登録済みで有効なrepoでは、開発中に前提が判明・変更された時点でエージェントがMCPで本文を更新できます。
前提が解消したら古い行を外し、配信する行が尽きたらその配信先を解除します。hookはその時点の
本文をローカルCLIで読み取ります。[MCPでの更新](../mcp.md#hook-context)・[配信先とCLIでの確認](../cli.md#context)
