---
title: Shared Stock Rules
description: shared/stock ディレクトリの運用ルール
kind: directory_rules
layer: stock
---

- このディレクトリには、検証済みで再利用可能な知識のみを保存する。
- 通常の knowledge 活用では `shared/stock` を参照し、`shared/review` は参照しない。
- 知識ファイルは原則 Markdown (`.md`) で管理する。
- 各ファイルの先頭に YAML front matter を付け、最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を記載する。
- 1ファイル1トピックを基本とする。
