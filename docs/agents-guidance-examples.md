# AGENTS.md追記サンプル

`knowledge-refinery project setup` は、デフォルトでは `AGENTS.md` を作成・変更しません。Knowledge Refineryの共通ルールが必要なrepoでは、次のように明示します。

```bash
knowledge-refinery project setup \
  --target "$PROJECT_ROOT" \
  --vault "$REFINERY_VAULT" \
  --project-id my-project \
  --agents
```

`--agents` が追加するmanaged blockは、Knowledge Refineryを使うための共通ルールです。以下のサンプルは作業領域に固有の補足なので、必要なものだけを `AGENTS.md` のmanaged blockの外側へコピーしてください。外側に置くことで、`update-agents-md` を実行してもサンプル部分は上書きされません。

## データ分析

```markdown
## Knowledge Refinery: データ分析

- 分析を始める前に、指標の定義、対象期間、母集団、除外条件に関係するmemoryとexperienceを検索する。
- SQL、notebook、集計結果、グラフなど、結論を再検証できる参照をevidenceとして残す。
- 仮説が外れた分析、差が出なかった比較、データ品質上の制約も、次の分析で再利用できる場合はexperienceに記録する。
- 指標定義や集計条件を変更した場合は、旧定義との差分と判断理由を記録する。
- 相関を因果として扱わず、確認できた事実、解釈、未検証の仮説を分けて記述する。
```

## アプリケーション開発

```markdown
## Knowledge Refinery: アプリケーション開発

- 実装前に、対象機能、利用技術、既知の障害、過去の設計判断に関係するmemoryとexperienceを検索する。
- APIやschemaの変更、ライブラリ選定、設計案の比較では、採用案だけでなく不採用案とtrade-offもexperienceに残す。
- test結果、benchmark、再現手順、関連するdiffやcommitを、判断を裏付けるevidenceとして記録する。
- 一時的な回避策と恒久対応を区別し、残る制約やfollow-upを明記する。
- repo固有の実装規約はproject memoryに置き、複数repoで確認できた原則だけをshared memoryへ昇格する。
```

## 障害調査・運用

```markdown
## Knowledge Refinery: 障害調査・運用

- 調査開始時に、症状、error message、対象component、直近の変更に関連するexperienceを検索する。
- timeline、観測事実、試した診断、否定できた原因、根本原因を分けてexperienceへ記録する。
- log、metric、trace、実行commandの結果は、機密情報を除去したうえで参照可能なevidenceとして残す。
- 復旧を優先した操作と再発防止策を区別し、未完了のfollow-upを明記する。
- 未確認の推測を確定事項としてmemoryへ抽出しない。
```

## 調査・プロトタイピング

```markdown
## Knowledge Refinery: 調査・プロトタイピング

- 調査前に、類似技術、過去のprototype、既知の制約に関係するmemoryとexperienceを検索する。
- 比較条件と評価軸を先に定め、成功例だけでなく動かなかった手法や適用限界も記録する。
- prototypeの結果は、本番利用可能性が未確認であることを明示し、production-readyな結論と混同しない。
- 再現に必要なversion、設定、入力条件、測定結果をevidenceとして残す。
- 将来の採用判断に使える結論と、追加検証が必要な問いを分けて記述する。
```

## ドキュメント・仕様策定

```markdown
## Knowledge Refinery: ドキュメント・仕様策定

- 仕様を更新する前に、関連する設計判断、利用者feedback、過去の変更理由を検索する。
- 用語定義、対象範囲、非目標、互換性への影響を明確にする。
- 採用した仕様だけでなく、議論した選択肢、不採用理由、未解決事項をexperienceに残す。
- 実装や運用で検証されていない内容は、確定した原則としてmemoryへ抽出しない。
- 仕様と実装が食い違った場合は、どちらを正としたか、その判断根拠も記録する。
```

## 組み合わせ方

複数の領域にまたがるrepoでは、サンプルを丸ごと重ねるのではなく、必要な項目だけを一つのsectionへ統合します。たとえば分析基盤の開発では、データ分析の「指標・母集団・集計条件」と、アプリケーション開発の「schema変更・test・trade-off」を組み合わせます。

プロジェクト独自のルールには、具体的な保存場所、実行command、evidenceの参照方法を加えると運用しやすくなります。一方、token、個人情報、顧客データなどの機密情報そのものはexperienceやevidenceへ記録しないでください。
