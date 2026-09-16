# Archive or delete handoffs

Limit cleanup to the requested project, task, IDs, and conditions. No automatic expiry applies.
Archive hides a snapshot from the default list while preserving its content. Delete removes its
file; historical links in other handoffs remain as IDs and can become unavailable. Git history
and external backups, if present, are not erased by this operation.

For an age-based cleanup, list metadata with the intended `project_id`, `include_archived: true`
and, when useful, `archived_before: <ISO-datetime-with-timezone>`. The cutoff is exclusive and applies to
`archived_at`, not creation or last access. Add `task_id` to keep cleanup within one task.
There is no timer and listing never deletes anything.

Resolve candidates and exact-get the affected records before a mutation. A cleanup preview
ends with the candidates. A request to archive identified completed or abandoned work authorizes
archiving it. For deletion, show the concrete target and effect when these have not already been
approved. Honor an existing explicit request or agreed completion cleanup for those same targets;
do not ask again merely because this reference was read. Do not infer deletion from "resume",
"save", or a generic maintenance request.

Read candidates with `refinery_get_handoff(project_id, handoff_id)`. Before a mutation, resolve
the source repository, apply the repo-status gate, and confirm its project ID matches the selected
record. Cross-project discovery alone does not authorize cleanup of every listed project.

- Archive with `refinery_archive_handoff(project_path, handoff_id, expected_updated_at)` using
  the exact-get `header.updated_at`. Get it again and verify `status: archived` and preserved body.
- Delete with `refinery_delete_handoff(project_path, handoff_id, expected_updated_at)`. Only
  archived snapshots are accepted. For an explicitly requested deletion of an active snapshot,
  archive it first and use the returned revision. The API deletes only this one ID.
- Verify the returned `deleted: true` and that the ID is absent from the project list with
  `include_archived: true`. An error listing records is not proof of deletion.

On stale-revision errors, re-read and reconsider the affected state. On an uncertain deletion
response, verify the target's existence before retrying. Report changed IDs and remaining items;
do not delete referenced experiences, memories, product files, or another task's handoffs.

CLI fallback: `knowledge-refinery handoff archive <id> --project <absolute-project-path>
--expected-updated-at <revision>` and the same arguments with `delete`. Each command returns JSON.
