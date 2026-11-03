---
name: refinery-issue
description: Knowledge Refineryのissue（課題・TODO）の作成、一覧、進捗更新、project紐付け、タグ管理に使う。GitHub Issuesの操作、experience／memoryの記録、チャットの引き継ぎは対象外。
---

# Refinery issue

Read the [shared operating rules](../operating-rules.md) for authorization, vault-scoped access,
and completion. Input is the requested issue operation and its title, ID, or selection criteria.
Use the `knowledge-refinery issue` CLI; there are no issue MCP tools. Do not edit `issues.json`
directly. Skill discovery does not authorize creating issues from ordinary development findings
or from automatic experience/memory recording guidance.

## Select the scope

Use the active vault, or an explicitly requested existing vault through `REFINERY_VAULT`.
Issue commands do not infer a project from the working directory. `--project` takes a registered
project ID, not a path; creation may repeat it to link multiple projects or omit it for no project.
Use an already known binding or `refinery_list_projects` when a requested project needs resolving.
Do not set up a repository merely to access issues. Missing vault configuration belongs to
`refinery-project`; an issue request alone does not authorize initialization or a global switch.

Variables in the examples stand for concrete values from the request or CLI results.

## Find or inspect

```bash
knowledge-refinery issue list --json
knowledge-refinery issue list --project "$PROJECT_ID" --status in_progress --tag "$TAG" --json
knowledge-refinery issue show "$ISSUE_ID" --json
```

Apply only requested filters; they combine with AND. The list is newest-update first and includes
done/cancelled issues unless filtered. It omits history; `show` returns the full history.
Select by returned ID rather than guessing from a title. A read-only request ends with findings.

## Create or update

```bash
knowledge-refinery issue create --title "$TITLE" --description "$DESCRIPTION" \
  --done-when "$DONE_WHEN" --project "$PROJECT_ID" --tag "$TAG" --json
knowledge-refinery issue update "$ISSUE_ID" --expected-revision "$REVISION" \
  --status in_progress --reason "$REASON" --json
```

Only the title is required for creation. Omit optional fields without a supported value; do not
invent completion criteria. New issues start at `backlog`, revision `1`; retain the returned ID.

Before updating, read the issue and pass its current `revision` as `--expected-revision`. Change
only requested fields: `--title`, `--description`, `--done-when`, `--status`, `--add-project`,
`--remove-project`, `--add-tag`, or `--remove-tag`. Project/tag additions and removals are repeatable.
Omitted fields are preserved; `--description ""` explicitly clears the description.
On `issue_revision_conflict` (exit code 2), reread and reconcile the current content with the
requested change. Do not blindly retry with a newer revision.

States are `backlog`, `ready`, `in_progress`, `blocked`, `done`, and `cancelled`; reopening is allowed.
Every status change requires `--reason`. For `done`, ensure a nonempty `done_when` and put the
completion and verification evidence in `--reason`. The CLI checks presence, not whether the work
meets its criteria; do not claim unverified completion. There is no issue-delete command.

After a write, use `show` to verify the affected fields and history. Report the ID, status, revision,
and any remaining limitation. Recording an issue does not itself perform the work described in it.

## Maintain issue tags

Use `issue tag list [--project ID] --json` for used tags and counts. These are free-form,
case-sensitive issue labels, separate from knowledge taxonomy and its `issue/...` facet.
For one issue, use `issue update` with `--add-tag` or `--remove-tag`.

`issue tag rename OLD NEW --json` and `issue tag remove TAG --json` affect every project and status.
Before either, inspect `issue list --tag "$TAG" --json` and ensure that the requested scope covers
all matches; do not turn a project-specific request into a global mutation. Rename merges into an
existing destination tag; remove detaches the tag without deleting issues or history. Verify the
returned `affected_issues` with `show` and check the resulting tag counts with `issue tag list`.
