## Toggle the optional deep search tool

Deep search publication is user-wide and independent of a repository's enabled state. Inspect it
with `knowledge-refinery deep-search status --json`. Run
`knowledge-refinery deep-search enable --model MODEL [--reasoning-effort EFFORT]`
or `knowledge-refinery deep-search disable` only when the user explicitly asks to change tool
availability. Tell the user to restart the Knowledge Refinery MCP server or open a new task after a
visibility change. Use `knowledge-refinery deep-search model MODEL` to change only the configured
model and reset reasoning effort to the model default, or add `--reasoning-effort EFFORT` to set both.
Use `knowledge-refinery deep-search reasoning-effort EFFORT` to change only the effort and `--reset`
to restore the model default. The CLI validates model and effort compatibility against the refreshed
Codex catalog before saving it. Enabling the tool does not authorize a search or write knowledge.

If malformed deep search configuration prevents publication, repair `deep_search.enabled`,
`deep_search.model`, and optional `deep_search.reasoning_effort` while preserving the active vault and
unknown config keys. Never place the central vault
path, Codex instructions, or deep search policy in a product repository's `AGENTS.md`.
