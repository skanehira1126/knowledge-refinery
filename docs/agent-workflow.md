# エージェントへの頼み方

登録済みで有効なrepoでは、Pluginの固定hookが新規開始時と圧縮後に運用指示を届けます。
エージェントはその後の作業に応じて、ローカルの中央vaultを使います。通常の導入に`--agents`は不要です。

## 作業中に何が起きるか

| 作業中に得たもの・必要になったもの | エージェントの動作 |
|---|---|
| 過去の判断が設計・診断・比較に役立つ問い | 関連するmemoryとexperienceを検索する。同じ問いと根拠なら既に確認した結果を使う |
| 将来の選択や検証方法を変える試行、不採用理由、有用な失敗 | 結果・根拠・限界を一つのexperienceにまとめて保存し、読み戻す |
| 複数のexperienceに裏付けられた判断原則 | project memoryを作成する。既存原則は新しい根拠・反例に合わせて同じIDで改訂し、前提が失われたら理由を残してアーカイブする |
| 特定の場面で毎回知っておくべきprojectの前提や依存関係 | `refinery-curate-context`で、該当する配信先の本文を数行だけ更新する。前提が失われたら古い行を除く |

セッション開始や圧縮のたびに検索・保存を行う必要はありません。typoや書式だけの修正はそのまま進めます。
Skill名や目的を指定して依頼することもできます。検索・診断・候補の提案だけを依頼した場合は読み取りで完了します。[hook本文の管理](skills/refinery-curate-context.md)

作業の引き継ぎは自動運用の対象外です。`$refinery-handoff`（Claude Code では `/knowledge-refinery:refinery-handoff`）を明示して、作成・再開・整理を依頼します。
本体が必要な手順だけを参照し、通常のナレッジ検索には引き継ぎ資料を混ぜません。
具体例は[新しいチャットへの引き継ぎ](handoffs.md)を参照してください。

課題・TODOの管理は`refinery-issue`へ依頼します。たとえば「Knowledge Refineryにこの課題を
記録して」「project exampleの進行中issueを一覧して」と伝えると、SkillがCLIで操作します。
issueはvault単位であり、repo登録や有効化は不要です。ナレッジの自動運用設定によってissueを
自動作成・更新することはありません。詳細は[refinery-issue](skills/refinery-issue.md)を参照してください。

## 指示の適用範囲

Pluginの各`SKILL.md`は、共通の実行・承認・完了条件を
`skills/operating-rules.md`から読み、個別手順は各Skillで扱います。Experienceの記録と導入の詳細は、
該当操作のときだけ参照ファイルを読みます。タグ選択の共通規則は
`skills/knowledge-tags.md`に置き、タグを付けるときやtaxonomyを点検するときに読みます。
固定hookはrepoの有効設定を見て、新規開始・圧縮時にPlugin同梱の運用指示を返します。
project別の本文は入力時、ツールの実行前後、サブエージェント開始時にホストが接続済みMCPから取得します。
運用指示をファイルでも配布したい場合は`--agents`で日英のmanaged blockを
追加できます。記録形式やAPI操作はPlugin Skillが扱います。

実行環境の権限、アクセス制御、組織上の必須承認を守ったうえで、利用者の明示要件をSkillの
一般指針より優先します。検索・診断・提案だけの依頼では書き込まず、実行を依頼された操作は
許可済みの範囲で保存・検証まで進めます。結果を左右する不明点だけを質問し、独立した作業は続けます。
disabled、未準備、vault不一致はrepo-scopedなrefinery操作の制限であり、依存しない開発作業まで止めません。

## コピーして使える依頼例

### 導入する

```text
$refinery-projectを使って、このrepoをKnowledge Refineryへ登録してください。
変更できないproject IDの候補と、現在のactive vaultから切り替わるかを先に示し、
私が確認してからsetupしてください。
```

### 書き込まずに検索する

```text
Knowledge Refineryから、この設計判断に関係するproject memory、shared memory、
experienceを検索してください。今回はvaultへ書き込まないでください。
```

### Experienceを記録する

```text
$refinery-experienceを使って、今回の比較と不採用理由を一つのexperienceとして
記録してください。確認できた事実、解釈、限界、次の可能性を分け、secretや個人情報は
保存しないでください。
```

### Memoryを抽出する

