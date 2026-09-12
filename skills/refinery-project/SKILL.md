---
name: refinery-project
description: Knowledge Refineryの導入・設定変更・状態確認・診断、仕組みの説明に使う。ナレッジ検索・記録やvault内の品質監査は対象外。
---

# Refinery project

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Choose only the requested operation below. An explanation
or diagnosis does not authorize setup or repair.

Use the `knowledge-refinery` CLI for lifecycle changes. Do not hand-edit managed files when the
CLI can perform the operation. Resolve the repository to an absolute `PROJECT_ROOT`; command
variables stand for concrete values selected by the user or returned by tools, never placeholders.

## Explain, inspect, or diagnose

- **Explanation:** use the relevant section or reference. Do not run local checks unless the question
  depends on the current repository or machine state.
- **State check:** run `knowledge-refinery project status --target "$PROJECT_ROOT" --json` and report
  the active vault, project ID, enabled state, and `vault_match`. A status-only request ends here.
- **Diagnosis or repair:** inspect status and run `knowledge-refinery doctor --target "$PROJECT_ROOT"`.
  When MCP is available, obtain `refinery_info.version` and pass it with `--mcp-version` to doctor.
  Report failed checks and apply only the requested repair using documented CLI commands.
  Version drift blocks refinery writes; continue permitted inspection until it is resolved.
  Do not repeat a successful preflight unless the relevant state changes.

`state=disabled` is an intentional opt-out. Re-enable only on the user's explicit request or
approval for that transition. Never hand-edit `vault_id` to bypass a mismatch.

## Set up

For repository setup or an active-vault change, read [setup.md](references/setup.md).

## Maintain project metadata

Read the current record with `refinery_get_project_metadata`, or
`knowledge-refinery project metadata show --target "$PROJECT_ROOT" --json` when MCP is unavailable.
Update only changed, stable identity or discovery facts. Keep purpose/domain tags lowercase
kebab-case and technology names in `technologies`; exclude local paths, temporary state, and guesses.

Prefer `refinery_update_project_metadata` with the current `updated_at` as `expected_updated_at`.
Send only changed fields: omission preserves values, while an empty `tags` or `technologies` list
clears it. With the CLI, `--clear-tags` and `--clear-technologies` are intentional clears.
Read back the result and verify that `project_id` is unchanged.

## Toggle use

- Enable with `knowledge-refinery project enable --target "$PROJECT_ROOT"` after the authorization
  above. Add `--agents` only when the user wants automatic operation.
- Disable with `knowledge-refinery project disable --target "$PROJECT_ROOT"`.
- Verify either transition with `knowledge-refinery project status --target "$PROJECT_ROOT"`.

Disable retains `.refinery.yaml` with `enabled: false` and all central-vault knowledge. Repository
offboarding does not authorize deleting vault data.

## Configure the optional deep search tool

For deep search publication, model, effort, or configuration repair, read
[deep-search.md](references/deep-search.md). These user-wide settings are independent of repo enablement.
