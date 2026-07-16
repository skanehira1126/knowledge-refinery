# Repository Maintenance Guide

このリポジトリは、ローカルMCPサーバーを含むKnowledge Refinery Codex Pluginと、そのPython CLIを管理する。
このリポジトリ自身ではKnowledge Refineryを使って作業記録を管理しない。

## Source of truth

- Plugin manifestは `.codex-plugin/plugin.json`、MCP起動設定は `.mcp.json` を正とする。
- 配布するSkillは `skills/` 配下を正とする。
- MCP toolsは `src/knowledge_refinery/mcp_server.py`、experience/memoryのドメイン処理は `experience_ops.py`、中央vault管理は `vault_ops.py` に置く。
- 利用repoへ挿入するAGENTS managed blockは `src/knowledge_refinery/data/agents.jp.md` と `agents.en.md` で管理する。
- READMEの「利用repoのAGENTS.mdサンプル」は、上記managed blockの方針と同期させる。

## Change rules

- MCP toolの名前、引数、戻り値を変更した場合は、root Skill、README、`tests/test_mcp_server.py` も更新する。
- experience/memoryのYAML schemaを変更した場合は、検索、validation、README、テストを同時に更新する。
- 利用repoへSkillをコピーする設計へ戻さない。SkillはPluginから提供する。
- `.refinery` symlinkを必須にしない。利用repoの必須設定は `.refinery.yaml` の `project_id` とする。
- プロダクトGitと中央refinery Gitのライフサイクルを分離する。

## Verification

変更後は次を実行する。

```bash
bash scripts/validate.sh
```

スクリプトは `CODEX_HOME` を参照し、未設定の場合は `~/.codex` を使う。
