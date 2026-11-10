# refinery-review-session

終了済みチャットを振り返り、実行結果・Skillの使われ方・改善を検討する根拠を日本語レポートにまとめます。
セッションID、リンク、ローカルログのパス、または対象期間を指定してください。

```text
$knowledge-refinery:refinery-review-session を使い、終了済みセッション <session-id> をレビューして、
reports/session-review.md に保存してください。
```

## 必要なもの

- 対象チャットのローカルログ
- `knowledge-refinery session` CLI。未導入・古い版ならSkillが導入・更新します。

候補一覧は現在のRefinery登録済みGitプロジェクトと、存在するworktreeに絞ります。
別プロジェクトはlistの `--project` で指定できます。明示したログの解析には登録もMCP接続も不要です。進行中のチャットは終了後にレビューしてください。

## 保存されるもの

レポートには、作業の流れ、実行結果、Skillの利用状況、根拠付きの指摘、再利用を検討できる作業を記載します。
子孫チャットも対象です。親だけを見たい場合は依頼時に指定してください。

保存先を省略すると、作業ディレクトリの `session-review-<session-id>.md` に保存します。
既存ファイルは上書きせず、vaultへの自動保存や対象コードの変更も行いません。

改善案を比較したい場合は、完成したレポートを指定して
[refinery-propose-improvements](refinery-propose-improvements.md)を呼び出してください。
CLIを直接使う場合は[sessionコマンド](../cli.md#session)を参照してください。
