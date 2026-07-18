---
name: refinery-memory
description: Distill repeatedly useful principles from validated Knowledge Refinery experiences into project or shared memory with explicit provenance. Use when several experiences support a reusable rule, when existing memory needs refinement, or when deciding whether knowledge is project-specific or cross-project.
---

# Refinery memory

1. Resolve the current repository to an absolute `PROJECT_ROOT`, then run `knowledge-refinery project status --target "$PROJECT_ROOT" --json`. Never pass a literal placeholder path. Stop unless `ready` and `enabled` are true.
2. Pass the repository's absolute path as `project_path` to every repo-scoped MCP tool. Search existing memory before creating a new record; update a matching principle instead of duplicating it.
3. Read every supporting experience with `refinery_get_experience`. For cross-project evidence, pass the qualified `project-id/experience-id` source and check its evidence, applicability conditions, counterexamples, and confidence.
4. Keep project-specific principles in project memory. Use unqualified experience IDs for project memory. Use shared memory only when independent experiences from at least two projects support the principle; pass at least two sources in `project-id/experience-id` form.
5. Record with `refinery_record_memory`, include every supporting experience ID, and read the result back with `refinery_get_memory`.

Creating a new memory omits `expected_updated_at`. Updating an existing memory requires the exact `updated_at` returned by `refinery_get_memory`; pass it as `expected_updated_at`. If the server reports a stale revision, read the current memory again and reconcile the competing change instead of retrying blindly.

Write the reusable principle in `summary`. Put conditions, limits, counterexamples, and operational guidance in the body. Keep detailed attempt history in the source experiences.

Never create memory without `source_experiences`. Do not promote a one-off observation to shared memory, and do not silently overwrite a conflicting principle; preserve the conflict or ask for a decision.

Use knowledge tags with one to three lowercase slug segments separated by `/`, such as `domain/ml/feature-selection`. Prefer existing project tag branches when known; a parent tag search also matches its descendants.
