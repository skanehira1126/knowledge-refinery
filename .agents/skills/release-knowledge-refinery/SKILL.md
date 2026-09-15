---
name: release-knowledge-refinery
description: Prepare and publish versioned GitHub Releases for the Knowledge Refinery repository. Use when asked to bump the Plugin/CLI version, prepare a release pull request, create and push a version tag, publish GitHub Release notes, or verify the release CI and documentation deployment.
---

# Release Knowledge Refinery

Release this repository through a validated pull request, an immutable tag on the merged commit,
and a published GitHub Release. Do not publish to PyPI.

## Interpret the request

- For “prepare a release”, stop after the release PR is green and report what remains.
- For “release” or “publish”, treat the request as authorization to ready and merge the release PR,
  push the tag, and publish the GitHub Release after all checks pass.
- Use an explicitly requested version. Otherwise infer SemVer from the release contents: use a patch
  for compatible fixes/features and the next minor version for a breaking change while pre-1.0.
- Never change a knowledge or vault `schema_version` merely because the package version changes.

## Inspect before changing

1. Confirm this is the Knowledge Refinery repository from `.codex-plugin/plugin.json` and
   `pyproject.toml`.
2. Check `git status -sb`, the current branch, `git remote -v`, `gh --version`, and
   `gh auth status`.
3. Fetch `origin` and confirm the local default branch is not ahead of or behind `origin/main`.
4. Preserve unrelated files. In particular, never stage `.refinery.local.yaml` or `uv.lock`.
5. Confirm that the intended tag and GitHub Release do not already exist.

## Prepare the version

1. Create `codex/release-v<version>` from the current `origin/main`.
2. Keep these package-version representations synchronized:
   - `src/knowledge_refinery/__init__.py`
   - `.codex-plugin/plugin.json`
   - version assertions in `tests/`
   - the `cli_version` example in `docs/schema.md`
3. Keep `uv.lock` untracked and ignored. The MCP configuration and GitHub workflows must not use
   frozen lockfile resolution.
4. Run the deterministic preflight:

   ```bash
   python3 .agents/skills/release-knowledge-refinery/scripts/preflight.py --version <version>
   ```

5. Run the repository-required validation:

   ```bash
   bash scripts/validate.sh
   ```

## Publish the release PR

1. Review the complete diff and stage only the intended files explicitly.
2. Commit with `Release v<version>`, push the branch, and create a draft PR.
3. Write the PR description in Japanese with changes, motivation, user impact, and validation.
4. Wait for every Python version in `.github/workflows/ci.yml` to pass. Inspect failures with GitHub Actions logs.
5. Fix failures caused by the release diff. If a failure exposes unrelated pre-existing work,
   report the root cause in Japanese and obtain approval before expanding the PR.
6. For a publish request, mark the green PR ready and squash-merge it. For a prepare request, stop.

## Tag and publish

1. Fetch `origin`, fast-forward local `main`, and capture the exact merged commit SHA.
2. Create annotated tag `v<version>` on that merge commit and push only that tag.
3. Never delete, recreate, or move a tag after it has been pushed or published.
4. Create the GitHub Release with `gh release create --verify-tag`. Write Japanese notes covering
   changes, verification, and Plugin/CLI update instructions.

## Verify the outcome

1. Verify that the tag resolves to the intended merged commit and the Release is published,
   non-draft, and non-prerelease unless explicitly requested otherwise.
2. Confirm main CI, documentation deployment, and Pages deployment all succeed.
3. If release-infrastructure fails after publication, fix it through a separate PR. Do not move the
   published tag. Cut another version only when distributed code or artifacts must change.
4. Report the Release URL, merged PRs, tag commit, checks, and untouched unrelated worktree files.
