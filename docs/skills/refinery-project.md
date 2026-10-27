# refinery-project

repoの導入、project metadataの管理、有効化、無効化、診断を担当するSkillです。手動編集ではなく `project setup / metadata / enable / disable / status` と `doctor` を使います。

説明だけなら必要な文書や参照先を読み、現在の環境に依存する質問でなければlocal検査を実行しません。
状態確認は`project status`で完了し、詳細診断・修復で`doctor`を使います。
診断・説明のみなら変更しません。setupではimmutableなIDとactive vaultの選択を、`vault init`を
含む書き込みより先に確認します。同じ正確な値への明示承認があれば、そのまま実行・検証へ進みます。

ON/OFF操作は中央vaultのknowledgeを削除しません。disabledは正常なopt-outであり、検索・記録依頼から暗黙にenableしません。診断時は `refinery_info.version` をdoctorへ渡してPlugin/CLI driftも検査します。

Knowledge Refinery設定のrepairには、このpluginに存在する`refinery-project` Skillと文書化されたCLIだけを使います。存在しないrepair Skillやcommandを案内しません。Skillのsource of truthは `skills/refinery-project/SKILL.md` です。

導入の詳細は`skills/refinery-project/references/setup.md`を該当操作のときだけ読みます。
