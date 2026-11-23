"""Store and select the Markdown delivered by project context hooks."""

import hashlib
from pathlib import Path

from typing_extensions import TypedDict

from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock


_TOOLS = ("Bash", "apply_patch", "Edit", "Write")
_SAVED_SESSION_TARGETS = {
    f"SessionStart/{source}" for source in ("startup", "resume", "clear", "compact", "fork")
}


class ContextSummary(TypedDict):
    """Identify a hook target and its current Markdown revision."""

    target: str
    revision: str | None


class ContextEntry(ContextSummary):
    """Include the exact Markdown body, or None for an unset target."""

    body: str | None


def context_targets() -> list[str]:
    """List every configurable target in hook order."""
    tool_targets = [
        f"{event}/{tool}" for event in ("PreToolUse", "PostToolUse") for tool in _TOOLS
    ]
    return ["UserPromptSubmit", *tool_targets, "SubagentStart"]


def _context_path(project_store: Path, target: str) -> Path:
    """Resolve one supported Markdown file inside the registered vault project."""
    if target not in context_targets() and target not in _SAVED_SESSION_TARGETS:
        raise ValueError(f"Unknown context target: {target}")
    path = project_store / "context" / f"{target}.md"
    if path.resolve() != path:
        raise ValueError(f"Project context path must not traverse symlinks: {path}")
    return path


def _read_body(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return None


def _entry(target: str, body: str | None) -> ContextEntry:
    revision = None if body is None else hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {"target": target, "revision": revision, "body": body}


def read_context(project_store: Path, target: str) -> ContextEntry:
    """Return the body and revision from the same read."""
    return _entry(target, _read_body(_context_path(project_store, target)))


def list_contexts(project_store: Path) -> list[ContextSummary]:
    """Return all supported targets, including unset ones, without their bodies."""
    entries: list[ContextSummary] = []
    for target in context_targets():
        entry = read_context(project_store, target)
        entries.append({"target": target, "revision": entry["revision"]})
    return entries


def update_context(
    project_store: Path, target: str, body: str | None, *, expected_revision: str | None
) -> ContextEntry:
    """Create, replace, or clear one target and return the committed revision."""
    if target in _SAVED_SESSION_TARGETS and body is not None:
        raise ValueError(
            "SessionStart uses fixed plugin guidance. Saved text can be read or cleared."
        )
    path = _context_path(project_store, target)
    if body is None and expected_revision is None:
        raise ValueError("Clearing a context target requires its current expected_revision")
    if body is not None and not body.strip():
        raise ValueError("Context body is blank. Pass body=null and its revision to clear it.")
    with interprocess_lock(path):
        current = _entry(target, _read_body(path))
        if current["revision"] != expected_revision:
            raise ValueError(
                f"Context revision conflict for {target}. Read the current body before retrying."
            )
        if current["body"] == body:
            return current
        if body is None:
            path.unlink()
        else:
            atomic_write_text(path, body)
        return _entry(target, body)
