# Skills

V2は次の4 skillsで構成します。

- `refinery-project`: repoの導入、有効化、無効化、診断
- `refinery-experience`: 過去のナレッジ検索と、意味のある試行のexperience記録。検索のみなら書き込まない
- `refinery-memory`: 原則2件以上の反復根拠からproject memoryを抽出し、承認された候補だけをshared memoryへ昇格
- `refinery-maintenance`: 日次または明示的な棚卸し

旧 `session/raw/flow/review/stock` フローはV2の配布対象ではありません。プロダクトGitの採否と経験の価値を分離し、中央refinery repoへ直接記録します。

ナレッジ検索は現在project memoryとshared memory、現在project experience、selected project、vault全体の
順に探索範囲を広げます。statusとconfidenceは[共通の決定表](../knowledge-model.md#status-confidence)を使い、
secret、credential、access token、個人情報、顧客data、未redact logをvaultへ保存しません。

各Skillは`skills/operating-rules.md`の共通実行条件を読みます。設定診断は
`refinery-project`、原則抽出は`refinery-memory`、日次棚卸しやvault品質監査は
`refinery-maintenance`が担当し、通常の開発レビューや単発の記録確認をvault監査へ広げません。
