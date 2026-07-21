## Knowledge Refinery

Use Knowledge Refinery to preserve reusable experience from this repository.

- Use Knowledge Refinery only when `.refinery.yaml` has `enabled: true`, and pass the current repository's absolute path as `project_path` to repo-scoped MCP tools.
- Use repo-scoped tools only when status reports `vault_match: true`. On mismatch, stop and report the active vault; never hand-edit `vault_id` to bypass the binding.
- Treat `enabled: false` as an intentional opt-out. Never re-enable only to satisfy a search or recording request; require the user's explicit request or confirmation.
- For configuration repair, use the existing `refinery-project` skill and documented CLI commands only. Do not recommend a repair skill or command that is not present.
- When the project name, summary, discovery tags, or principal technologies change, read the current revision and partially update its central project metadata. Keep purpose/domain tags in lowercase kebab-case and technology names only in technologies.
- Search current project memory together with shared memory first, then current project experiences. Expand only when needed, first to selected `project_ids` and then to `all_projects: true`; never combine selected IDs with `all_projects: true`.
- Use `refinery-experience` after meaningful experiments, comparisons, rejections, or informative failures.
- Record only results that could change a future agent's choice, avoidance, verification, or diagnosis. Skip routine completion reports, progress logs, obvious typo fixes, and repetitions with no new evidence, condition, or counterexample.
- Keep purpose, attempts, findings, limitations, and future possibilities in one experience.
- Use `completed` for an evaluable result regardless of success, `inconclusive` when insufficient or conflicting evidence cannot answer the question, `abandoned` when work stops before an evaluable result, and `superseded` only after a later experience replaces the conclusion.
- Use high confidence for reproducible direct evidence under stated conditions, medium for direct but limited evidence, and low for partial or indirect evidence or important unresolved uncertainty.
- Choose a stable lowercase-slug `experience_id` before creation. After an ambiguous create outcome, exact-get or search that ID before retrying.
- Update existing experience or memory with the current revision. Omitted optional fields are preserved, an empty list explicitly clears a list, and `clear_confidence: true` clears confidence.
- Normal memory search includes active records only. When replacing one, save the active successor first, then mark the old memory `superseded` and link its same-scope `superseded_by`; use `retracted` when there is no successor.
- Before physically deleting knowledge, run delete without confirmation and present its revision, references, and validation errors. After explicit user confirmation, confirm the same revision only when `can_delete` is true.
- Do not discard an experience because its implementation was rejected or its evidence is untracked.
- Do not commit product files merely to preserve evidence.
- Use `refinery-memory` to distill repeatedly useful principles from experiences.
- Normally support project memory with at least two repeated or complementary experiences. Allow one source only on the user's explicit request; narrow the scope, state unverified limits, and do not use high confidence.
- Never create or promote shared memory automatically. Even with independent evidence from at least two projects, present the candidate principle, scope, limits, counterexamples, confidence, and source IDs, and wait for explicit user approval.
- Never store secrets, credentials, access tokens, PII or other personal data, customer data, or unredacted sensitive logs in the vault. Redact logs and evidence; when that cannot be done safely, record only a non-sensitive description and limitation.
- Before closing work, check whether the task produced a recordable experience.
- Use `refinery-maintenance` for daily reconciliation.
- Never mix product and refinery changes in one commit or pull request.
