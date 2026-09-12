# refinery-experience

過去のナレッジ検索だけの依頼にも使用します。その場合は関連する結果とsource IDを返して完了し、
experience、metadata、tag説明を保存しません。記録は明示依頼または自動運用の許可がある場合に行います。

自動検索は過去の知識が設計判断・診断・比較・既知の制約に役立つときに行い、機械的な修正では
省略します。既に確認した同じ問いと根拠の結果は再利用します。検索はSkill本体で扱い、保存・更新時
だけ`skills/refinery-experience/references/recording.md`の記録手順を読みます。

将来の選択、回避、検証、診断を変え得る試行だけを、目的・試したこと・分かったこと・微妙だった点と限界・次の可能性を含む一つのexperienceとして保存します。routine完了logや新しい根拠のない反復は除外し、実装へ採用しなかった検証やuntracked evidenceは記録対象にします。

作成前にstable `experience_id`を決め、結果不明のcreateはexact getまたはID検索後にだけretryします。statusとconfidenceは[決定表](../knowledge-model.md#status-confidence)に従います。更新には直前の`updated_at`を使い、optional fieldの省略は保持、空listはclear、confidenceは`clear_confidence: true`でclearします。機密情報と未redact logは保存しません。詳細なsource of truthは`skills/refinery-experience/SKILL.md`です。

通常検索で足りず、複数文書の意味的な比較・統合・矛盾整理が必要な場合だけ、公開済みの
`refinery_deep_search`を利用できます。返却source IDをexact getで確認し、deep searchからknowledgeを
作成・更新しません。

記録する価値の判断はagent自身で行い、毎回利用者へ質問しません。通常の保存確認を終えたら完了し、
vault全体のvalidationは全体監査、schema・provenance修復、具体的な整合性の懸念がある場合に行います。
