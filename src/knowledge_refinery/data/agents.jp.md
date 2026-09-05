## Knowledge Refinery

このリポジトリでは、開発中に得た再利用可能な経験をKnowledge Refineryで管理する。

- このblockはKnowledge Refineryの利用に適用する。実行環境の権限・必須承認を守り、利用者の明示要件をSkillの一般指針より優先する。検索・診断・提案のみの依頼ではvaultへ書き込まない。
- `.refinery.yaml` が `enabled: true` の場合だけ利用し、repo-scoped MCP toolsには現在repoの絶対パスを `project_path` として渡す。
- statusの`ready`、`enabled`、`vault_match`がtrueの場合だけrepo-scoped toolsを使う。不一致・未準備の場合はrefinery操作を止めて状態とactive vaultを報告し、refineryに依存しない依頼作業は続ける。`vault_id`を手編集して回避しない。
- `enabled: false` は意図的なOFFとして扱い、検索や記録の依頼だけを理由に再有効化しない。再有効化は利用者の明示依頼または確認がある場合だけ行う。
- 設定を修復するときは、存在する `refinery-project` skillと文書化されたCLIだけを使い、存在しないrepair skillやcommandを案内しない。
- projectの名前、概要、検索用tag、主要技術が変わった場合は、現在revisionを取得して中央vaultのproject metadataを部分更新する。目的・領域のtagはlowercase kebab-case、技術名はtechnologiesだけに保存する。
- 作業開始時は、現在project memoryとshared memory、現在project experienceの順に検索する。足りない場合だけ、`project_ids`で選んだproject、さらに必要な場合だけ`all_projects: true`へ広げる。`project_ids`と`all_projects: true`は併用しない。
- meaningfulな検証、比較、不採用判断、失敗から知見を得た場合は `refinery-experience` skillを使う。
- 将来のagentの選択、回避、検証、診断を変える結果だけをexperienceにし、定型作業の完了報告、進捗log、明白なtypo修正、新しい根拠のない反復は記録しない。
- experienceは目的、試したこと、分かったこと、微妙だった点、次の可能性を一つの記録にまとめる。
- statusは、評価可能な結果なら成否を問わず`completed`、根拠不足や矛盾で答えが出ないなら`inconclusive`、評価前に停止したなら`abandoned`、後続experienceが結論を置換した場合だけ`superseded`とする。
- confidenceは、条件を明記した再現可能な直接根拠なら`high`、直接根拠はあるが反復や適用範囲が限定的なら`medium`、部分的・間接的な根拠または重要な未解決点があるなら`low`とする。
- 新規experienceは安定したlowercase slugの`experience_id`を先に決める。結果不明のcreateをretryする前にexact getまたはID検索で保存済みか確認する。
- 既存experience/memoryの更新は現在revisionを使う。optional fieldの省略は保持、空listは明示clear、confidenceのclearは`clear_confidence: true`とする。
- 実装へ採用しなかったことや、evidenceがuntrackedであることを理由に記録を捨てない。
- evidenceを保存するためだけにプロダクトrepoへcommitしない。
- 複数experienceから繰り返し使える原則を抽出するときは `refinery-memory` skillを使う。
- project memoryは原則として反復または相補的な2件以上のexperienceを根拠にする。利用者が明示依頼した場合だけ1件を許し、scopeを狭め、未検証の限界を本文へ書き、confidenceを`high`にしない。
- shared memoryは異なる2 project以上の独立した根拠があっても自動作成しない。候補の原則、scope、限界、反例、confidence、source IDを提示し、利用者の明示承認後だけ作成・昇格する。同一候補に対する既存承認は再確認せず、内容や影響が変わった場合だけ確認する。
- knowledgeの削除やmemoryの原則・適用範囲を変える大幅な書き換えも、具体的な差分と根拠への明示承認を必要とする。確認待ちでは独立した作業を続け、停止の根拠となる指示fileへのlinkと該当文、適用理由を短く示す。
- secret、credential、access token、PII（個人情報）、顧客data、redactしていない機密logをvaultへ保存しない。logやevidenceは機密値を除去し、安全にできない場合は非機密の説明と限界だけを残す。
- 作業終了前に、今回の作業から記録すべきexperienceがないかagent自身で判断する。定型的な確認質問にはしない。
- 日次棚卸しでは `refinery-maintenance` skillを使う。
- 通常の記録は保存結果を確認して完了し、vault全体のvalidationは保守時または具体的な整合性懸念がある場合に行う。必要な確認が通った後は、新しい変更・失敗・未解決点がある場合だけ追加検証する。
- プロダクトrepoとrefinery repoの変更を同じcommitやPRへ混ぜない。
