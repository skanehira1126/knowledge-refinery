from collections.abc import Mapping
from pathlib import Path

import yaml


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    write_text(path, content)


def write_yaml_data(path: Path, data: Mapping[str, object]) -> None:
    rendered = yaml.safe_dump(dict(data), allow_unicode=True, sort_keys=False)
    write_text(path, rendered)


def render_markdown_document(header: Mapping[str, object], body: str) -> str:
    front_matter = yaml.safe_dump(dict(header), allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front_matter}\n---\n\n{body.rstrip()}\n"


def write_markdown_document(path: Path, header: Mapping[str, object], body: str) -> None:
    write_markdown(path, render_markdown_document(header, body))


def make_session_meta(session_id: str = "session-123", **overrides: object) -> dict[str, object]:
    meta: dict[str, object] = {
        "session_id": session_id,
        "kind": "task",
        "title": "Initial title",
        "task": "Initial task",
        "created_at": "2026-04-17T00:00:00Z",
        "created_by": "user",
        "repository": "repo-a",
        "domain": "backend",
        "status": "active",
        "phase": "capture",
        "current_step": "collecting notes",
        "next_action": "summarize findings",
        "last_updated_at": "2026-04-17T00:00:00Z",
        "closed_at": None,
        "blocked_reason": None,
        "resume_condition": None,
        "parent_session_id": None,
        "child_session_ids": [],
        "related_sessions": [],
        "depends_on": [],
        "supersedes": [],
        "superseded_by": None,
        "evidence_status": "collecting",
        "flow_status": "not_started",
        "synthesis_status": "not_started",
        "coverage_status": "unknown",
        "confidence": "low",
        "raw_item_count": 0,
        "flow_item_count": 0,
        "last_flow_update_at": None,
    }
    meta.update(overrides)
    return meta
