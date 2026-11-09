# ローカルログの取得と抽出

## 取得

ユーザー指定パスを優先する。IDしかない場合は `CODEX_HOME`（未設定なら `~/.codex`）の
`sessions/` 内で、そのIDを含むJSONLのファイル名を探す。
`archived_sessions/` はユーザーがアーカイブを対象として明示した場合だけ探す。
本文全件検索はせず、発見したファイルの `session_meta` でIDを照合する。
複数候補を勝手に連結しない。対象ホストにログがない場合はログの提供を依頼する。
認証ファイルや内部DBを探索する必要はない。

## ローカルCLIで抽出する

Codexが動作するホストで `knowledge-refinery session` を使う。未導入なら
`uv tool install git+https://github.com/skanehira1126/knowledge-refinery.git`、
sessionコマンドがない古い版なら `uv tool upgrade knowledge-refinery` で導入・更新する。
CLIが利用可能になってから抽出へ進む。MCPサーバーへローカルログを読ませない。
引数・既定値・出力の解釈は[CLIと解析JSONの読み方](session-analysis.md)を参照する。

```bash
knowledge-refinery session extract /path/to/rollout.jsonl --output /tmp/session-analysis.json
knowledge-refinery session stats /tmp/session-analysis.json
knowledge-refinery session search /tmp/session-analysis.json --kind call --limit 20
knowledge-refinery session search /tmp/session-analysis.json --skill refinery-experience
knowledge-refinery session show /tmp/session-analysis.json --call-id call-001 --before 2 --after 2
```

保存先はGit追跡・公開対象でないローカルの新規ファイルにする。抽出JSONは本文を保持するが匿名化ではない。
stdoutの保存結果だけで分析せず、statsとsearch/showを使って根拠を読む。
検索はページを最後まで辿り、未読範囲を記録する。表示の切詰めはmax-charsを増やすか元の該当行で補う。

分析には解析JSONを使い、CLIによるcall ID照合と重複処理を利用する。
関連記録から非同期完了・実際の結果・Skill本文取得を評価する。未知形式、対応不明、欠落、
判断に不足する内容がある場合だけ元ログの該当箇所を補う。unparsedは通常表示されないため、
必要性と機密内容を確認してからinclude-unparsedで読む。未知形式を「実行なし」に置き換えない。

Skill検索は名前参照・本文提供・読込候補の検索であり、成功や遵守の自動判定ではない。
ツール件数はstatsのcalls、実行イベント件数はexecution_eventsとして区別する。
searchのヒット件数やラッパー内のコード中の呼出し数を実行回数としない。

## サブエージェント

extractは既定で対象チャットの子孫も探索・保存する。親だけを対象にする場合は
`--exclude-children` を指定する。
自動探索の既定は `sessions/` のみ。アーカイブも対象とする明示依頼では
`--sessions-dir` に必要な探索先を指定する。
子孫のmetadataで親IDを確認し、チャット固有IDと共有session IDを区別する。
search/show/statsも既定で取得済み子孫を含める。`--chat-id`で起点を選び、
`--exclude-children`でそのチャットだけに限定する。
親子を含む集計か親だけかをレポートに明記する。child_linksのnot_loaded／ambiguousを確認し、
未取得の子を「0回」としない。継承した親の履歴はcontext_onlyとして件数から除かれる。
ownership_unresolvedなら子の実行回数を断定せず、必要な前提はinclude-contextで読む。
前後表示は同一チャット内、親子への移動は関係情報から行う。

## 抽出の制約と終了状態

導入・更新または抽出が失敗した場合は原因を報告し、解析を保留する。
未対応形式には対応するrollout JSONLが必要。reasoning本文・暗号化内容は分析資料へ転載しない。

ターン終了イベントはその時点の証拠であり、ファイルを読み終えた後の再開までは保証しない。
報告する範囲を取得時点で固定し、開始イベントの後に対応する終了イベントがない場合や、
最新のユーザー依頼が終了イベントの後にある場合は、終了済みと判断しない。
