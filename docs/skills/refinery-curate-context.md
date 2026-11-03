# refinery-curate-context

`$refinery-curate-context` は、対象projectのexperience・memoryから、次の作業を始める前に
知っておきたい事実を抽出します。たとえば「注文テーブルは明細単位で、同じ注文IDが複数行に現れる」
のように、集計や解釈を変える前提を数行に絞ります。

```text
$refinery-curate-contextを使って、売上集計で最初に知るべき前提を候補だけ出してください。
$refinery-curate-contextを使って、既存ナレッジから確認できた欠損値の意味をcontext.mdに反映してください。
```

候補だけを依頼した場合は、文案と根拠のレコードIDを返します。更新を依頼した場合は
vaultの `projects/<project_id>/context.md` に反映します。裏付けが足りない場合は保留し、
新たに採用する事実がなければファイルはそのままです。

このスキルは明示呼び出し専用です。チャットの開始時・履歴圧縮後には、hook が保存済みの本文を
配信します。配信内容の確認方法は [CLI の context](../cli.md#context) を参照してください。
