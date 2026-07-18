# Knowledge Refinery

Knowledge Refineryは、Codexで得た開発経験と再利用可能な原則を、プロダクトGitから独立したローカルGit vaultで一元管理するCodex Pluginです。

## 解決すること

- 不採用の試行、失敗、untrackedの検証結果も将来の判断材料として残す。
- 複数repoのexperienceを1つの中央vaultで検索する。
- repo固有のmemoryと、複数repoで検証されたshared memoryを分ける。
- Pluginはグローバルに一度導入し、repoごとに有効・無効を切り替える。
- 定型変更はCLIに寄せ、エージェントの手作業を減らす。

!!! important
    このリポジリ自身の作業記録にKnowledge Refineryは使いません。プロダクトGitと中央vault Gitのライフサイクルは常に分離します。

ナレッジの昇華フローと検索方法は[ナレッジモデルと検索](knowledge-model.md)、
初めて使う場合は[導入手順](getting-started.md)、継続的な保守を始める場合は
[ナレッジ運用](knowledge-operations.md)へ進んでください。
