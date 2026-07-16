#!/usr/bin/env bash
set -euo pipefail

codex_home="${CODEX_HOME:-${HOME}/.codex}"
plugin_creator="${codex_home}/skills/.system/plugin-creator"
skill_creator="${codex_home}/skills/.system/skill-creator"

if [[ ! -f "${plugin_creator}/scripts/validate_plugin.py" ]]; then
  echo "Plugin validator not found under CODEX_HOME: ${plugin_creator}" >&2
  exit 1
fi

if [[ ! -f "${skill_creator}/scripts/quick_validate.py" ]]; then
  echo "Skill validator not found under CODEX_HOME: ${skill_creator}" >&2
  exit 1
fi

uv run tox
uv run --extra docs mkdocs build --strict
uv run python "${plugin_creator}/scripts/validate_plugin.py" .

for skill in refinery-project refinery-experience refinery-memory refinery-maintenance; do
  uv run python "${skill_creator}/scripts/quick_validate.py" "skills/${skill}"
done
