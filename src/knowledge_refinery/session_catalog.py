"""List local root chats by repository, title, modification time, and observed activity."""

from datetime import UTC
from datetime import date
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from knowledge_refinery.session_ops import _child_identity
from knowledge_refinery.session_ops import _metadata
from knowledge_refinery.session_ops import string
from knowledge_refinery.session_sources import open_rollout
from knowledge_refinery.session_sources import rollout_paths
from knowledge_refinery.vault_ops import resolve_project_id


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
    project: Path = Path("."),
    title: str | None = None,
    title_index: Path | None = None,
    updated_since: str | None = None,
    updated_before: str | None = None,
    active_since: str | None = None,
    active_before: str | None = None,
    removed_worktrees_root: Path | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Return matching root chats once each, newest first, with local titles when available."""
    since = parse_updated_bound(updated_since)
    before = parse_updated_bound(updated_before)
    if since is not None and before is not None and since >= before:
        raise ValueError("updated-since must be earlier than updated-before")
    start, end = parse_updated_bound(active_since), parse_updated_bound(active_before)
    if start is not None and end is not None and start >= end:
        raise ValueError("active-since must be earlier than active-before")
    if limit <= 0 or offset < 0:
        raise ValueError("limit must be positive and offset nonnegative")
    if title is not None and not title.strip():
        raise ValueError("Title filter must not be empty")
    title_query = title.casefold() if title is not None else None
    identity = _repository_identity(project)
    if identity is None:
        raise ValueError(f"Project is not an accessible Git working tree: {project}")
    project_root, common_dir = identity
    project_id = resolve_project_id(project_root)
    entries, scanned, skipped = _scan_root_chats(roots)
    entries = _project_chats(entries, common_dir, removed_worktrees_root)
    titles = _read_titles(title_index) if title_index is not None else {}
    for entry in entries:
        entry["title"] = titles.get(entry["chat_id"])
    selected = [
        entry
        for entry in entries
        if (since is None or datetime.fromisoformat(entry["updated_at"]) >= since)
        and (before is None or datetime.fromisoformat(entry["updated_at"]) < before)
        and (title_query is None or title_query in (entry["title"] or "").casefold())
    ]
    if start or end:
        selected = [entry for entry in selected if _has_activity(entry, start, end)]
    selected.sort(key=lambda entry: entry["chat_id"])
    selected.sort(key=lambda entry: entry["updated_at"], reverse=True)
    return {
        "project_id": project_id,
        "project_root": str(project_root),
        "git_common_dir": str(common_dir),
        "updated_at_source": "file_mtime",
        "updated_since": since.isoformat() if since else None,
        "updated_before": before.isoformat() if before else None,
        "active_since": start.isoformat() if start else None,
        "active_before": end.isoformat() if end else None,
        "total": len(selected),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(selected) else None,
        "scanned_files": scanned,
        "skipped_files": skipped,
        "chats": selected[offset : offset + limit],
    }


def _has_activity(entry: dict[str, Any], start: datetime | None, end: datetime | None) -> bool:
    lower = start.timestamp() if start else float("-inf")
    upper = end.timestamp() if end else float("inf")
    for path in entry["paths"]:
        with open_rollout(Path(path)) as source:
            for raw in source:
                if b'"item_completed"' not in raw:
                    continue
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                timestamp = _activity_timestamp(event, entry["chat_id"])
                if timestamp is not None and lower <= timestamp < upper:
                    return True
    return False


def _activity_timestamp(event: Any, chat_id: str) -> float | None:
    if not isinstance(event, dict) or event.get("type") != "event_msg":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "item_completed":
        return None
    if payload.get("thread_id") != chat_id or not isinstance(payload.get("item"), dict):
        return None
    if not string(payload["item"].get("id")):
        return None
    completed = payload.get("completed_at_ms")
    if isinstance(completed, int | float) and not isinstance(completed, bool) and completed > 0:
        return completed / 1000
    try:
        stamp = datetime.fromisoformat(event["timestamp"])
    except (KeyError, TypeError, ValueError):
        return None
    return stamp.timestamp() if stamp.tzinfo else None


def _read_titles(path: Path) -> dict[str, str | None]:
    titles: dict[str, str | None] = {}
    try:
        with path.expanduser().open("rb") as index:
            for line in index:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if (
                    isinstance(row, dict)
                    and (chat_id := string(row.get("id")))
                    and isinstance(name := row.get("thread_name"), str)
                ):
                    # Codex appends name updates and resolves the last entry for each chat ID.
                    titles[chat_id] = string(name)
    except OSError:
        return {}
    return titles


def _scan_root_chats(roots: list[Path]) -> tuple[list[dict[str, Any]], int, int]:
    directories = list(dict.fromkeys(root.expanduser().resolve() for root in roots))
    for root in directories:
        if not root.is_dir():
            raise ValueError(f"Session directory does not exist: {root}")
    paths = rollout_paths(directories)
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
            "session_id": string(meta.get("session_id")),
            "updated_at": updated.isoformat(),
            "path": str(path),
            "cwd": string(meta.get("cwd")),
            "_git": meta.get("git"),
        }
        if chat_id not in chats:
            chats[chat_id] = {**entry, "paths": [str(path)]}
        else:
            existing = chats[chat_id]
            existing["paths"].append(str(path))
            if entry["updated_at"] > existing["updated_at"]:
                existing.update(entry)
    return list(chats.values()), len(paths), skipped


def _repository_identity(path: Path) -> tuple[Path, Path] | None:
    path = path.expanduser().resolve()
    if not path.is_dir():
        return None
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}
    }
    result = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode:
        return None
    root, common_dir = result.stdout.splitlines()
    return Path(root).resolve(), Path(common_dir).resolve()


def _removed_worktree_commit(cwd: Path, worktrees: Path, git: Any, origin: str) -> str | None:
    if not origin or not isinstance(git, dict) or git.get("repository_url") != origin:
        return None
    path = cwd.resolve()
    if not path.is_relative_to(worktrees):
        return None
    parts = path.relative_to(worktrees).parts
    if len(parts) < 2 or worktrees.joinpath(*parts[:2]).exists():
        return None
    commit = git.get("commit_hash")
    if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        return commit
    return None


def _project_chats(
    entries: list[dict[str, Any]], common_dir: Path, removed_worktrees_root: Path | None
) -> list[dict[str, Any]]:
    identities: dict[str, tuple[Path, Path] | None] = {}
    git = ["git", "--git-dir", str(common_dir)]
    origin = ""
    if removed_worktrees_root:
        removed_worktrees_root = removed_worktrees_root.expanduser().resolve()
        origin = subprocess.run(
            [*git, "config", "--get", "remote.origin.url"], capture_output=True, text=True
        ).stdout.strip()
    commits: dict[str, bool] = {}
    selected = []
    for entry in entries:
        metadata = entry.pop("_git")
        cwd = entry["cwd"]
        if not cwd or not Path(cwd).is_absolute():
            continue
        if cwd not in identities:
            identities[cwd] = _repository_identity(Path(cwd))
        identity = identities[cwd]
        if identity is not None and identity[1] == common_dir:
            selected.append(entry)
        elif (
            identity is None
            and removed_worktrees_root
            and (
                commit := _removed_worktree_commit(
                    Path(cwd), removed_worktrees_root, metadata, origin
                )
            )
        ):
            if commit not in commits:
                result = subprocess.run(
                    [*git, "cat-file", "-t", commit],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
                )
                commits[commit] = result.returncode == 0 and result.stdout.strip() == "commit"
            if commits[commit]:
                selected.append({**entry, "project_match": "recorded_origin_and_commit"})
    return selected
