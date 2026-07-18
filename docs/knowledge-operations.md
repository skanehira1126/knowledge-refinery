# ナレッジ運用

この文書は、中央vaultに保存するexperienceとmemoryを継続的に保守するためのrunbookです。
昇華フロー、タグ階層、検索可能なfieldは[ナレッジモデルと検索](knowledge-model.md)、
データ形式の詳細は[YAML schema](schema.md)、Git操作の原則は[Git運用](git-operations.md)、
障害別の確認事項は[トラブルシューティング](troubleshooting.md)を参照してください。

## 運用の目的

- 将来の判断を変え得る試行をexperienceとして残す。
- 繰り返し使える原則だけをmemoryへ抽出する。
- 根拠、適用条件、限界を追跡できる状態を維持する。
- product Gitとvault Gitの履歴を混ぜない。
- 破損、競合、誤削除からGit履歴で復旧できる状態を保つ。

## 責任分界

| 操作 | 通常の担当 | 必要な確認 |
|---|---|---|
| project metadataの更新 | Codex / 作業者 | repoの安定した事実と現在revision |
| experienceの新規記録 | Codex / 作業者 | meaningfulな試行であること |
| project memoryの作成・更新 | Codex / 作業者 | 根拠experienceと適用範囲 |
| shared memoryへの昇格 | Codexが提案、利用者が判断 | 2 project以上の独立した根拠 |
| memoryの大幅な書き換え | Codexが提案、利用者が確認 | 競合、反例、既存利用への影響 |
| 文書の削除 | 利用者が明示承認 | Git履歴と参照元の確認 |
| vaultのcommit・push・backup | vault管理者 | diff、機密情報、remote状態 |

自動処理やエージェントは、validationエラーの修復を理由に文書を黙って削除しません。

## ナレッジのライフサイクル

### 1. Experienceを記録する

検証、比較、不採用判断、失敗、または再利用可能な発見を一つのexperienceへまとめます。
単なる作業ログや、将来の判断に影響しない定型作業は記録しません。

experienceには少なくとも次を含めます。

- 目的
- 試したこと
- 観察した事実と解釈
- 微妙だった点・限界
- 次の可能性
- 実際に確認したevidence

既存experienceを更新するときは、直前に取得した `updated_at` を
`expected_updated_at` として渡します。stale revisionが拒否された場合は、最新内容を読み直し、
競合する変更を統合してから再実行します。

### 2. Project memoryへ抽出する

同じproject内で繰り返し利用できる判断原則をproject memoryへ抽出します。一度だけ観察した事実や、
適用条件が不明な知見はexperienceに留めます。

- 実在するsource experienceを最低1件指定する。
- 詳細な試行履歴はexperienceに残し、memoryには原則、条件、限界を書く。
- 既存memoryと意味が重なる場合は、新規作成よりrevision付き更新を優先する。
- 反例がある場合は削除せず、適用条件または未解決の競合として残す。

### 3. Shared memoryへ昇格する

shared memoryは、異なる2 project以上のexperienceが同じ原則を支持するときだけ作成します。
sourceはすべて `project-id/experience-id` 形式で指定し、作成前に本文とevidenceを読みます。

次の場合はsharedへ昇格しません。

- 根拠が1 projectに偏っている。
- 同じ実装や同じデータを複製しただけで、独立した検証ではない。
- project固有の前提を取り除くと原則が成立しない。
- 反例や適用限界を説明できない。

### 4. 更新・置換・削除を判断する

- experienceは試行の履歴です。事実訂正や追記を除き、過去の結論を現在の結論へ書き換えません。
- 後続experienceが古いexperienceを置き換える場合は、後続側の `supersedes` と旧側の
  `status: superseded` を使って関係を残します。
- memoryは現在の再利用可能な原則として更新できますが、source experience、条件、限界を保持します。
- 現行schemaにはmemoryのarchive/deprecated状態がありません。独自fieldを追加せず、必要なら
  現行原則へrevision付きで更新するか、判断が確定するまで競合を本文に残します。
- 文書削除は通常の整理手段にしません。重複や誤記でも、参照元とGit履歴を確認し、利用者の
  明示承認を得てから実施します。

## 運用頻度

以下のコマンド例では、`REFINERY_VAULT` に実際のactive vaultの絶対パスを設定してから実行します。
active vaultは `knowledge-refinery doctor --target "$PROJECT_ROOT" --json` の
`project.active_vault` でも確認できます。

