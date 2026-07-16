# Git運用

Knowledge Refineryはproduct Gitと中央vault Gitのライフサイクルを分離します。
commit頻度、backup、validation、復旧を含む日常runbookは
[ナレッジ運用](knowledge-operations.md)を参照してください。

## 原則

- productのcommitやPRにexperience/memoryを混ぜない。
- knowledgeのためだけにuntracked product evidenceをcommitしない。
- vaultは独立Git rootにし、小さく意図の明確なcommitを作る。
- CLI/MCPはvaultへ書き込むが、Git commitやpushは自動実行しない。

## 推奨フロー

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"  # product repoで実行
REFINERY_VAULT="${HOME}/knowledge-refinery-vault"
PROJECT_ID="my-project"
EXPERIENCE_ID="validated-experiment"

knowledge-refinery doctor --target "$PROJECT_ROOT"
knowledge-refinery experience upsert \
  --project "$PROJECT_ROOT" \
  --experience-id "$EXPERIENCE_ID" \
  --title "Validated experiment" \
  --purpose "Preserve a reusable development finding" \
  --status completed \
  --body "The validated result and its limits."

knowledge-refinery memory upsert \
  --project "$PROJECT_ROOT" \
  --memory-id "validated-principle" \
  --title "Validated principle" \
  --summary "The reusable principle derived from the experiment." \
  --source-experience "$EXPERIENCE_ID"

git -C "$REFINERY_VAULT" status --short
git -C "$REFINERY_VAULT" diff --check
git -C "$REFINERY_VAULT" add "projects/${PROJECT_ID}"
git -C "$REFINERY_VAULT" commit -m "record ${PROJECT_ID} experiment"
```

shared memoryを更新した場合は、根拠となる複数projectのexperienceも同じvault Gitで追跡します。
