---
name: refinery-experiences
description: shared/stock から手動で短い experience を抽出し、shared/experiences と EXPERIENCES.md の参照範囲を整える skill。stock を毎回大量に読まず、後続作業で使う判断原則だけを圧縮したいときに使う。
---

# refinery-experiences skill

## Purpose

`shared/stock` に蓄積した安定知識から、後続セッションで繰り返し使う短い経験則を手動で抽出し、`shared/experiences` に整理する。

experience はモデル学習や true memory ではない。stock の詳細を毎回コンテキストへ入れずに済むよう、作業開始時に読む短い operating knowledge として扱う。

## Applicability

- `shared/stock` が増え、毎回読むには token が重くなってきたとき
- 複数の stock にまたがる判断原則、適用条件、確認観点を短く安定化したいとき
- `EXPERIENCES.md` の参照範囲を更新し、タスク別に読む experience を絞りたいとき
- 既存 experience が古くなった、広すぎる、または根拠 stock とずれてきたとき

## Workflow

1. `shared/experiences/EXPERIENCES.md` を読み、既存の参照範囲を確認する。
2. `knowledge-refinery knowledge search --scope stock` で関連 stock を探し、必要な stock 本文だけを読む。
3. 繰り返し使う判断原則、適用条件、確認観点だけを抽出する。単なる詳細、事例、根拠説明は stock に残す。
4. experience の配置先を domain や作業種別で決める。例: `repository/maintenance.md`, `coding/python-cli.md`, `review/knowledge-promotion.md`。
5. experience ファイルを手動で作成または更新し、front matter に `title`, `description`, `source_stock`, `confidence` を入れる。
6. `EXPERIENCES.md` の Experience Map に、いつその experience を読むかを短く追加または修正する。
7. 更新後、`EXPERIENCES.md` と対象 experience を読み直し、通常作業時に不要な stock まで読ませる導線になっていないか確認する。

## Experience File Format

```yaml
---
title: Repository Maintenance Experiences
description: knowledge-refinery リポジトリ保守時に再利用する経験則
source_stock:
  - constructive--template-update-policy
  - reference--knowledge-file-schema
confidence: medium
---
```

本文は次の構成を基本にする。

```md
## Principles

- 後続作業で毎回使う短い判断原則を書く。

## Apply When

- この experience を読むべき状況を書く。

## Check

- 作業中または終了前に確認する観点を書く。

## Escalate To Stock

- 詳細な根拠や反例を確認するために stock へ戻る条件を書く。
```

## Guardrails

- experience は stock の全文要約にしない。
- `EXPERIENCES.md` に経験則本文を溜め込まず、参照範囲の index に保つ。
- 根拠のない一般化を避け、必ず `source_stock` を残す。
- `source_stock` にない新しい事実を experience へ直接入れない。まず `flow` / `review` / `stock` の通常経路で安定化する。
- experience が長くなったら、複数ファイルへ分割するか、詳細を stock へ戻す。
- 古い experience を削除する場合は、ユーザ確認を取る。
