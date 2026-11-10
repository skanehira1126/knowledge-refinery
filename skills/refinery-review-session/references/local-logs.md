# ローカルログを取得して読む

## 1. ログを選ぶ

指定パスを優先する。IDだけの場合は `CODEX_HOME/sessions`（未設定なら `~/.codex/sessions`）で
IDを含むファイル名を探し、先頭の `session_meta` で照合する。アーカイブは明示依頼時だけ探す。
複数候補を勝手に連結しない。対象ホストにログがなければ提供を依頼する。

期間・直近の指定には `session list` を使う。
引数と出力は[CLI早見表](session-analysis.md)を参照する。

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
