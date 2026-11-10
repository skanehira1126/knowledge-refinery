"""List local root chats by log modification time without reading transcript bodies."""

from datetime import UTC
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

from knowledge_refinery.session_ops import _child_identity
from knowledge_refinery.session_ops import _metadata
from knowledge_refinery.session_ops import string


def parse_updated_bound(value: str | None) -> datetime | None:
    """Accept a UTC calendar date or an ISO timestamp with an explicit timezone."""
    if value is None:
        return None
    try:
        if len(value) == 10:
            day = date.fromisoformat(value)
            return datetime(day.year, day.month, day.day, tzinfo=UTC)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC)
    except ValueError:
        pass
    raise ValueError("Use YYYY-MM-DD (UTC) or an ISO timestamp with Z or a timezone offset")


def list_sessions(
    roots: list[Path],
    *,
    updated_since: str | None = None,
    updated_before: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Return root chats once each, newest first, in a half-open modification-time range."""
    since = parse_updated_bound(updated_since)
    before = parse_updated_bound(updated_before)
    if since is not None and before is not None and since >= before:
        raise ValueError("updated-since must be earlier than updated-before")
    if limit <= 0 or offset < 0:
        raise ValueError("limit must be positive and offset nonnegative")
    entries, scanned, skipped = _scan_root_chats(roots)
    selected = [
        entry
        for entry in entries
        if (since is None or datetime.fromisoformat(entry["updated_at"]) >= since)
        and (before is None or datetime.fromisoformat(entry["updated_at"]) < before)
    ]
    selected.sort(key=lambda entry: entry["chat_id"])
    selected.sort(key=lambda entry: entry["updated_at"], reverse=True)
    return {
        "updated_at_source": "file_mtime",
        "updated_since": since.isoformat() if since else None,
        "updated_before": before.isoformat() if before else None,
        "total": len(selected),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(selected) else None,
        "scanned_files": scanned,
        "skipped_files": skipped,
        "chats": selected[offset : offset + limit],
    }


def _scan_root_chats(roots: list[Path]) -> tuple[list[dict[str, Any]], int, int]:
    directories = list(dict.fromkeys(root.expanduser().resolve() for root in roots))
    for root in directories:
        if not root.is_dir():
            raise ValueError(f"Session directory does not exist: {root}")
    paths = sorted({p.resolve() for root in directories for p in root.rglob("*.jsonl")})
    chats: dict[str, dict[str, Any]] = {}
    skipped = 0
    for path in paths:
        try:
            updated = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        except OSError:
            skipped += 1
            continue
        meta = _metadata(path)
        if not isinstance(meta, dict) or not (chat_id := string(meta.get("id"))):
            skipped += 1
            continue
        if _child_identity(meta) is not None or meta.get("thread_source") == "subagent":
            continue
        entry = {
            "chat_id": chat_id,
            "updated_at": updated.isoformat(),
            "path": str(path),
            "cwd": string(meta.get("cwd")),
        }
        if chat_id not in chats:
            chats[chat_id] = {**entry, "paths": [str(path)]}
        else:
            existing = chats[chat_id]
            existing["paths"].append(str(path))
            if entry["updated_at"] > existing["updated_at"]:
                existing.update(entry)
    return list(chats.values()), len(paths), skipped
