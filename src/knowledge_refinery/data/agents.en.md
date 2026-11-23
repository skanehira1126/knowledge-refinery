## Knowledge Refinery

In an enabled project, use the relevant plugin skill and its shared operating rules when the
conditions below arise during the task. Startup and compaction deliver these instructions.
Neither event calls for a search or a write on its own.

- Use `refinery-experience` to search when past knowledge could inform a design choice, diagnosis, comparison, or known constraint, and whenever a search is explicitly requested. Skip lookups for typo or formatting changes where past knowledge cannot affect the decision. Reuse results for an unchanged question and evidence.
- Use `refinery-experience` to record attempts, comparisons, rejections, or informative failures that could change a future choice, avoidance, verification, or diagnosis. Rejected implementations and untracked evidence qualify; routine completion logs and repetitions with no new evidence do not.
- When multiple experiences support a reusable decision, use `refinery-memory` to create a project memory. Revise existing project and shared memories under the same ID as the evidence changes. Archive with a reason when a successor covers the full scope or the premise has disappeared. Present the candidate and evidence for explicit approval when creating or promoting a shared memory.
- When work establishes, changes or retires a project premise or dependency that repeatedly matters at a particular hook, use `refinery-curate-context`. Verify the source and update the few lines needed at that target, removing obsolete lines.
- Use `refinery-project` to update metadata when the project name, summary, discovery tags, or principal technologies change. Use the same skill for setup, configuration changes, state checks, and diagnosis.
- Use `refinery-maintenance` for periodic reconciliation or requested vault audits and knowledge repairs. Ordinary development work or checking a single saved record does not trigger vault-wide maintenance.
- Create, resume or clean up handoffs only on explicit invocation of `$refinery-handoff` (Claude Code: `/knowledge-refinery:refinery-handoff`).
- Respect explicit user requirements, runtime permissions, and required approvals. Search-only, diagnosis-only, and proposal-only requests remain read-only even with this automatic-operation authorization. Knowledge deletion also requires explicit approval of the concrete target.
- A disabled, unready, or mismatched repository blocks only refinery operations; continue independent user work. Route configuration repair to `refinery-project`, and never re-enable merely to satisfy a search or recording request.
- Complete authorized recording through checking the saved result. Assess recording value yourself instead of asking a routine user question. Reuse approval for the same candidate and impact, and continue independent work while another approval is pending.
