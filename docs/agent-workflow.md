# エージェントへの頼み方

Knowledge Refineryには、必要なときだけSkillを呼ぶ「明示呼出モード」と、repoの
`AGENTS.md`へ共通ルールを追加する「自動運用モード」があります。どちらのモードでも、
保存先はローカルの中央vaultです。

## 2つの利用モード

| モード | 向いている使い方 | 有効にする方法 |
|---|---|---|
| 明示呼出 | 検索や記録を必要なtaskだけで行う | setupを既定のまま実行し、依頼時にSkill名または目的を伝える |
| 自動運用 | 通常の開発taskでも開始時の検索と終了前の記録判断を行う | `project setup --agents` でmanaged guidanceを追加する |

`--agents` を指定しない場合、repoを登録しただけでは、通常の開発依頼で必ずKnowledge
Refineryが使われるわけではありません。「新しいtaskを開くだけ」で運用できるのは、
managed guidanceを追加した自動運用モードです。

## コピーして使える依頼例

### 導入する

```text
$refinery-projectを使って、このrepoをKnowledge Refineryへ登録してください。
変更できないproject IDの候補と、現在のactive vaultから切り替わるかを先に示し、
私が確認してからsetupしてください。自動運用モードにするためAGENTS.mdも更新してください。
```

明示呼出モードにする場合は、最後の文を「AGENTS.mdは変更しないでください」へ置き換えます。

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

## 書き込みと確認の境界

- 検索、status、doctor、metadata取得は読み取りです。
- setupはrepoの`.refinery.yaml`と中央vaultのproject領域を作成し、指定したvaultを
  ユーザー全体のactive vaultにします。project IDは登録後に変更できないため、未設定repoでは
  IDとvault切り替えの有無を確認してから実行します。
- Experienceとproject memoryは、利用者が明示的に記録を依頼した場合、または
  `--agents`で自動運用を選んだ場合に記録対象となります。
- shared memoryの新規作成、memoryの大幅な書き換え、knowledge文書の削除は、候補、根拠、
  影響を提示し、利用者が確認してから行います。
- `enabled: false`は意図的な停止です。検索や記録のために暗黙で再有効化しません。
- CLIとMCPはvaultのGit commit、push、backupを自動実行しません。Git履歴が必要な場合は
  vaultで`git init`し、差分確認後にvault Gitだけをcommitします。

## 保存してはいけない情報

Experience、memory、project metadata、tag説明へsecret、credential、token、個人情報、
顧客データを保存しません。logやerror messageは必要な箇所だけを残し、機密値を除去します。
Evidenceは既定ではpathやURIへの参照であり、参照先の安全性も確認します。記録後はvaultの
差分を確認してからcommitまたはpushしてください。

## 自動運用を停止・再開する

`project disable`は`.refinery.yaml`を`enabled: false`にし、managed guidanceを削除しますが、
中央vaultのknowledgeは保持します。再開時に自動運用へ戻す場合は`project enable --agents`、
明示呼出モードで戻す場合は`project enable`を使います。
