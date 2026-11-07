# refinery-review-session

終了済みCodexセッションの実行コード・ツール結果・Skill読込を根拠付きの日本語レポートにします。
明示呼び出し専用で、進行中の監視やコードの再実行はしません。

```text
$knowledge-refinery:refinery-review-session を使い、終了済みセッション <session-id> を解析し、
レポートを reports/session-review.md に保存してください。
```

ID・リンク・ログパスを受け、利用可能ならアプリの履歴読取を優先します。
ローカルログは[既存CLI](../session-analysis.md)で全文保存し、search/showで必要な根拠を読み、statsで集計します。解析はCodex側で行い、
MCPサーバーにログを読ませません。vault未設定・連携無効でもローカル解析は利用できます。

レポートは最終ターンの終了根拠、実行結果、Skill掲載と本文取得の違い、欠落と限界、
作業ID付きの入出力・判断・副作用・独立した観測回数を残します。指定先がなければ
`session-review-<session-id>.md` に保存し、既存ファイルは上書きしません。
生ログや抽出JSONを外部へ送信せず、抜粋から機密値を除きます。

解析Skillはレポート作成までで完了し、提案Skillを自動で呼び出しません。
改善先の比較は[refinery-propose-improvements](refinery-propose-improvements.md)を別途明示して依頼します。
レポート全文や生ログをvaultへ自動保存しません。
