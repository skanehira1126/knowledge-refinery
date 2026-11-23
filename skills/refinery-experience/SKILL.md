---
name: refinery-experience
description: Knowledge Refineryのナレッジ検索、または再利用できる試行・比較・失敗のexperience記録に使う。原則の抽出・改善はrefinery-memory、設定操作はrefinery-projectを使う。
---

# Refinery experience

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Input is the current repo or verified vault-maintenance context and a knowledge question or an
inspected attempt with its evidence. Search-only requests finish with relevant findings and source
IDs. Read the recording reference only when creating or updating an experience.

## Search

Search when explicitly requested, or when the project's operating instructions apply and past
knowledge could affect a design choice, diagnosis, comparison, or known constraint. Skip
unrelated lookups for mechanical edits and on startup or compaction alone.
Reuse relevant results already inspected while their sources and the question remain unchanged.

In a repository, search current project memory together with shared memory, then current project experiences.
Expand beyond the project only when the local result is insufficient: choose IDs with
`refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded
project set is defensible. Never combine `project_ids` with `all_projects: true`.

Ordinary memory search returns active principles. When investigating past decisions, use
`include_archived: true` or read the old ID with `refinery_get_memory`; its header gives the
archive reason and any successor.

In direct vault maintenance, retain the verified context and start with the requested project set
or shared scope. Select `vault_context.project_id` before writing a project's experience; no local
product repo or new registration is required.

## Record

Assess whether an inspected result could change a future agent's choice, avoidance, verification,
or diagnosis. Comparisons, rejections, informative failures, constraints, and reusable discoveries
qualify. Skip routine completion logs, progress summaries, obvious typo fixes, and repetitions with
no new evidence, condition, or counterexample. Rejected implementations and untracked evidence
can still support a useful record.

When recording is authorized under the shared rules, read [recording.md](references/recording.md).
Save the attempt, result and limits together. Update the same experience when new evidence
clarifies that attempt, and verify the saved record. Use results already inspected for the task.
If this and earlier experiences support a reusable decision or change an existing principle,
use `refinery-memory` with those source IDs.
