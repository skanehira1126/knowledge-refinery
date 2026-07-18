# Skills

V2は次の4 skillsで構成します。

- `refinery-project`: repoの導入、有効化、無効化、診断
- `refinery-experience`: routine logを除外し、目的、試行、観測、限界、次の仮説を一つのexperienceとして保存
- `refinery-memory`: 原則2件以上の反復根拠からproject memoryを抽出し、承認された候補だけをshared memoryへ昇格
- `refinery-maintenance`: 日次または明示的な棚卸し

旧 `session/raw/flow/review/stock` フローはV2の配布対象ではありません。プロダクトGitの採否と経験の価値を分離し、中央refinery repoへ直接記録します。

各Skillは現在project memoryとshared memory、現在project experience、selected project、vault全体の
順に探索範囲を広げます。statusとconfidenceは[共通の決定表](../knowledge-model.md#status-confidence)を使い、
secret、credential、access token、個人情報、顧客data、未redact logをvaultへ保存しません。
