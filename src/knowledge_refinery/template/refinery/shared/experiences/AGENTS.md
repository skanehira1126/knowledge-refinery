---
title: Shared Experiences Rules
description: shared/experiences ディレクトリの運用ルール
---

# shared/experiences rules

- `shared/experiences` は、`shared/stock` の安定知識から手動で抽出した短い経験則を置く。
- `EXPERIENCES.md` は参照範囲を管理する index として使い、経験則の本文を詰め込みすぎない。
- 通常の作業開始時はまず `EXPERIENCES.md` を読み、関連する experience ファイルだけを読む。
- 詳細な根拠、反例、更新判断が必要な場合だけ、各 experience の `source_stock` を確認する。
- experience は true memory やモデル学習ではなく、後続セッションへ差し込む短い運用知識として扱う。
- experience を更新するときは `source_stock` を保ち、根拠のない一般化を避ける。
