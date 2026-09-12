## Knowledge Refinery

This block authorizes automatic Knowledge Refinery use for reusable development experience.
Before refinery operations, read the relevant plugin skill and follow its shared operating rules
and the references needed for the task.

- Use `refinery-experience` to search when past knowledge could inform a design choice, diagnosis, comparison, or known constraint, and whenever a search is explicitly requested. Skip lookups for typo or formatting changes where past knowledge cannot affect the decision. Reuse results for an unchanged question and evidence.
- Use `refinery-experience` to record attempts, comparisons, rejections, or informative failures that could change a future choice, avoidance, verification, or diagnosis. Rejected implementations and untracked evidence qualify; routine completion logs and repetitions with no new evidence do not.
- Use `refinery-memory` to distill repeatedly useful principles from multiple experiences into project memory. Creating or promoting shared memory and materially rewriting memory require explicit approval of the concrete candidate and evidence.
- Use `refinery-project` to update metadata when the project name, summary, discovery tags, or principal technologies change. Use the same skill for setup, configuration changes, state checks, and diagnosis.
- Use `refinery-maintenance` for periodic reconciliation or requested vault audits and knowledge repairs. Ordinary development work or checking a single saved record does not trigger vault-wide maintenance.
- Respect explicit user requirements, runtime permissions, and required approvals. Search-only, diagnosis-only, and proposal-only requests remain read-only even with this automatic-operation authorization. Knowledge deletion also requires explicit approval of the concrete target.
- A disabled, unready, or mismatched repository blocks only refinery operations; continue independent user work. Route configuration repair to `refinery-project`, and never re-enable merely to satisfy a search or recording request.
- Complete authorized recording through checking the saved result. Assess recording value yourself instead of asking a routine user question. Reuse approval for the same candidate and impact, and continue independent work while another approval is pending.
