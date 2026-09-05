# refinery-memory

反復または相補的な複数experienceから、繰り返し使える判断原則を抽出します。Project memoryは原則2件以上を根拠とし、利用者が明示依頼した1件の例外はscopeを狭め、limitsを記載し、confidenceをhighにしません。

提案のみなら候補・根拠・scope・limitsを返し、保存しません。memoryの原則・適用範囲・反例の扱いを
変える大幅な更新は、差分と根拠への明示承認を必要とします。同一候補への既存承認は再利用します。

Shared memoryは`project-id/experience-id`形式の実在する独立根拠を2 project以上から読み、候補の原則、scope、限界、反例、confidence、source IDを提示して、利用者の明示承認後だけ作成・昇格します。既存memoryの更新は直前の`updated_at`を要求し、optional fieldの省略は保持、空listはclear、confidenceは`clear_confidence: true`でclearします。機密情報と未redact logは保存しません。詳細なsource of truthは`skills/refinery-memory/SKILL.md`です。
