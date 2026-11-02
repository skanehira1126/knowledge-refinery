# Direct vault maintenance

Use this route when the user opens the central vault itself and requests an audit, cross-project
knowledge review, or repair. It manages knowledge already stored in that vault; it does not opt a
product repository into automatic search or recording. Never choose it automatically after a
repo-scoped access failure. The user must explicitly request vault administration.

1. Resolve the opened vault root to an absolute path and call `refinery_vault_status(vault_path)`.
   The path must resolve to the active vault and its marker must contain a valid `vault_id`.
   The CLI equivalent is `knowledge-refinery vault status --target "$VAULT_ROOT" --json`.
   Neither route registers the vault as a project, writes `.refinery.yaml`, or changes the active
   vault. A mismatch needs a separate, authorized configuration change through `refinery-project`.
2. Reuse the returned `vault_context` on knowledge, project-metadata, and tag tools, passing
   `project_path: null`. Never supply both a repository path and a vault context. The server checks
   the path and ID on every call; after a mismatch, inspect the intended vault rather than replacing
   the ID blindly. Pass the context to `refinery_list_projects` and `refinery_validate` as well.
3. Choose the requested scope. For searches use `project_ids` for a bounded set or `all_projects: true`
   for a vault audit. Shared-only memory search uses `scopes: [shared]`. To work within one registered
   project, set `vault_context.project_id` to its ID from the project list; default searches then
   include that project's records and shared memory. No local product repository is needed, even
   when it has moved or been disabled. Its opt-out remains unchanged.
4. Read experiences with qualified `project-id/experience-id` sources. Read memory using its `scope`
   and ID, with the result's `project_id` for project memory and no `project_id` for shared memory.
   Project metadata, experience writes, and project-memory writes require an explicit
   `vault_context.project_id`. Shared-memory writes use `shared: true`; omit the context's project
   ID when working only with shared knowledge. Tag browse/search needs a selected context project
   or `all_projects: true`; tag descriptions apply to the whole vault.
5. Continue the owning skill's evidence review, approval, revision, readback, and diff checks with
   this same context. A maintenance request is not approval of a concrete shared principle,
   material memory rewrite, or deletion. `refinery_validate` remains vault-wide even when the
   context contains a project ID. Handoff writes have no vault-context route.

The context is a target-identity check, not proof of user approval. Filesystem permissions and the
shared operating rules still apply. If the connected MCP lacks this interface, report the version
limitation; do not create a placeholder project or weaken a repository's configuration. The CLI
status command only inspects the entrypoint; knowledge maintenance through this route uses MCP.