```text
$refinery-memoryを使って、既存experienceからこのrepoで再利用できる原則を抽出してください。
shared memoryの候補になる場合は、書き込む前に根拠と適用範囲を提示してください。
```

### 状態だけを確認する

```text
$refinery-projectを使って、このrepoの状態を診断してください。設定変更や再有効化はせず、
active vault、project ID、enabled状態、失敗した検査だけを報告してください。
```

## 書き込みと確認の境界 {#write-approval-boundary}

- 検索、status、doctor、metadata取得は読み取りです。
- setupはrepoの`.refinery.yaml`と中央vaultのproject領域を作成し、指定したvaultを
  ユーザー全体のactive vaultにします。project IDは登録後に変更できないため、未設定repoでは
  IDとvault切り替えの有無を確認してから実行します。
- `vault init`もactive vaultを変更します。エージェントは初期化前に保存先と切り替えの影響を
  提示し、未承認の選択だけを確認します。正確なID・保存先・切り替えが既に明示承認されていれば
  同じ質問を繰り返しません。`--agents`や`--link`は、それぞれを利用者が明示的に希望した場合だけ追加します。
- Experienceとproject memoryは、利用者が明示的に記録を依頼した場合、または
  固定hookや適用中のrepo指示で自動運用が許可されている場合に、根拠の条件を満たせば保存・確認まで進めます。
  検索・診断・提案のみという明示要件がある場合は、自動運用でも書き込みません。
- 既存のproject・shared memoryは、エージェントが根拠に合わせて改訂・統合・アーカイブし、結果を読み戻します。
- shared memoryの新規作成・昇格とknowledge文書の削除は、候補、根拠、
  影響を提示し、利用者が確認してから行います。
- `enabled: false`は意図的な停止です。検索や記録のために暗黙で再有効化しません。
- CLIとMCPはvaultのGit commit、push、backupを自動実行しません。Git履歴が必要な場合は
  vaultで`git init`し、差分確認後にvault Gitだけをcommitします。

必要な承認を求める前に、実施できる調査、根拠確認、候補や差分の作成を済ませます。
同じ候補と影響への既存承認は再利用し、一般的な保守依頼を個別の削除・昇格への承認とは扱いません。
指示を理由に停止する場合は、対象fileへのlinkと該当文、どう適用されるかを短く示し、
明示された要求とagentの解釈を区別します。

## 完了と検証

通常の記録や指定対象の事実修正は保存結果を読み戻して確認します。vault全体のvalidationは
全体監査、schema・provenanceの修復、具体的な整合性の懸念がある場合に行い、必須確認が
通った後は新しい変更・失敗・未解決点がない限り繰り返しません。`refinery_validate`は常に
active vault全体を検査しますが、対象外の不備を見つけても修復範囲を暗黙に広げません。
記録のためだけにproductの実験を再実行せず、既存evidenceと限界を明記します。

完了報告は結果、保存IDやpath、検証、残る制約を簡潔に示します。記録本文の必須構造・根拠・限界は
省略せず、sourceの保存とcommit・push・backupの実施状況を分けて伝えます。

## 保存してはいけない情報

Experience、memory、project metadata、tag説明へsecret、credential、token、個人情報、
顧客データを保存しません。logやerror messageは必要な箇所だけを残し、機密値を除去します。
Evidenceは既定ではpathやURIへの参照であり、参照先の安全性も確認します。記録後はvaultの
差分を確認してからcommitまたはpushしてください。

## 自動運用を停止・再開する

Codexでは `/hooks` で `context guidance-hook` だけを無効にできます。以降の新規セッションでは、
project固有のcontext配信とSkillの明示呼び出しを使い続けられます。過去に`--agents`で追加した
ファイル内の指示も読み込まれる環境では、その指示は引き続き適用されます。[Codexのhook設定](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)

既存のrepoを固定hookだけの運用に移す場合は、`AGENTS.md`（Claude Codeでは`CLAUDE.md`）の
`<!-- knowledge-refinery:agents:start … -->`から`<!-- knowledge-refinery:agents:end -->`までを取り除くと、共通指示の重複を解消できます。

repo全体の連携を止めるには`project disable`、再開には`project enable`を使います。
中央vaultのknowledgeとproject固有のcontext本文はどちらの操作でも保持されます。
