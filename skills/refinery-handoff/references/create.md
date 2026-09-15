# Create a handoff

Use existing task evidence and inspect the current artifacts where necessary. Keep the handoff
short enough to orient a fresh chat, with references for details. Do not rerun experiments only
to prepare the handoff. Separate confirmed facts, user constraints, provisional interpretations,
and unresolved questions. Record what a rejected attempt tested and under which conditions it
failed; do not turn it into a permanent prohibition.

Prepare `title`, `goal`, `done_when`, and a Markdown `body` containing:

- Current artifacts and work state: relevant repository-relative paths or resource URLs, branch
  and commit if known, uncommitted changes, and verification already performed and its limits.
- Confirmed constraints and decisions with their rationale; identify assumptions separately.
- Attempts and outcomes, remaining questions, and useful next checks.
- Relevant existing experience/memory IDs, including project or shared scope for exact retrieval.
  Say when there are no supporting records instead of inventing them.

Before saving, choose a lowercase slug `handoff_id` so an uncertain create response can be
reconciled by exact get. `task_id` identifies this unit of work; on the first snapshot it defaults
to `handoff_id`. Independent tasks have different task IDs. To replace an active handoff, first
get that exact record, then pass its ID as `supersedes` and its `header.updated_at` as
`expected_updated_at`. The task ID is inherited. Never replace the newest project record merely
because it is newest; identify the same task. Snapshot content is immutable: changes create a
new ID. Only lifecycle metadata changes in place.

Call `refinery_create_handoff(project_path, title, goal, done_when, body, handoff_id, ...)`.
It returns `{header, body, path}`. Read it back with `refinery_get_handoff` and check the saved
content. For a replacement, also verify the predecessor is archived and points to the new ID.
If the response is uncertain, retrieve both IDs before retrying; do not generate another ID
blindly. Report any incomplete replacement and preserve both records for reconciliation.

Return the handoff ID, task ID, vault-relative path, and a copyable prompt such as:

```text
$refinery-handoffを使い、このprojectの引き継ぎ「<handoff-id>」を読んでください。
現在の成果物と照合し、目的と完了条件に沿って作業を再開してください。
```

The prompt carries identity and intent; the handoff carries the task state. Create a new chat
only when separately requested and a supported app capability is available.

CLI fallback: `knowledge-refinery handoff create --project <absolute-project-path> --id <id>
--title <title> --goal <goal> --done-when <condition> --body-file <utf8-markdown-file>`.
Replacement adds `--supersedes <old-id> --expected-updated-at <old-revision>`.
