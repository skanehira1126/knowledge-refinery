---
title: Shared Stock Rules
description: shared/stock ディレクトリの運用ルール
kind: directory_rules
layer: stock
---

- このディレクトリには、検証済みで再利用可能な知識のみを保存する。
- 通常の knowledge 活用では `shared/stock` を参照し、`shared/review` は参照しない。
- review を通過し採用条件を満たした知識は、追加のユーザー確認なしでこのディレクトリへ反映してよい。
- 知識ファイルは原則 Markdown (`.md`) で管理する。
- 各ファイルの先頭に YAML front matter を付け、最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を記載する。知識の性質を区別したい場合は `knowledge_type: reference|constructive` も付ける。
- `tags` は再利用検索の主軸なので、原則 2-5 個付ける。`domain/...` または `artifact/...` に加えて、必要なら `task/...`, `tech/...`, `issue/...` を使う。
- `reference` は lookup しやすい短い形に保ち、`constructive` は why や適用条件を削りすぎない。
- 1ファイル1トピックを基本とする。
