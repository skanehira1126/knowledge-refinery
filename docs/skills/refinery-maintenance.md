# refinery-maintenance

定期棚卸し・vault品質監査と、指定したナレッジ・metadata・taxonomyの修復を担当します。
全体監査ではvalidation、project metadata、evidence参照、重複・矛盾・陳腐化、taxonomyを点検します。
指定対象の修復では対象と根拠だけを調べ、無関係なprojectやmemoryの清掃へ広げません。

監査・提案のみなら書き込まず、修復依頼では結論を変えない根拠のある修正まで進めます。
Experience本文の更新は`refinery-experience`、memoryの作成・更新は`refinery-memory`へ委ねます。
Shared memory、knowledge削除、memoryの大幅な書き換えには具体案への承認が必要です。

指定したmetadataやtag説明の事実修正は、現在revisionで更新して読み戻し・差分確認まで行います。
Schema・provenanceの修復や全体監査で書き込んだ場合は、まとめて適用した後に再validationします。
`refinery_validate`は常にactive vault全体を検査し、対象を絞る引数はありません。対象外の既存エラーは
別途報告し、指定対象の修復・検証が済んでいればその依頼を完了できます。

Git未導入のvaultでは変更fileを確認し、その制約を報告します。機密値を報告や修復内容へ複製しません。
実施頻度、Git／backup、復旧手順は[ナレッジ運用](../knowledge-operations.md)、詳細なsource of truthは
`skills/refinery-maintenance/SKILL.md`を参照してください。
