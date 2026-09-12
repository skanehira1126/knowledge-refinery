---
name: refinery-experience
description: Knowledge Refineryのナレッジ検索、または再利用できる試行・比較・失敗のexperience記録に使う。原則の抽出・改善はrefinery-memory、設定操作はrefinery-projectを使う。
---

# Refinery experience

Read the [shared operating rules](../operating-rules.md) for authorization,
blocked operations, and completion. Input is the current repo and a knowledge question or an
inspected attempt with its evidence. Search-only requests finish with relevant findings and source
IDs. Read the recording reference only when creating or updating an experience.

## Search

Search when explicitly requested, or when opted-in repository guidance calls for past knowledge
that could affect a design choice, diagnosis, comparison, or known constraint. Ordinary development
work does not need a search merely because it started; skip unrelated lookups for mechanical edits.
Reuse relevant results already inspected while their sources and the question remain unchanged.

Search current project memory together with shared memory, then current project experiences.
Expand beyond the project only when the local result is insufficient: choose IDs with
`refinery_list_projects` and pass `project_ids`; use `all_projects: true` only when no bounded
project set is defensible. Never combine `project_ids` with `all_projects: true`.

Use available `refinery_deep_search` only when deterministic search is insufficient and the question
benefits from semantic synthesis, comparison, or contradiction analysis. The server selects the
configured model. Treat the answer as generated synthesis and exact-get its source IDs before a
consequential decision. Deep search never records or updates knowledge.

## Record

Assess whether an inspected result could change a future agent's choice, avoidance, verification,
or diagnosis. Comparisons, rejections, informative failures, constraints, and reusable discoveries
qualify. Skip routine completion logs, progress summaries, obvious typo fixes, and repetitions with
no new evidence, condition, or counterexample. Rejected implementations and untracked evidence
can still support a useful record.

When recording is explicitly requested or authorized by opted-in guidance, read
[recording.md](references/recording.md), save the integrated experience, and verify it. This value
judgment does not require a routine question to the user. Search needed for the record can reuse
the relevant results from the current task.
