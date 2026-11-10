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

対象の指定方法によって、登録の要否が変わります。

- Codex appツールでタイトルやプロジェクトから候補を探す場合：Refinery登録は不要です。
- CLIの `session list` で期間や直近の条件から候補を探す場合：対象リポジトリの有効なRefinery登録が必要です。
- ログのパスを直接指定する場合：Refinery登録は不要です。

RefineryのMCP接続は不要です。アプリツールは候補と状態の確認に使い、本文の解析には
ローカルログとCLIを使います。進行中のチャットは終了後にレビューしてください。

## 保存されるもの

レポートには、作業の流れ、実行結果、Skillの利用状況、根拠付きの指摘、再利用を検討できる作業を記載します。
子孫チャットも対象です。親だけを見たい場合は依頼時に指定してください。

保存先を省略すると、作業ディレクトリの `session-review-<session-id>.md` に保存します。
既存ファイルは上書きせず、vaultへの自動保存や対象コードの変更も行いません。

改善案を比較したい場合は、完成したレポートを指定して
[refinery-propose-improvements](refinery-propose-improvements.md)を呼び出してください。
CLIを直接使う場合は[sessionコマンド](../cli.md#session)を参照してください。
