# refinery-maintenance

定期棚卸し・vault品質監査と、指定したナレッジ・metadata・taxonomyの修復を担当します。
全体監査ではvalidation、project metadata、evidence参照、重複・矛盾・陳腐化、taxonomyを点検します。
指定対象の修復では対象と根拠だけを調べ、無関係なprojectやmemoryの清掃へ広げません。

中央vaultそのものを開いて保守を依頼できます。`refinery_vault_status`へvault rootの絶対パスを
渡し、返された`vault_context`を検索・更新へ引き継ぎます。この場合は`project_path: null`を
使い、vault自身のproject登録や保守専用repoは作成しません。CLIでの入口確認は
`knowledge-refinery vault status --json`です。各呼び出しでactive vaultのpathとIDを照合します。

検索は依頼されたproject集合、shared scope、または全体監査の範囲を指定します。projectの
metadata・experience・memoryを書くときはcontext内の`project_id`で保存先を明示します。
repoの無効化はこの中央管理と独立していますが、無効repoの通常操作からの自動迂回は禁止です。
APIの対象指定は[MCP tools](../mcp.md#vault-maintenance)を参照してください。

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
