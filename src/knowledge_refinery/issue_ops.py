"""Manage vault-wide issues independently of project knowledge."""

from collections import Counter
from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
import re
from typing import TypedDict
from typing import cast
from uuid import uuid4

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import validate_vault_root


ISSUE_STATUSES = ("backlog", "ready", "in_progress", "blocked", "done", "cancelled")
ISSUE_ID_RE = re.compile(r"issue-[0-9a-f]{32}")


class IssueEvent(TypedDict):
    """Record the changed fields and reason for one issue revision."""

    revision: int
    at: str
    reason: str
    changes: dict[str, object]


class Issue(TypedDict):
    """Represent a globally identified task and its complete change history."""

    id: str
    title: str
    description: str
    done_when: str
    status: str
    projects: list[str]
    tags: list[str]
    created_at: str
    updated_at: str
    revision: int
    history: list[IssueEvent]


def _store_path(vault: Path) -> Path:
    path = validate_vault_root(vault) / "issues.json"
    if path.is_symlink():
        raise ValueError(f"Issue storage must not be a symlink: {path}")
    return path


def _names(values: list[str], field: str) -> list[str]:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must contain non-empty strings")
    return sorted({value.strip() for value in values})


def _validate_issue(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ValueError("Issue must be an object")
    for field in ("id", "title", "status", "created_at", "updated_at"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise ValueError(f"Issue {field} must be a non-empty string")
    if not ISSUE_ID_RE.fullmatch(raw["id"]) or raw["status"] not in ISSUE_STATUSES:
        raise ValueError("Invalid issue ID or status")
    for field in ("description", "done_when"):
        if not isinstance(raw.get(field), str):
            raise ValueError(f"Issue {field} must be a string")
    for field in ("projects", "tags"):
        values = raw.get(field)
        if not isinstance(values, list) or values != _names(values, field):
            raise ValueError(f"Issue {field} must be a sorted, unique list")
    if raw["status"] == "done" and not raw["done_when"].strip():
        raise ValueError("Done issues must have completion criteria")
    _validate_history(cast(Issue, raw))


def _validate_history(issue: Issue) -> None:
    created = datetime.fromisoformat(issue["created_at"])
    updated = datetime.fromisoformat(issue["updated_at"])
    if created.tzinfo is None or updated.tzinfo is None or updated < created:
        raise ValueError("Invalid issue timestamps")
    revision = issue.get("revision")
    history = issue.get("history")
    if type(revision) is not int or revision < 1:
        raise ValueError("Issue revision must be a positive integer")
    if not isinstance(history, list) or len(history) != revision:
        raise ValueError("Issue history must contain every revision")
    for index, event in enumerate(history, 1):
        if (
            not isinstance(event, dict)
            or type(event.get("revision")) is not int
            or event["revision"] != index
            or not isinstance(event.get("at"), str)
            or not isinstance(event.get("reason"), str)
            or not isinstance(event.get("changes"), dict)
        ):
            raise ValueError("Invalid issue history event")
    if history[0]["at"] != issue["created_at"] or history[-1]["at"] != issue["updated_at"]:
        raise ValueError("Issue timestamps must match history")


def _read_store(path: Path) -> list[Issue]:
    if path.is_symlink():
        raise ValueError(f"Issue storage must not be a symlink: {path}")
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(raw, dict)
        or type(raw.get("schema_version")) is not int
        or raw["schema_version"] != 1
        or not isinstance(raw.get("issues"), list)
    ):
        raise ValueError(f"Unsupported issue store schema: {path}")
    seen = set()
    for issue in raw["issues"]:
        _validate_issue(issue)
        if issue["id"] in seen:
            raise ValueError(f"Duplicate issue ID: {issue['id']}")
        seen.add(issue["id"])
    return cast(list[Issue], raw["issues"])


def _write_store(path: Path, issues: list[Issue]) -> None:
    # One atomic snapshot also makes a multi-issue tag rename all-or-nothing.
    atomic_write_text(
        path,
        json.dumps({"schema_version": 1, "issues": issues}, ensure_ascii=False, indent=2) + "\n",
    )


def _find_issue(issues: list[Issue], issue_id: str) -> Issue:
    for issue in issues:
        if issue["id"] == issue_id:
            return issue
    raise ValueError(f"Issue does not exist: {issue_id}")


def create_issue(
    vault: Path,
    *,
    title: str,
    description: str = "",
    done_when: str = "",
    projects: list[str] | None = None,
    tags: list[str] | None = None,
) -> Issue:
    """Create a backlog issue, optionally linked to registered project IDs."""
    path = _store_path(vault)
    project_ids = _names(projects or [], "projects")
    for project_id in project_ids:
        read_project_metadata(vault, project_id)
    now = datetime.now(UTC).isoformat()
    issue: Issue = {
        "id": f"issue-{uuid4().hex}",
        "title": title.strip(),
        "description": description,
        "done_when": done_when,
        "status": "backlog",
        "projects": project_ids,
        "tags": _names(tags or [], "tags"),
        "created_at": now,
        "updated_at": now,
        "revision": 1,
        "history": [],
    }
    issue["history"].append(
        {
            "revision": 1,
            "at": now,
            "reason": "Created",
            "changes": {key: value for key, value in issue.items() if key != "history"},
        }
    )
    _validate_issue(issue)
    with interprocess_lock(path):
        issues = _read_store(path)
        issues.append(issue)
        _write_store(path, issues)
    return issue


def get_issue(vault: Path, issue_id: str) -> Issue:
    """Read an issue with history without requiring a local project checkout."""
    return _find_issue(_read_store(_store_path(vault)), issue_id)


def list_issues(
    vault: Path,
    *,
    project: str | None = None,
    status: str | None = None,
    tag: str | None = None,
) -> list[Issue]:
    """List all issues, newest update first, combining filters with AND."""
    if status is not None and status not in ISSUE_STATUSES:
        raise ValueError(f"Invalid issue status: {status}")
    issues = _read_store(_store_path(vault))
    return sorted(
        (
            issue
            for issue in issues
            if (project is None or project in issue["projects"])
            and (status is None or status == issue["status"])
            and (tag is None or tag in issue["tags"])
        ),
        key=lambda issue: (issue["updated_at"], issue["id"]),
        reverse=True,
    )


def _record_change(issue: Issue, before: dict[str, object], reason: str) -> bool:
    changes = {key: value for key, value in issue.items() if value != before[key]}
    if not changes:
        return False
    now = max(datetime.now(UTC).isoformat(), issue["updated_at"])
    issue["revision"] += 1
    issue["updated_at"] = now
    issue["history"].append(
        {"revision": issue["revision"], "at": now, "reason": reason, "changes": changes}
    )
    _validate_issue(issue)
    return True


def update_issue(
    vault: Path,
    issue_id: str,
    *,
    expected_revision: int,
    title: str | None = None,
    description: str | None = None,
    done_when: str | None = None,
    status: str | None = None,
    add_projects: list[str] | None = None,
    remove_projects: list[str] | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    reason: str = "",
) -> Issue:
    """Update only supplied fields; reject stale revisions and unexplained status changes."""
    path = _store_path(vault)
    additions = _names(add_projects or [], "projects")
    removals = _names(remove_projects or [], "projects")
    tag_additions = _names(add_tags or [], "tags")
    tag_removals = _names(remove_tags or [], "tags")
    if set(additions) & set(removals) or set(tag_additions) & set(tag_removals):
        raise ValueError("Cannot add and remove the same project or tag")
    for project_id in additions:
        read_project_metadata(vault, project_id)
    with interprocess_lock(path):
        issues = _read_store(path)
        issue = _find_issue(issues, issue_id)
        if type(expected_revision) is not int or issue["revision"] != expected_revision:
            raise RefineryCliError(
                code="issue_revision_conflict",
                summary=(
                    f"Issue changed: expected {expected_revision}, current {issue['revision']}"
                ),
                suggested_action="Read the issue again and retry with its current revision.",
            )
        before = dict(issue)
        if title is not None:
            issue["title"] = title.strip()
        if description is not None:
            issue["description"] = description
        if done_when is not None:
            issue["done_when"] = done_when
        if status is not None and status != issue["status"]:
            if not reason.strip():
                raise ValueError("Status changes require a non-empty reason")
            issue["status"] = status
        issue["projects"] = sorted((set(issue["projects"]) | set(additions)) - set(removals))
        issue["tags"] = sorted((set(issue["tags"]) | set(tag_additions)) - set(tag_removals))
        if _record_change(issue, before, reason):
            _write_store(path, issues)
        return issue


def list_issue_tags(vault: Path, *, project: str | None = None) -> list[dict[str, object]]:
    """List currently used issue tags with usage counts, optionally within a project."""
    counts = Counter(tag for issue in list_issues(vault, project=project) for tag in issue["tags"])
    return [{"tag": tag, "count": count} for tag, count in sorted(counts.items())]


def maintain_issue_tag(vault: Path, tag: str, *, replacement: str | None = None) -> list[str]:
    """Rename/merge a tag, or remove it globally, atomically preserving issue history."""
    tag = _names([tag], "tag")[0]
    if replacement is not None:
        replacement = _names([replacement], "replacement")[0]
        if tag == replacement:
            raise ValueError("Replacement must differ from the source tag")
    path = _store_path(vault)
    with interprocess_lock(path):
        issues = _read_store(path)
        affected = [issue for issue in issues if tag in issue["tags"]]
        if not affected:
            raise ValueError(f"Issue tag does not exist: {tag}")
        for issue in affected:
            before = dict(issue)
            issue["tags"] = sorted(
                (set(issue["tags"]) - {tag}) | ({replacement} if replacement else set())
            )
            reason = f"Rename tag {tag} to {replacement}" if replacement else f"Remove tag {tag}"
            _record_change(issue, before, reason)
        _write_store(path, issues)
        return [issue["id"] for issue in affected]
