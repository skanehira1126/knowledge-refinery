# refinery skills overview

このドキュメントは、refinery で配布する skill 群の関係と役割をまとめた overview です。
セッション運用の中心は 4 つの skill で構成し、`refinery-repair` と `refinery-stock` は保守系の補助 skill として扱います。

## Skill map

```text
refinery-session
  -> refinery-capture
  -> refinery-curation
  -> knowledge-refinery skills prepare-review / knowledge-refinery skills refresh-review
  -> refinery-shared

refinery-repair
  -> front matter / meta.yaml が壊れたときに横断的に介入

refinery-stock
  -> shared/stock の棚卸し
  -> stock 反映済み flow の掃除
```

## Overview

refinery の skill は、知識を次の順序で扱います。

1. `refinery-session` が session の開始、再利用、知識化のタイミング、review 準備を管理する。
2. `refinery-capture` が作業中の観測事実や証拠を `raw/` に軽量記録する。
3. `refinery-curation` が `raw/` の証拠を `flow/` の暫定知識に整理する。
4. `refinery-session` が `knowledge-refinery skills prepare-review` または `knowledge-refinery skills refresh-review` で review スナップショットを整える。
5. `refinery-shared` が `shared/review` を見て `shared/stock` への昇格可否を判断する。
6. 定期棚卸しでは `refinery-stock` が `shared/stock` と stock 反映済み `flow` の整理を担当する。
7. front matter や `meta.yaml` が壊れて CLI で読めない場合だけ `refinery-repair` を使う。

## Skill documents

- [refinery-session](./refinery-session.md)
- [refinery-capture](./refinery-capture.md)
- [refinery-curation](./refinery-curation.md)
- [refinery-shared](./refinery-shared.md)
- [refinery-stock](./refinery-stock.md)
- [refinery-repair](./refinery-repair.md)

## Recommended usage

日常運用では次の使い分けを基本にします。

- session の開始や終了整理は `refinery-session`
- 作業中の軽い記録は `refinery-capture`
- 区切りごとの知識整理は `refinery-curation`
- review から shared への昇格判断は `refinery-shared`
- stock の棚卸しと stock 反映済み flow の掃除は `refinery-stock`
- 壊れたファイルの修復は `refinery-repair`

## Example flow

```text
依頼開始
  -> refinery-session で session を開始
  -> 作業中に refinery-capture で raw を蓄積
  -> 区切りで refinery-curation で flow を更新
  -> 終了前に refinery-session で review を prepare / refresh
  -> refinery-shared で promote / reject を判断
  -> 定期棚卸しで refinery-stock を使って stock / flow を整理
  -> 壊れたファイルがあれば refinery-repair で復旧
```
