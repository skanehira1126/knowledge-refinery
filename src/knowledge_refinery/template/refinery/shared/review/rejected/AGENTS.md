---
title: Rejected Review Rules
description: shared/review/rejected ディレクトリの運用ルール
kind: directory_rules
layer: review_rejected
---

- このディレクトリは review キューから外した rejected ファイルを保管する。
- rejected ファイルは通常の knowledge 活用では参照しない。
- 再審査するときは内容を見直したうえで `shared/review/` に戻すか、`flow` から `refresh-review` 相当の手順で再生成する。
