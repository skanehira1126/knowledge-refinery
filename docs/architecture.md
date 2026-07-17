# アーキテクチャ

```text
Codex surfaces
  └─ Global Plugin
      ├─ refinery-project / experience / memory / maintenance Skills
      └─ local stdio MCP (uv, frozen lock)
             │
             ├─ REFINERY_CONFIG or XDG config directory → active vault
             └─ central vault Git
                 ├─ projects/<project_id>/project.yaml
                 ├─ projects/<project_id>/experiences
                 ├─ projects/<project_id>/evidence
                 ├─ projects/<project_id>/memory
                 └─ shared/memory

Product repo
  ├─ .refinery.yaml → project_id + enabled
  └─ AGENTS.md → optional managed workflow block (`project setup --agents`)
```

## 境界

- PluginとMCPはユーザー単位でグローバルに1つ導入します。
- active vaultはユーザー設定に1つ持ちます。設定ファイルは `REFINERY_CONFIG` で明示でき、未指定時は `${XDG_CONFIG_HOME:-$HOME/.config}/knowledge-refinery/config.yaml` を使います。`REFINERY_VAULT` でactive vaultを一時overrideできます。
- repo-scoped MCP toolsは `project_path` を受け、server側で `enabled` とproject登録を検証します。
- symlinkは人間の閲覧用であり、MCPとCLIの必須依存ではありません。
- vault markerのmanagerとschemaを利用前に検証し、未対応schemaへの書き込みを拒否します。
- 中央vaultの書き込みはatomic replaceとpath lockで破損を防ぎ、project metadata、experience、memoryの更新は`expected_updated_at`による楽観的排他で競合上書きを拒否します。
- 検索は不正文書を隔離し、exact getは対象IDの正規pathを直接検証します。不正文書の一覧は `refinery_validate` が返します。

## データフロー

1. Skillが `project status` でrepoの有効性を確認する。
2. MCPが `project_path` からproject IDを導出する。
3. domain処理がproject metadataまたはknowledge文書のYAML schemaとprovenanceを検証する。
4. storage層が中央vaultへatomicに保存する。
5. refinery Gitがknowledge履歴をproduct Gitとは別に追跡する。
