# Knowledge Refinery

Knowledge Refineryは、Codexで得た開発経験と再利用可能な原則を、プロダクトrepoから
独立したローカル中央vaultで一元管理するCodex Pluginです。vaultはfilesystem directoryで、
必要に応じて独立したGit repositoryとして履歴管理します。

## 解決すること

- 不採用の試行、失敗、untrackedの検証結果も将来の判断材料として残す。
- 複数repoのexperienceを1つの中央vaultで検索する。
- repo固有のmemoryと、複数repoで検証されたshared memoryを分ける。
- Pluginはグローバルに一度導入し、repoごとに有効・無効を切り替える。
- 定型変更はCLIに寄せ、エージェントの手作業を減らす。

!!! important
    このリポジリ自身の作業記録にKnowledge Refineryは使いません。プロダクトGitと中央vault Gitのライフサイクルは常に分離します。

## 最初に読むページ

1. [導入手順](getting-started.md)でPlugin、CLI、vault、repoを設定する。
2. [エージェントへの頼み方](agent-workflow.md)で明示呼出と自動運用を選び、コピー可能な
   依頼例と承認境界を確認する。
3. [ナレッジモデルと検索](knowledge-model.md)でexperienceからmemoryへの昇華を理解する。
4. 継続的に利用する場合は[ナレッジ運用](knowledge-operations.md)でGit、validation、backupを
   設定する。

CLIとMCPはvaultのGit初期化、commit、push、backupを自動実行しません。また、secret、
credential、個人情報、顧客データをknowledgeへ保存しません。
