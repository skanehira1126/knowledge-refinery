---
title: Shared Review Rules
description: shared/review ディレクトリの運用ルール
kind: directory_rules
layer: review
---

- このディレクトリは `flow` からコピーされた review 用スナップショットを置く。
- 通常の knowledge 活用では `review` を参照せず、`stock` を参照する。
- review ファイルは原則 Markdown (`.md`) で管理する。
- 各ファイルの先頭に YAML front matter を付け、最低でも `title`, `description`, `summary`, `knowledge_id`, `source_sessions`, `derived_from` を記載する。
- `review` から `stock` へ昇格するときもコピーで扱い、`flow` 側の作業物は残す。
