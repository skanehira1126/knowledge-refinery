---
name: refinery-curate-context
description: 有効なprojectで、作業中に判明・変更された前提や他projectとの依存関係を、必要なhookで届く短い本文に整える。候補の提案や配信内容の参照・更新にも使う。
---

# Curate project hook context

Read the [shared operating rules](../operating-rules.md). Maintain hook text by default
when work in an enabled project establishes or invalidates a fact that will change future
decisions at that hook. Search, diagnosis, and proposal-only requests remain read-only.
Use the MCP management tools to edit a target's Markdown. The host calls
`refinery_deliver_context` at the matching event. At startup and after compaction the plugin
delivers its packaged operating instructions through a fixed command.

1. Apply the repo-status check and pass the absolute repo root as `project_path` to the MCP
   tools. Use `refinery_list_contexts` to discover targets when needed. For explicitly requested
   work in an opened vault, use the selected project's [vault context](../vault-maintenance.md).
2. Check relevant project memory, experiences, or the current source, schema, or published
   interface. For a relationship between projects, verify the other project's ID, which
   side owns the artifact or contract, and what this project consumes. A shared tag only
   helps locate candidates. Leave disputed facts pending until their scope can be verified.
3. Choose the narrowest target where the fact is repeatedly needed. Use
   `SubagentStart` for a delegated worker's scope,
   `PreToolUse/<tool>` for an input or editing constraint, and `PostToolUse/<tool>` for
   interpreting the result. Reserve `UserPromptSubmit` for facts that affect every request.
   Write a few short lines stating the fact and its consequence. A trial's detailed evidence
   belongs in an experience, a reusable principle in memory, and task progress in a handoff.
   Link the source when it helps verify the premise. Leave unused targets unset.
4. Read the current body and revision together with `refinery_get_context`. Preserve
   unrelated lines. For a proposal-only request, return the target, proposed lines, and source
   IDs or paths. For an update, save with `refinery_update_context`, passing the revision just read as
   `expected_revision` (null for a new target). When the last applicable line is obsolete,
   pass `body: null` and its current revision to stop that delivery. On a conflict, reread
   and reconcile. Check the returned target, text, and revision and report the supporting evidence.
