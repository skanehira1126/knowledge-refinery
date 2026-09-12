## Set up

Inspect `knowledge-refinery project status --target "$PROJECT_ROOT" --json` to establish the
current binding and active vault before preparing setup. An unconfigured repo is expected here.

1. Inspect the active vault and the user-selected absolute `VAULT_ROOT`. If no initialized vault exists there, prepare `knowledge-refinery vault init --root "$VAULT_ROOT"` for execution after step 3; `vault init` also changes the user-wide active vault.
2. Inspect stable repo-owned sources such as README files and package manifests. Derive a human-readable name, a one-sentence summary, focused lowercase kebab-case discovery tags for purpose or domain, and the principal technologies. Keep technology names out of tags. Never include secrets, local absolute paths, temporary task state, or unsupported guesses.
3. For an unconfigured repository, present the proposed immutable `PROJECT_ID`, `VAULT_ROOT`, derived metadata, and whether setup will switch the user-wide active vault. Require explicit user confirmation of the ID and vault transition before writing; an explicit choice or approval already given for those exact values satisfies this requirement. Ask only for the unresolved choice. Before any active-vault change, including for an existing repo, apply the same approval boundary.
4. Initialize the selected vault if needed, then run `knowledge-refinery project setup --target "$PROJECT_ROOT" --vault "$VAULT_ROOT" --project-id "$PROJECT_ID" --project-name "$PROJECT_NAME" --summary "$SUMMARY"`, repeating `--tag` and `--technology` for the selected metadata. The CLI rejects connecting an unconfigured repository to an ID already registered in the vault.
5. Add `--link` only when a human explicitly wants a `.refinery` browsing symlink.
6. `project setup` does not change repository guidance by default. Add `--agents` only when a human explicitly wants the managed guidance block appended. Check applicable repository guidance first: an `AGENTS.override.md` in the same directory takes precedence over `AGENTS.md`. If the edited file will not be loaded, report that limitation instead of claiming automatic mode is active or overwriting the override.
7. Verify with `knowledge-refinery doctor --target "$PROJECT_ROOT"`.
