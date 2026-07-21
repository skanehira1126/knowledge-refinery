# refinery-memory

反復または相補的な複数experienceから、繰り返し使える判断原則を抽出します。Project memoryは原則2件以上を根拠とし、利用者が明示依頼した1件の例外はscopeを狭め、limitsを記載し、confidenceをhighにしません。

Shared memoryは`project-id/experience-id`形式の実在する独立根拠を2 project以上から読み、候補の原則、scope、限界、反例、confidence、source IDを提示して、利用者の明示承認後だけ作成・昇格します。既存memoryの更新は直前の`updated_at`を要求し、optional fieldの省略は保持、空listはclear、confidenceは`clear_confidence: true`でclearします。機密情報と未redact logは保存しません。詳細なsource of truthは`skills/refinery-memory/SKILL.md`です。

通常検索はactive memoryだけを返します。置換時はactiveな後継を先に保存してから旧memoryを`superseded`へ更新し、後継なしの撤回は`retracted`にします。物理削除はdry-runで参照とvalidationを確認し、利用者の明示確認後だけ同じrevisionへconfirmを付けます。
