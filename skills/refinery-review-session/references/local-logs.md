# ローカルログの取得と抽出

## 取得

ユーザー指定パスを優先する。IDしかない場合は `CODEX_HOME`（未設定なら `~/.codex`）の
`sessions/` と `archived_sessions/` 内で、そのIDを含むJSONLのファイル名を探す。
本文全件検索はせず、発見したファイルの `session_meta` でIDを照合する。
複数候補を勝手に連結しない。対象ホストにログがない場合はアプリ経由の履歴を使い、
それも取得不可ならログの提供を依頼する。認証ファイルや内部DBを探索する必要はない。

## ローカルCLIで抽出する

Codexが動作するホストで既存CLIを実行する。MCPサーバーへローカルログを読ませない。
出力のフィールド・検索条件・件数の解釈が必要なら[解析JSONの読み方](session-analysis.md)を読む。

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

通常の入力は解析JSONとする。CLIが済ませたcall ID照合や重複処理を全件手作業で再構築しない。
関連記録から非同期完了・実際の結果・Skill本文取得を評価する。未知形式、対応不明、欠落、
判断に不足する内容がある場合だけ元ログの該当箇所を補う。unparsedは通常表示されないため、
必要性と機密内容を確認してからinclude-unparsedで読む。未知形式を「実行なし」に置き換えない。

Skill検索は名前参照・本文提供・読込候補の検索であり、成功や遵守の自動判定ではない。
ツール件数はstatsのcalls、実行イベント件数はexecution_eventsとして区別する。
searchのヒット件数やラッパー内のコード中の呼出し数を実行回数としない。

## サブエージェント

依頼範囲に子の内部分析が必要な場合はextractのinclude-children、またはchildで対象ログを追加する。
子孫のmetadataで親IDを確認し、チャット固有IDと共有session IDを区別する。
検索・集計は既定でrootだけ。chat-idで子を選び、include-childrenで取得済み子孫を含める。
親子を含む集計か親だけかをレポートに明記する。child_linksのnot_loaded／ambiguousを確認し、
未取得の子を「0回」としない。継承した親の履歴はcontext_onlyとして件数から除かれる。
ownership_unresolvedなら子の実行回数を断定せず、必要な前提はinclude-contextで読む。
前後表示は同一チャット内、親子への移動は関係情報から行う。

## CLIが使えない場合

未導入・古いCLI・未対応形式の場合は制約を報告し、元ログを行番号付きで範囲を分けて読む。
別CLIや同じ抽出処理の補助スクリプトは作らない。rollout、アプリ要約JSON、codex exec --jsonを区別する。
この場合だけcall ID照合と二重計上防止を直接行い、未読・欠落・未知形式を明記する。
reasoning本文・暗号化内容は分析資料へ転載しない。

ターン終了イベントはその時点の証拠であり、ファイルを読み終えた後の再開までは保証しない。
報告する範囲を取得時点で固定し、開始イベントの後に対応する終了イベントがない場合や、
最新のユーザー依頼が終了イベントの後にある場合は、終了済みと判断しない。
