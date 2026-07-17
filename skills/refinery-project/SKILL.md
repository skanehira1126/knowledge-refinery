---
name: refinery-project
description: Set up, describe, enable, disable, inspect, or diagnose Knowledge Refinery for a repository while preserving the central vault. Use when onboarding or offboarding a repository, creating or updating central project metadata, selecting its vault, repairing `.refinery.yaml`, updating the managed AGENTS block, or troubleshooting the local MCP connection.
---

# Refinery project

Use the `knowledge-refinery` CLI for lifecycle changes. Do not hand-edit managed files when the CLI can perform the operation.

Resolve the current repository to an absolute path and refer to that value as `PROJECT_ROOT`. Use `VAULT_ROOT`, `PROJECT_ID`, and `MCP_VERSION` below only as names for concrete values already selected or returned by tools. Never pass unresolved placeholder tokens to a command.

## Inspect before changing

1. Run `knowledge-refinery project status --target "$PROJECT_ROOT"`.
2. Run `knowledge-refinery doctor --target "$PROJECT_ROOT"` when status is unhealthy or the MCP tools are unavailable.
3. Report the active vault, project ID, enabled state, and failed checks before applying a repair.
4. When MCP is available, set `MCP_VERSION` to `refinery_info.version` and pass it to `knowledge-refinery doctor --target "$PROJECT_ROOT" --mcp-version "$MCP_VERSION"`. Stop and report version drift before writing.

`state=disabled` is a healthy, intentional opt-out state, not damage to repair. Never run `project enable` merely to satisfy a search or recording request. Enable only when the user explicitly asks to re-enable the repository or explicitly confirms that transition after you report the disabled state.

## Set up

1. Require an initialized central vault. If none exists, run `knowledge-refinery vault init --root "$VAULT_ROOT"` with the user-selected absolute vault path.
2. Inspect stable repo-owned sources such as README files and package manifests. Derive a human-readable name, a one-sentence summary, focused discovery tags, and the principal technologies. Never include secrets, local absolute paths, temporary task state, or unsupported guesses.
3. Run `knowledge-refinery project setup --target "$PROJECT_ROOT" --vault "$VAULT_ROOT" --project-id "$PROJECT_ID" --project-name "$PROJECT_NAME" --summary "$SUMMARY"`, repeating `--tag` and `--technology` for the derived values.
   Treat `PROJECT_ID` as immutable. The CLI rejects connecting an unconfigured repository to an ID already registered in the vault.
4. Add `--link` only when a human explicitly wants a `.refinery` browsing symlink.
5. `project setup` does not change repository guidance by default. Add `--agents` only when a human explicitly wants the managed guidance block appended.
6. Verify with `knowledge-refinery doctor --target "$PROJECT_ROOT"`.

## Maintain project metadata

1. Read the current record with `refinery_get_project_metadata`, or use `knowledge-refinery project metadata show --target "$PROJECT_ROOT" --json` when MCP is unavailable.
2. Update metadata only when stable project identity or discovery facts changed. Preserve accurate existing values and keep tags focused enough to help choose cross-project search scope.
3. Prefer `refinery_update_project_metadata` and pass the current `updated_at` as `expected_updated_at`. With the CLI, pass the same revision to `project metadata update` and provide the complete replacement name, summary, tags, and technologies.
4. Read the result back and verify that `project_id` is unchanged.

## Toggle use

- Enable with `knowledge-refinery project enable --target "$PROJECT_ROOT"` only after the explicit authorization above.
- Disable with `knowledge-refinery project disable --target "$PROJECT_ROOT"`.
- Verify either transition with `knowledge-refinery project status --target "$PROJECT_ROOT"`.

Treat disable as reversible. It must retain `.refinery.yaml` with `enabled: false` and preserve every document in the central vault. Do not delete vault data as part of repository offboarding. When disabled, do not call Knowledge Refinery MCP tools for that repository.

Never combine product-repository commits with central-vault commits.
