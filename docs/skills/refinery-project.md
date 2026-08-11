# refinery-project

repoの導入、project metadataの管理、有効化、無効化、診断を担当するSkillです。手動編集ではなく `project setup / metadata / enable / disable / status` と `doctor` を使います。

ON/OFF操作は中央vaultのknowledgeを削除しません。disabledは正常なopt-outであり、検索・記録依頼から暗黙にenableしません。診断時は `refinery_info.version` をdoctorへ渡してPlugin/CLI driftも検査します。

Knowledge Refinery設定のrepairには、このpluginに存在する`refinery-project` Skillと文書化されたCLIだけを使います。存在しないrepair Skillやcommandを案内しません。Skillのsource of truthは `skills/refinery-project/SKILL.md` です。

任意のdeep search tool公開状態も担当します。`deep-search enable --model MODEL / disable`は
user-wide設定であり、明示依頼がある場合だけ変更し、公開状態変更後のMCP再起動を案内します。
modelはCLIがCodex catalogへ照合してから保存します。
