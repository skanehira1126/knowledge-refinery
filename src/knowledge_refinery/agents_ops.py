from importlib.resources import files
from pathlib import Path
import re

from knowledge_refinery.storage_ops import atomic_write_text


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


def _split_suffix_after_truncated_block(current: str, start_match: re.Match[str]) -> str:
    tail = current[start_match.end() :]
    boundary = tail.find("\n\n")
    if boundary == -1:
        return ""
    return tail[boundary:].lstrip("\n")


def replace_managed_block(current: str, block: str) -> str:
    managed_match = MANAGED_BLOCK_RE.search(current)
    if managed_match is not None:
        return MANAGED_BLOCK_RE.sub(block, current, count=1)

    start_match = START_MARKER_RE.search(current)
    if start_match is None:
        if current and not current.endswith("\n"):
            current = f"{current}\n"
        separator = "\n" if current.strip() else ""
        return f"{current}{separator}{block}"

    prefix = current[: start_match.start()]
    if prefix and not prefix.endswith("\n"):
        prefix = f"{prefix}\n"
    separator = "\n" if prefix.strip() else ""
    suffix = _split_suffix_after_truncated_block(current, start_match)
    if suffix:
        return f"{prefix}{separator}{block}\n{suffix}"
    return f"{prefix}{separator}{block}"


def apply_agents_md(target: Path, lang: str, filename: str = "AGENTS.md") -> Path:
    agents_path = resolve_agents_path(target, filename=filename)
    block = render_managed_block(lang)

    if agents_path.exists():
        current = agents_path.read_text(encoding="utf-8")
        updated = replace_managed_block(current, block)
    else:
        updated = block

    agents_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(agents_path, updated)
    return agents_path


def has_managed_block(target: Path, filename: str = "AGENTS.md") -> bool:
    agents_path = resolve_agents_path(target, filename=filename)
    if not agents_path.is_file():
        return False
    return MANAGED_BLOCK_RE.search(agents_path.read_text(encoding="utf-8")) is not None


def remove_agents_md(target: Path, filename: str = "AGENTS.md") -> Path | None:
    """Remove only the Knowledge Refinery managed block.

    A guide created solely for the managed block is removed. User-authored content is
    preserved byte-for-byte except for the separator directly surrounding the block.
    """
    agents_path = resolve_agents_path(target, filename=filename)
    if not agents_path.is_file():
        return None

    current = agents_path.read_text(encoding="utf-8")
    if MANAGED_BLOCK_RE.search(current) is None:
        return None
    updated = MANAGED_BLOCK_RE.sub("", current, count=1)
    if not updated.strip():
        agents_path.unlink()
    else:
        atomic_write_text(agents_path, updated)
    return agents_path
