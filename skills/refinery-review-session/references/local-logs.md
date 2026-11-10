# ローカルログを取得して読む

## 1. ログを選ぶ

指定パスを優先する。IDだけの場合は `CODEX_HOME/sessions`（未設定なら `~/.codex/sessions`）で
IDを含むファイル名を探し、先頭の `session_meta` で照合する。アーカイブは明示依頼時だけ探す。
複数候補を勝手に連結しない。対象ホストにログがなければ提供を依頼する。

IDやパスが未確定なら、利用可能な入口を依頼に合わせて選ぶ。

- Codex appツールが使える場合は `list_threads` でタイトル・ID・状態・作業ディレクトリを確認する。
  プロジェクト名から探す場合は `list_projects` でパスと所属IDを照合する。所属未設定でも
  作業ディレクトリが対象repoを指す場合があるため、所属IDだけで除外しない。
  最近の一覧にない場合はhistoryモードと返されたcursorで辿る。アーカイブは明示依頼時だけ
  `list_archived_threads` で探す。対象のCodexチャットを選び、ホストとIDを保持して
  `read_thread` で状態を確認する。一覧やターン要約はログ本文の解析根拠を代替しない。
- 登録済みプロジェクトの直近・期間指定には `session list` の `--project`・
  `--updated-since`・`--updated-before`・`--limit` を使う。アプリツールが使えない場合も
  この入口を使える。引数と出力は[CLI早見表](session-analysis.md)を参照する。

アプリで得たIDも、対象ホストのログ先頭にある `session_meta` と照合してから抽出する。

## 2. CLIで抽出する

Codexホストで `knowledge-refinery session` を使う。未導入なら次で導入する。

```bash
uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git
```

古い版なら `uv tool upgrade knowledge-refinery` で更新する。
導入・更新・抽出が失敗した場合は原因を報告し、解析を保留する。

```bash
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/session-analysis.json
```

保存先はGit追跡・公開対象でない新規ファイルにする。解析JSONは匿名化済みではない。
親だけの依頼では `--exclude-children` を指定する。

## 3. 必要な根拠を読む

```bash
knowledge-refinery session stats /tmp/session-analysis.json
knowledge-refinery session search /tmp/session-analysis.json --kind call --limit 20
knowledge-refinery session show /tmp/session-analysis.json --call-id call-001 --before 2 --after 2
```

抽出時の要約だけで分析せず、検索結果・対応結果・警告を読む。
[出力を読む際の判断](session-analysis.md#出力を読む際の判断)に従い、続きを取得し、未読・欠落・対象範囲を記録する。
元ログを読むのは、解析JSONの未知形式・対応不明・欠落を補う必要がある箇所に限る。
reasoning本文・暗号化内容はレポートへ転載しない。

終了状態は取得時点で確認する。開始後の終了イベントがない場合や、最新のユーザー依頼が
終了イベントより後にある場合は終了済みと判断しない。
