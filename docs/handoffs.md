# 新しいチャットへの引き継ぎ

handoffは特定の作業を再開するための資料です。試行から得た経験を扱うexperience、
再利用する原則を扱うmemoryと保存領域を分け、過去の判断を再評価できる状態で渡します。

## Skillから使う

旧チャットで、明示的に次のように依頼します。

```text
$refinery-handoffを使って、この作業の引き継ぎを保存してください。
確認済みの事実、未検証の仮説、未解決事項を分けてください。
```

保存結果の確認後、引き継ぎIDと新チャット向けの短い依頼文が返ります。新しいチャットで、
保存元の`project_id`と引き継ぎIDを含む依頼文を使います。別projectのチャットからも参照でき、
保存元repoがローカルに存在しなくてもactive vaultから取得できます。

```text
$refinery-handoffを使い、project「project-a」の引き継ぎ「search-fix-01」を読んでください。
現在の成果物と照合し、目的と完了条件に沿って作業を再開してください。
```

資料には目的、完了条件、成果物の場所、branch・commit・未commit変更などの現在状態、
確認結果と限界、確定事項、仮説、未解決事項、関連ナレッジIDを残します。
既存の結論や承認に関する記述は過去の記録として扱い、今回の依頼と最新の成果物を基準に判断します。
参照先が移動・削除されていれば、その不足を示します。会話全体の再投入は行いません。

`agents/openai.yaml`の`policy.allow_implicit_invocation: false`により、Skillは明示呼び出し専用です。
`--agents`による自動運用の対象にも含めません。本体は作成・再開・整理を振り分け、必要な参照ファイル
だけを読みます。新しいチャットの作成は、対応するアプリ機能が利用可能で、別途依頼された場合に扱います。

## ライフタイム {#lifetime}

| 操作 | 結果 |
|---|---|
| 作成 | 新しいIDの`active`資料を保存する |
| 取得・再開 | 内容・状態を変更しない |
| 置き換え | 同じ`task_id`の旧版を`archived`にし、双方に新旧IDを残す |
| アーカイブ | 内容を保持し、既定の一覧から外す |
| 削除 | 指定した`archived`資料のファイルを削除する |

一つの作業に一つのactive資料を持ちます。独立した作業は別の`task_id`で扱います。
初回は`task_id`を省略すると`handoff_id`と同じ値になります。置き換え時は旧版から継承します。
本文・目的・完了条件の変更は新しいsnapshotとして保存し、状態だけを更新します。

自動期限・常時監視・バックグラウンド削除はありません。明示された再開依頼に「完了時にこの資料を
アーカイブする」と含めれば、同じSkillの処理内で終了時に整理できます。読み込みだけの依頼は整理を含みません。
削除では具体的な対象と影響について既存の依頼・承認を使い、未合意の場合だけ確認します。

アーカイブ済みの資料もID指定で取得できます。削除後も他の資料に残る新旧ID参照は履歴として保持し、
参照先が存在しない場合があります。削除はproduct file、experience、memory、Git履歴、外部backupを消しません。

## CLIで使う

すべてのhandoff commandはJSONを返します。作成・アーカイブ・削除は設定済みの利用repoから
実行するか、`--project /absolute/path/to/project`を付けます。一覧・取得は`--project-id`で
中央vaultのprojectを指定でき、ローカルrepoは不要です。`list`で指定を省略すると全projectを
対象にします。`get`には`--project-id`または従来の`--project`が必須です。両者は併用できません。

```bash
knowledge-refinery handoff create \
  --id search-fix-01 --task-id search-fix \
  --title '検索の不具合修正' \
  --goal '検索結果の欠落を直す' \
  --done-when '再現ケースの回帰テストが通る' \
  --body-file /tmp/search-handoff.md

knowledge-refinery handoff list
knowledge-refinery handoff list --project-id project-a
knowledge-refinery handoff get search-fix-01 --project-id project-a
knowledge-refinery handoff list --project-id project-a --include-archived --task-id search-fix
```

置き換えには`create --supersedes <旧ID> --expected-updated-at <取得した旧版のupdated_at>`を付けます。
新しい`--id`を指定し、目的・完了条件・本文も渡してください。アーカイブと削除も直前に取得した
revisionを使います。

```text
knowledge-refinery handoff archive <ID> --expected-updated-at <updated_at>
knowledge-refinery handoff delete <ID> --expected-updated-at <archived版のupdated_at>
```

一定期間前にアーカイブした資料の候補は次のように一覧できます。境界日時自体は含まず、
`archived_at`がそれより前の資料だけを返します。作成日や最終アクセス日は使いません。

```bash
knowledge-refinery handoff list --include-archived --archived-before 2026-09-01T00:00:00Z
```

## 保存と検証

保存先は`projects/<project_id>/handoffs/<handoff_id>.md`です。既存vaultでは初回保存時に領域を作るため、
再setupは不要です。新規setupでは空の領域も作成します。`.refinery` symlinkは不要です。

書き込みはproject内のhandoff操作をlockし、ファイルをatomic replaceします。置き換えでは新版の保存後に
旧版をアーカイブし、通常の書き込み失敗では新版を取り消して旧版を保持します。複数ファイルの変更全体は
OSの単一transactionではないため、強制終了や応答不明時には両IDの保存状態を確認します。
重複作成・古いrevision・active資料の直接削除は拒否します。保存領域や資料のsymlinkも拒否します。

通常検索、tag集計、deep search snapshotはhandoffを含みません。`refinery_validate`はhandoffのschemaと
配置も検査します。handoff一覧・更新は不正文書を検出すると停止し、部分的な一覧を削除候補と誤認させません。

API引数は[MCPリファレンス](mcp.md#handoff-tools)、保存形式は[YAML schema](schema.md#handoff)を参照してください。
