from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from knowledge_refinery import get_version  # noqa: E402


EXPECTED_SKILLS = {
    "refinery-project",
    "refinery-experience",
    "refinery-memory",
    "refinery-maintenance",
}


def _read_json(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return raw


def _skill_header(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"Skill is missing YAML front matter: {path}")
    block = text.split("\n---\n", 1)[0][4:]
    raw = yaml.safe_load(block)
    if not isinstance(raw, dict):
        raise ValueError(f"Skill front matter must be a mapping: {path}")
    return raw


def validate() -> None:
    plugin = _read_json(ROOT / ".codex-plugin" / "plugin.json")
    if plugin.get("name") != "knowledge-refinery":
        raise ValueError("Plugin name must be knowledge-refinery")
    if plugin.get("version") != get_version():
        raise ValueError(
            f"Plugin/Python version drift: plugin={plugin.get('version')}, python={get_version()}"
        )
    if plugin.get("skills") != "./skills/" or plugin.get("mcpServers") != "./.mcp.json":
        raise ValueError("Plugin skill or MCP path does not match the repository layout")

    mcp = _read_json(ROOT / ".mcp.json")
    servers = mcp.get("mcpServers")
    if not isinstance(servers, dict) or "knowledge-refinery" not in servers:
        raise ValueError(".mcp.json must define the knowledge-refinery server")

    skill_names = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
    if skill_names != EXPECTED_SKILLS:
        raise ValueError(
            f"Unexpected distributed skills: expected={sorted(EXPECTED_SKILLS)}, "
            f"actual={sorted(skill_names)}"
        )
    for name in sorted(EXPECTED_SKILLS):
        header = _skill_header(ROOT / "skills" / name / "SKILL.md")
        if header.get("name") != name:
            raise ValueError(f"Skill name does not match its directory: {name}")
        if not isinstance(header.get("description"), str) or not header["description"]:
            raise ValueError(f"Skill description is missing: {name}")

    marketplace = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not any(
        isinstance(item, dict) and item.get("name") == "knowledge-refinery" for item in plugins
    ):
        raise ValueError("Personal marketplace is missing knowledge-refinery")


if __name__ == "__main__":
    validate()
    print("Distribution validation passed")
