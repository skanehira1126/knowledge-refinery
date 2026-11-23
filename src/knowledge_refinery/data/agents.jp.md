## Knowledge Refinery

有効なprojectでは、作業中に次の条件を満たしたときに該当するPlugin Skillを使い、共通運用ルールに従う。セッション開始・圧縮は指示が届くタイミングであり、それだけで検索や保存を始めない。

- 設計判断、原因調査、手法比較、既知の制約などに過去の知識が役立つ場合は、`refinery-experience`で検索する。明示された検索依頼も対象とする。単純なtypo・書式変更など、過去の知識が判断に影響しない作業では省略し、同じ問いと根拠の検索結果は再利用する。
- 将来の選択、回避、検証、診断を変える試行・比較・不採用理由・有用な失敗は、`refinery-experience`で記録する。採用しなかった実装やuntracked evidenceも対象にし、定型的な完了logや新しい根拠のない反復は記録しない。
- 複数のexperienceが同じ判断原則を裏付けたら、`refinery-memory`でproject memoryを作成する。既存のproject・shared memoryは新しい根拠に合わせて同じIDで改訂する。後継が全範囲を引き継いだ場合や前提が失われた場合は、理由を残してアーカイブする。shared memoryを新規作成・昇格するときは候補と根拠を示し、明示承認を得る。
- 特定の場面で繰り返し必要なprojectの前提や依存関係が判明・変更されたら、`refinery-curate-context`で根拠を確認し、該当するhookの本文を数行で更新する。前提が解消したら古い行を除く。
- projectの名前、概要、検索用tag、主要技術が変わった場合は、`refinery-project`でmetadataを更新する。導入・設定変更・状態確認・診断も同Skillを使う。
- 定期棚卸しや依頼されたvault監査・ナレッジ修復は、`refinery-maintenance`を使う。通常の開発作業や単発の保存確認を理由に全体保守を始めない。
- handoffの作成・再開・整理は`$refinery-handoff`（Claude Codeでは`/knowledge-refinery:refinery-handoff`）を明示して依頼されたときだけ行う。
- 利用者の明示要件と実行環境の権限・必須承認を守る。検索・診断・提案のみの依頼では、この自動運用の許可があってもvaultへ書き込まない。knowledgeの削除にも具体的な対象への明示承認を必要とする。
- disabled・未準備・vault不一致ならrefinery操作だけを止め、依存しない依頼作業は続ける。設定修復は`refinery-project`で扱い、検索や記録の依頼だけを理由に再有効化しない。
- 許可済みの記録は保存結果の確認まで完了する。記録価値はagent自身で判断し、毎回の確認質問にしない。同じ候補・影響への既存承認は再利用し、承認待ちでも独立した作業を続ける。
