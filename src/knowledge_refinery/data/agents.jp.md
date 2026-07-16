## Knowledge Refinery

このリポジトリでは、開発中に得た再利用可能な経験をKnowledge Refineryで管理する。

- `.refinery.yaml` が `enabled: true` の場合だけ利用し、repo-scoped MCP toolsには現在repoの絶対パスを `project_path` として渡す。
- `enabled: false` は意図的なOFFとして扱い、検索や記録の依頼だけを理由に再有効化しない。再有効化は利用者の明示依頼または確認がある場合だけ行う。
- 作業開始時、判断に影響しそうな既存memoryとexperienceを検索する。
- meaningfulな検証、比較、不採用判断、失敗から知見を得た場合は `refinery-experience` skillを使う。
- experienceは目的、試したこと、分かったこと、微妙だった点、次の可能性を一つの記録にまとめる。
- 実装へ採用しなかったことや、evidenceがuntrackedであることを理由に記録を捨てない。
- evidenceを保存するためだけにプロダクトrepoへcommitしない。
- 複数experienceから繰り返し使える原則を抽出するときは `refinery-memory` skillを使う。
- project固有の原則はproject memory、複数projectで支持される原則だけをshared memoryへ保存する。
- 作業終了前に、今回の作業から記録すべきexperienceがないか確認する。
- 日次棚卸しでは `refinery-maintenance` skillを使う。
- プロダクトrepoとrefinery repoの変更を同じcommitやPRへ混ぜない。
