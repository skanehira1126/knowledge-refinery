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


def _validate_plugin() -> None:
    plugin = _read_json(ROOT / ".codex-plugin" / "plugin.json")
    if plugin.get("name") != "knowledge-refinery":
        raise ValueError("Plugin name must be knowledge-refinery")
    if plugin.get("version") != get_version():
        raise ValueError(
            f"Plugin/Python version drift: plugin={plugin.get('version')}, python={get_version()}"
        )
    if plugin.get("skills") != "./skills/" or plugin.get("mcpServers") != "./.mcp.json":
        raise ValueError("Plugin skill or MCP path does not match the repository layout")


def _validate_mcp() -> None:
    mcp = _read_json(ROOT / ".mcp.json")
    servers = mcp.get("mcpServers")
    if not isinstance(servers, dict) or "knowledge-refinery" not in servers:
        raise ValueError(".mcp.json must define the knowledge-refinery server")
    server = servers["knowledge-refinery"]
    if not isinstance(server, dict):
        raise ValueError("knowledge-refinery MCP server config must be an object")
    expected_server = {
        "cwd": ".",
        "command": "uv",
        "args": ["run", "--frozen", "--project", ".", "knowledge-refinery", "mcp", "serve"],
    }
    for key, expected in expected_server.items():
        if server.get(key) != expected:
            raise ValueError(
                f"MCP server {key} drift: expected={expected}, actual={server.get(key)}"
            )


def _validate_skills() -> None:
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
        agent_path = ROOT / "skills" / name / "agents" / "openai.yaml"
        if not agent_path.is_file():
            raise ValueError(f"Skill agent interface is missing: {name}")
        agent = yaml.safe_load(agent_path.read_text(encoding="utf-8"))
        interface = agent.get("interface") if isinstance(agent, dict) else None
        if not isinstance(interface, dict):
            raise ValueError(f"Skill agent interface must be a mapping: {name}")
        default_prompt = interface.get("default_prompt")
        if not isinstance(default_prompt, str) or f"${name}" not in default_prompt:
            raise ValueError(f"Skill default prompt must invoke ${name}")


def _validate_marketplace() -> None:
    marketplace = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not any(
        isinstance(item, dict) and item.get("name") == "knowledge-refinery" for item in plugins
    ):
        raise ValueError("Personal marketplace is missing knowledge-refinery")


def validate() -> None:
    _validate_plugin()
    _validate_mcp()
    _validate_skills()
    _validate_marketplace()


if __name__ == "__main__":
    validate()
    print("Distribution validation passed")
