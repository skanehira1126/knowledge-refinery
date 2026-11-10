# refinery-propose-improvements

セッションレビューのレポートから、次に取り組む改善案を比較し、優先順位と具体案を日本語でまとめます。
1件でも、複数レポートをまとめて指定しても使えます。

```text
$knowledge-refinery:refinery-propose-improvements を使い、reports/session-review.md から
優先する改善案と具体的な変更案を提案し、reports/improvements.md に保存してください。
```

## 入力と成果物

入力は解析済みのレポートです。ログしかない場合は、先に
[refinery-review-session](refinery-review-session.md)でレビューしてください。

提案書では、既存機能の改善、Skill化、CLI化、AGENTS.mdへの反映、見送りを比較します。
採用候補には変更先・具体案・検証方法を、見送りには理由を記載します。
根拠が不足する案は、未確認事項を添えて区別します。

保存先を省略すると、作業ディレクトリの `improvement-proposals.md` に保存します。
元レポートと既存ファイルは上書きしません。実装やvaultへの保存は、提案を確認した後で別途依頼してください。
