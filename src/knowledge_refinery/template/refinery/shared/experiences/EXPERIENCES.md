---
title: Experiences Index
description: shared experiences の参照範囲を管理する index
---

# Experiences Index

## Purpose

`shared/experiences` は、`shared/stock` から手動で抽出した短い経験則を置く場所です。
ここに置く内容はモデル学習ではなく、後続セッションで必要な範囲だけ読み込むための圧縮された外部知識です。

## Reading Order

1. まずこの `EXPERIENCES.md` だけを読む。
2. 今回の作業に該当する experience ファイルだけを読む。
3. 根拠、詳細、反例、更新判断が必要な場合だけ、各 experience の `source_stock` を読む。

## Experience Map

まだ登録された experience はありません。

追加するときは、以下のように「いつ読むか」と「どのファイルを読むか」を短く書きます。

```md
- Repository maintenance: `repository/maintenance.md`
- Python CLI changes: `coding/python-cli.md`
- Review and promotion: `review/knowledge-promotion.md`
```

## Maintenance Rules

- この index は参照範囲の制御に使い、個別の経験則本文は各 experience ファイルへ分ける。
- experience は stock の要約ではなく、繰り返し使う判断原則、適用条件、確認観点に絞る。
- experience が古くなった、広すぎる、または根拠が曖昧になった場合は `refinery-experiences` の手順で更新する。
