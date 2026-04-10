# Repository Maintenance Guide

このリポジトリは refinery の配布テンプレートを管理する。

- 配布対象は `template/` 配下。
- 新規機能や方針変更は、まず `template/` を更新する。
- ルート `scripts/apply_template.py` は `template/` を他リポジトリへ展開するためのユーティリティ。
