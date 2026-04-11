from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re


LANG_CHOICES = ("jp", "en")
GUIDE_FILENAME_CHOICES = ("AGENTS.md", "CLAUDE.md")
START_MARKER_PREFIX = "<!-- knowledge-refinery:agents:start"
START_MARKER_RE = re.compile(r"<!-- knowledge-refinery:agents:start lang=(jp|en) -->")
END_MARKER = "<!-- knowledge-refinery:agents:end -->"
MANAGED_BLOCK_RE = re.compile(
    r"<!-- knowledge-refinery:agents:start lang=(jp|en) -->\n.*?\n"
    r"<!-- knowledge-refinery:agents:end -->\n?",
    flags=re.DOTALL,
)


def resolve_agents_path(target: Path, filename: str = "AGENTS.md") -> Path:
    if filename not in GUIDE_FILENAME_CHOICES:
        raise ValueError(f"Unsupported guide filename: {filename}")

    resolved = target.resolve()
    if resolved.name in GUIDE_FILENAME_CHOICES:
        return resolved
    return resolved / filename


def load_agents_snippet(lang: str) -> str:
    if lang not in LANG_CHOICES:
        raise ValueError(f"Unsupported language: {lang}")
    return (
        files("knowledge_refinery.data")
        .joinpath(f"agents.{lang}.md")
        .read_text(encoding="utf-8")
        .rstrip()
    )


def render_managed_block(lang: str) -> str:
    snippet = load_agents_snippet(lang)
    return f"{START_MARKER_PREFIX} lang={lang} -->\n{snippet}\n{END_MARKER}\n"


def apply_agents_md(target: Path, lang: str, filename: str = "AGENTS.md") -> Path:
    agents_path = resolve_agents_path(target, filename=filename)
    block = render_managed_block(lang)

    if agents_path.exists():
        current = agents_path.read_text(encoding="utf-8")
        if START_MARKER_RE.search(current):
            updated = MANAGED_BLOCK_RE.sub(block, current, count=1)
        else:
            if current and not current.endswith("\n"):
                current = f"{current}\n"
            separator = "\n" if current.strip() else ""
            updated = f"{current}{separator}{block}"
    else:
        updated = block

    agents_path.parent.mkdir(parents=True, exist_ok=True)
    agents_path.write_text(updated, encoding="utf-8")
    return agents_path