### 作業開始時

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
knowledge-refinery project status --target "$PROJECT_ROOT" --json
```

`ready: true` と `enabled: true` のときだけrepo-scoped MCP toolsを使います。判断に影響しそうな
project memory、shared memory、experienceを狭い条件から検索します。`refinery_list_projects` の
metadataを使って、関連するprojectへcross-project検索を広げるか判断します。

### 意味のある試行の後

1. experienceとして残す価値があるか判断する。
2. `refinery_record_experience` で一つの統合記録を保存する。
3. 戻り値のIDを `refinery_get_experience` で読み直す。
4. vaultの差分を確認する。

### 日次または書き込みのまとまりごと

1. `refinery-maintenance` Skillで `refinery_validate` を実行する。
2. project metadataが現在の名前、概要、検索用tag、主要技術を表しているか確認する。
3. validationエラーをpath単位で修復する。
4. vault Gitのstatusとdiffを確認する。
5. 意図の明確な単位でcommitし、利用しているremoteへpushする。

```bash
git -C "$REFINERY_VAULT" status --short
git -C "$REFINERY_VAULT" diff --check
git -C "$REFINERY_VAULT" diff
```

### 週次または蓄積量が増えたとき

- low confidenceまたは文脈不足のexperienceを確認する。
- 重複、矛盾、陳腐化したproject/shared memoryを検索する。
- project memoryからshared memoryへ昇格できる候補を探す。
- shared memoryのsourceが現在も存在し、2 project以上を維持しているか確認する。
- 長期間pushされていないcommitや未commit差分がないか確認する。

## Validationエラーの復旧

検索は壊れた文書を隔離するため、検索が成功してもvault全体が正常とは限りません。定期的に
`refinery_validate` を実行し、返された `path` と `error` をすべて確認します。

復旧手順:

1. 対象文書と周辺のGit差分を確認する。
2. YAML、filename、ID、scope、source experienceのどれが不正か切り分ける。
3. Git履歴から直前の正常内容を確認する。
4. 最小限の修正を行い、`refinery_validate` を再実行する。
5. vault全体がvalidになってからdiffをcommitする。

```bash
git -C "$REFINERY_VAULT" diff -- "path/from/validation.md"
git -C "$REFINERY_VAULT" log --oneline -- "path/from/validation.md"
git -C "$REFINERY_VAULT" show COMMIT:"path/from/validation.md"
```

復旧前の差分を失わないよう、既知の正常commitへ戻す操作は内容を退避し、利用者が復旧方針を
確認した後に行います。evidenceの参照先が移動しただけの場合は、結論を削除せず制約として扱います。

## Revision競合の復旧

`expected_updated_at is stale` は、別の処理が同じ文書を先に更新したことを示します。

1. exact getで最新headerと本文を取得する。
2. 自分の変更と最新変更を比較する。
3. source、反例、条件を失わない形で統合する。
4. 最新の `updated_at` を指定して一度だけ再実行する。

最新revisionを読まずに同じ更新を繰り返したり、vaultファイルを直接上書きしたりしません。

## Gitとbackup

CLIとMCPはcommit、push、backupを自動実行しません。vaultは独立Git repositoryとして管理し、
少なくとも次を満たす運用にします。

- 書き込みのまとまりごとにcommitする。
- activeに利用するvaultは日次を目安にprivate remoteへpushする。
- remoteとは別に、組織または個人の要件に沿った定期backupを持つ。
- backupからmarker、project領域、shared memory、Git履歴を復元できることを定期確認する。
- evidenceや本文へsecret、credential、不要な個人情報を保存しない。

product Gitとvault Gitのcommitやpull requestは常に分離します。

## 運用チェックリスト

### 書き込み前

- [ ] 対象repoが `ready: true` か。
- [ ] project metadataが現在のprojectを正確に表しているか。
- [ ] 既存memoryとexperienceを検索したか。
- [ ] evidenceを実際に確認したか。
- [ ] 更新の場合は最新revisionを取得したか。

### 書き込み後

- [ ] 保存した文書をexact getで読み直したか。
- [ ] `refinery_validate` がvalidか。
- [ ] product repoを変更していないか。
- [ ] vault Gitのdiffに機密情報や意図しない変更がないか。
- [ ] vaultの変更をcommitし、必要なremoteへpushしたか。

### 定期棚卸し

- [ ] dangling source、重複、矛盾、stale memoryを確認したか。
- [ ] shared memoryの根拠が2 project以上あるか。
- [ ] 未commit・未pushの変更が残っていないか。
- [ ] backupから復旧可能か。
