# refinery-maintenance

全projectのmetadata、recent experience、壊れたevidence参照、重複memory、shared memory候補を定期棚卸しします。現在projectとsharedから検索を始め、必要な場合だけselected projectまたはvault全体へ広げます。

依頼されたprojectやrecordの範囲を守ります。監査・提案のみなら書き込まず、修復依頼では結論を
変えない根拠のある修正まで進めます。書き込みはまとめて行った後に再validationし、読み取りだけなら
初回validationを不要に繰り返しません。Git未導入のvaultでは変更fileを確認し、その制約を報告します。

Project memoryは原則2件以上の根拠を要求し、1件の例外は利用者の明示依頼、狭いscope、limits、high未満のconfidenceを必要とします。Shared memoryは候補を提示し、利用者の明示承認後だけ作成・昇格します。機密値を報告や修復内容へ複製しません。実施頻度、Git／backup、復旧チェックリストは[ナレッジ運用](../knowledge-operations.md)、詳細なsource of truthは`skills/refinery-maintenance/SKILL.md`を参照してください。
