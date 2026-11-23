# refinery-memory

反復または相補的な複数experienceから、繰り返し使える判断原則を抽出します。Project memoryは原則2件以上を根拠とし、利用者が明示依頼した1件の例外はscopeを狭め、limitsを記載し、confidenceをhighにしません。

通常の作業では、エージェントが根拠を読んで既存のproject・shared memoryの原則・適用範囲・反例を同じIDで更新します。提案だけを依頼された場合は、候補・根拠・適用範囲・限界を返します。

後継が全範囲を引き継いだ場合や前提が失われた場合は、理由と任意の後継を付けてアーカイブし、旧IDで結果を確認します。[改訂とアーカイブの判断](../knowledge-operations.md#memory-lifecycle)

明示依頼または固定hookなどの運用指示のもとで、根拠の揃ったproject memoryをその作業中に保存・
読み戻しします。既存原則を裏付ける経験が増えたら同じIDに根拠を追加します。タグを付けるときだけ
`skills/knowledge-tags.md`を読み、語句検索または階層参照で
意味を確認した既存タグを再利用します。

Shared memoryは`project-id/experience-id`形式の実在する独立根拠を2 project以上から読み、候補の原則、scope、限界、反例、confidence、source IDを提示して、利用者の明示承認後だけ作成・昇格します。既存memoryの更新は直前の`updated_at`を要求し、optional fieldの省略は保持、空listはclear、confidenceは`clear_confidence: true`でclearします。機密情報と未redact logは保存しません。詳細なsource of truthは`skills/refinery-memory/SKILL.md`です。
