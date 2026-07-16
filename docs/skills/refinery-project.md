# refinery-project

repoの導入、有効化、無効化、診断を担当するSkillです。手動編集ではなく `project setup / enable / disable / status` と `doctor` を使います。

ON/OFF操作は中央vaultのknowledgeを削除しません。disabledは正常なopt-outであり、検索・記録依頼から暗黙にenableしません。診断時は `refinery_info.version` をdoctorへ渡してPlugin/CLI driftも検査します。Skillのsource of truthは `skills/refinery-project/SKILL.md` です。
