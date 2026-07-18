# refinery-experience

将来の選択、回避、検証、診断を変え得る試行だけを、目的・試したこと・分かったこと・微妙だった点と限界・次の可能性を含む一つのexperienceとして保存します。routine完了logや新しい根拠のない反復は除外し、実装へ採用しなかった検証やuntracked evidenceは記録対象にします。

作成前にstable `experience_id`を決め、結果不明のcreateはexact getまたはID検索後にだけretryします。statusとconfidenceは[決定表](../knowledge-model.md#status-confidence)に従います。更新には直前の`updated_at`を使い、optional fieldの省略は保持、空listはclear、confidenceは`clear_confidence: true`でclearします。機密情報と未redact logは保存しません。詳細なsource of truthは`skills/refinery-experience/SKILL.md`です。
