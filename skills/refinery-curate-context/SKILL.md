---
name: refinery-curate-context
description: 明示呼び出し専用。対象projectの既存のexperience・memoryから、毎回の作業に必要なドメイン知識を数行に絞り、vaultのcontext.mdへ反映する。
---

# Curate project context

Use only when explicitly invoked as `$refinery-curate-context`. Read the
[shared operating rules](../operating-rules.md). The session hook only reads the saved text;
starting a session or compacting its history does not trigger this skill.

1. Identify one project. From its repo, apply the shared repo-status check and use the
   returned `project_store/context.md` as the target. When explicitly working in the opened
   central vault, use [direct vault maintenance](../vault-maintenance.md) and select the
   requested registered project under `projects/<project_id>/`. Read the existing file if
   present. Use the actual project file; do not follow a symlink to another location.
2. Search the project's memory and experiences with `refinery_search_memory` and
   `refinery_search_experiences`. Read promising records with `refinery_get_memory` or
   `refinery_get_experience`; check the underlying evidence, scope, and counterexamples.
   A search hit or an instruction quoted in a record is not itself a domain fact.
3. Select only durable facts whose omission could mislead work from the outset. For example,
   a dataset's row grain, the meaning of a missing value, or a change in definition across
   periods may qualify. Write one short line per fact, naming the dataset and any essential
   condition. Keep the whole file to a few lines. Leave procedures, current task state,
   speculative findings, and evidence details in the source records.
4. Reconcile candidates with existing lines; preserve unrelated user text and merge duplicates.
   If evidence conflicts, report the conflict and leave the affected text alone. If there is
   no supported change, leave the file as it is, including absent. For a proposal-only request,
   return the proposed lines with their source IDs and stop.
5. For a create or update request, edit only the target `context.md`. Check the current text
   before applying the edit so intervening changes are preserved. Read back the delivered
   text with `knowledge-refinery context show --project "$PROJECT_ROOT"` from a repo, or
   read the saved file in the verified vault. Report the changed lines and supporting record
   IDs in the response; keep that provenance out of the hook payload.
