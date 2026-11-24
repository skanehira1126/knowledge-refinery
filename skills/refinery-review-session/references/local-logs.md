# ローカルログを取得して読む

## 1. ログを選ぶ

指定パスを優先する。`/status` のセッションIDを指定された場合は、次節の `--session-id` を使う。
履歴を探す範囲は依頼に合わせる。同一チャットの継続ファイルはCLIが出典を保持してまとめる。
対象ホストにログがなければ提供を依頼する。

IDやパスが未確定なら、登録済みプロジェクトの候補を `session list` で探す。
タイトルの一部は `--title`、別プロジェクトは `--project` で指定する。期間中の作業は
`--active-since` と `--active-before`、ファイル更新期間は `--updated-since` と
`--updated-before` で絞る。過去の作業を棚卸しするときは `--include-archived` を使い、
削除済みCodex worktreeも対象なら `--include-removed-worktrees` を加える。`total` と `next_offset` を確認し、
一意に選べない場合はタイトルと更新日時を示して選択を求める。選んだ `chats[].path` を抽出に使う。
引数と出力は[CLI早見表](session-analysis.md)を参照する。

タイトル検索はローカルの `session_index.jsonl` に名前があるチャットが対象。対象プロジェクトが
未登録の場合や、ローカルのタイトルを取得できない場合は、利用可能ならCodex appの `list_threads`
で同じ条件の候補を探せる。プロジェクト名しか分からないときは `list_projects` でパスと所属IDを照合する。
所属未設定でも作業ディレクトリが対象repoを指す場合がある。最近の一覧にない場合はhistoryモードと
返されたcursorで辿る。アーカイブも対象とする依頼では `list_archived_threads` を使える。
選んだチャットのホストとIDを保持して `read_thread` で状態を確認する。
一覧やターン要約はログ本文の解析根拠を代替しない。

リンクやアプリでチャット固有IDを得た場合は、対象ホストで対応するログを探し、先頭の
`session_meta.payload.id` と照合してパスを渡す。ログ名にIDを含むものは候補として使える。

## 2. CLIで抽出する

対象のCodexログが読める環境で、Plugin同梱の `knowledge-refinery session` を使う。
抽出に失敗した場合は原因を報告し、解析を保留する。

`/status` のセッションIDを使う場合は、CLIが共有 `session_id` で親ログを探し、既定で子孫も抽出する。
標準出力の `root_chat_id` が親チャットの固有ID。候補が複数ある場合は、対象のログパスを確定してから進める。

```bash
knowledge-refinery session extract --session-id SESSION_ID --output /tmp/session-analysis.json
```

ログパスを指定する場合は、次の形で抽出する。

```bash
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/session-analysis.json
```

探索先は `CODEX_HOME/sessions`（未設定なら `~/.codex/sessions`）。アーカイブを含める依頼では
`--include-archived` を指定する。圧縮ログと同一チャットの継続ファイルも直接抽出できる。
保存先はGit追跡・公開対象でない新規ファイルにする。解析JSONは匿名化済みではない。
親だけの依頼では `--exclude-children` を指定する。

## 3. 必要な根拠を読む

```bash
knowledge-refinery session stats /tmp/session-analysis.json
knowledge-refinery session search /tmp/session-analysis.json --kind call --limit 20
knowledge-refinery session show /tmp/session-analysis.json --call-id call-001 --before 2 --after 2
```

抽出時の要約だけで分析せず、検索結果・対応結果・警告を読む。
終了コードや呼び出し先で絞るときは `--where`、コマンド本文だけに照合するときは `--text-field` を使う。
[出力を読む際の判断](session-analysis.md#出力を読む際の判断)に従い、続きを取得し、未読・欠落・対象範囲を記録する。
元ログを読むのは、解析JSONの未知形式・対応不明・欠落を補う必要がある箇所に限る。
reasoning本文・暗号化内容はレポートへ転載しない。

終了状態は取得時点で確認する。開始後の終了イベントがない場合や、最新のユーザー依頼が
終了イベントより後にある場合は終了済みと判断しない。
