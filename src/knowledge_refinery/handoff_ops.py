"""Persist task handoffs separately from reusable knowledge."""

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import secrets

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import SLUG_RE
from knowledge_refinery.front_matter import render_front_matter
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import list_project_ids
from knowledge_refinery.vault_ops import read_project_metadata


HANDOFF_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Handoff:
    """Hold a validated snapshot and its lifecycle metadata."""

    path: Path
    header: dict[str, object]
    body: str

    def as_dict(self, vault: Path, *, include_body: bool = True) -> dict[str, object]:
        """Serialize a handoff for CLI and MCP consumers."""
        payload: dict[str, object] = {
            "header": self.header,
            "path": str(self.path.relative_to(vault.resolve())),
        }
        if include_body:
            payload["body"] = self.body
        return payload


def _handoff_root(vault: Path, project_id: str) -> Path:
    context = context_from_vault(vault, project_id)
    root = context.project_store / "handoffs"
    # A handoff operation must never follow a redirected project or storage area.
    for path in (context.vault_root / "projects", context.project_store, root):
        if path.is_symlink():
            raise ValueError(f"Handoff storage must not use symlinks: {path}")
    if root.exists() and not root.is_dir():
        raise ValueError(f"Handoff storage must be a directory: {root}")
    read_project_metadata(vault, project_id)
    return root


def _handoff_path(root: Path, handoff_id: str) -> Path:
    if not SLUG_RE.fullmatch(handoff_id):
        raise ValueError("handoff_id must be a lowercase slug")
    path = root / f"{handoff_id}.md"
    if path.is_symlink():
        raise ValueError(f"Handoff must not be a symlink: {path}")
    return path


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO datetime with a timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def validate_handoff(header: dict[str, object], body: str, path: Path, project_id: str) -> None:
    """Validate the snapshot schema, lifecycle, and storage identity."""
    if (
        type(header.get("schema_version")) is not int
        or header["schema_version"] != HANDOFF_SCHEMA_VERSION
    ):
        raise ValueError("Unsupported handoff schema_version")
    for field in ("handoff_id", "task_id", "title", "goal", "done_when"):
        value = header.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"handoff {field} must be a non-empty string")
    for field in ("handoff_id", "task_id"):
        if not SLUG_RE.fullmatch(str(header[field])):
            raise ValueError(f"handoff {field} must be a lowercase slug")
    if header.get("project_id") != project_id or path.name != f"{header['handoff_id']}.md":
        raise ValueError("Handoff project_id and filename must match storage identity")
    if not body.strip():
        raise ValueError("handoff body must contain the task state and references")
    _validate_lifecycle(header)


def _validate_lifecycle(header: dict[str, object]) -> None:
    created = _timestamp(header.get("created_at"), "created_at")
    updated = _timestamp(header.get("updated_at"), "updated_at")
    if updated < created:
        raise ValueError("handoff updated_at must not precede created_at")
    if header.get("status") not in ("active", "archived"):
        raise ValueError("handoff status must be active or archived")
    if header["status"] == "archived":
        archived = _timestamp(header.get("archived_at"), "archived_at")
        if not created <= archived <= updated:
            raise ValueError("handoff archived_at must fall between created_at and updated_at")
    elif header.get("archived_at") is not None or header.get("superseded_by") is not None:
        raise ValueError("active handoffs cannot have archived_at or superseded_by")
    for field in ("supersedes", "superseded_by"):
        value = header.get(field)
        if value is not None and (
            not isinstance(value, str)
            or not SLUG_RE.fullmatch(value)
            or value == header["handoff_id"]
        ):
            raise ValueError(f"handoff {field} must name another handoff ID")


def _read_handoff(root: Path, project_id: str, handoff_id: str) -> Handoff:
    path = _handoff_path(root, handoff_id)
    header, body = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
    validate_handoff(header, body, path, project_id)
    return Handoff(path, header, body)


def read_handoff_at(vault: Path, project_id: str, handoff_id: str) -> Handoff:
    """Read one current or archived handoff without consuming it."""
    root = _handoff_root(vault, project_id)
    if not root.exists():
        raise ValueError(f"Handoff does not exist: {handoff_id}")
    with interprocess_lock(root / "lifecycle"):
        return _read_handoff(root, project_id, handoff_id)


def list_handoffs_at(
    vault: Path,
    project_id: str | None = None,
    *,
    include_archived: bool = False,
    task_id: str | None = None,
    archived_before: str | None = None,
) -> list[Handoff]:
    """List one or all vault projects' handoffs, newest first, with optional filters."""
    if task_id is not None and not SLUG_RE.fullmatch(task_id):
        raise ValueError("task_id must be a lowercase slug")
    cutoff = (
        _timestamp(archived_before, "archived_before") if archived_before is not None else None
    )
    if cutoff is not None and not include_archived:
        raise ValueError("archived_before requires include_archived")
    if (vault / "projects").is_symlink():
        raise ValueError("Handoff storage must not use symlinks: projects")
    project_ids = list_project_ids(vault) if project_id is None else [project_id]
    records: list[Handoff] = []
    for selected_project in project_ids:
        root = _handoff_root(vault, selected_project)
        if not root.exists():
            continue
        with interprocess_lock(root / "lifecycle"):
            records.extend(
                _read_handoff(root, selected_project, path.stem)
                for path in sorted(root.glob("*.md"))
            )
    selected = [
        record
        for record in records
        if (include_archived or record.header["status"] == "active")
        and (task_id is None or record.header["task_id"] == task_id)
        and (
            cutoff is None
            or (
                record.header["status"] == "archived"
                and _timestamp(record.header["archived_at"], "archived_at") < cutoff
            )
        )
    ]
    return sorted(
        selected,
        key=lambda record: (
            _timestamp(record.header["created_at"], "created_at"),
            str(record.header["project_id"]),
            str(record.header["handoff_id"]),
        ),
        reverse=True,
    )


def _archive_header(record: Handoff, superseded_by: str | None = None) -> dict[str, object]:
    now = max(
        datetime.now(UTC),
        _timestamp(record.header["updated_at"], "updated_at") + timedelta(microseconds=1),
    ).isoformat()
    return {
        **record.header,
        "status": "archived",
        "updated_at": now,
        "archived_at": now,
        "superseded_by": superseded_by,
    }


def _write_handoff(path: Path, header: dict[str, object], body: str) -> None:
    validate_handoff(header, body, path, str(header["project_id"]))
    atomic_write_text(path, render_front_matter(header) + "\n" + body.rstrip() + "\n")


def _check_predecessor(
    previous: Handoff, task_id: str | None, expected_updated_at: str | None
) -> None:
    if previous.header["updated_at"] != expected_updated_at:
        raise ValueError("handoff replacement conflict: expected_updated_at is stale")
    if previous.header["status"] != "active":
        raise ValueError("Only an active handoff can be replaced")
    if task_id is not None and task_id != previous.header["task_id"]:
        raise ValueError("A replacement must keep the predecessor's task_id")


def create_handoff_at(
    vault: Path,
    project_id: str,
    *,
    title: str,
    goal: str,
    done_when: str,
    body: str,
    handoff_id: str | None = None,
    task_id: str | None = None,
    supersedes: str | None = None,
    expected_updated_at: str | None = None,
) -> Handoff:
    """Create an immutable snapshot and archive its explicitly selected predecessor."""
    root = _handoff_root(vault, project_id)
    document_id = handoff_id if handoff_id is not None else f"handoff-{secrets.token_hex(12)}"
    path = _handoff_path(root, document_id)
    with interprocess_lock(root / "lifecycle"):
        if path.exists():
            raise ValueError("handoff already exists; retrieve it or create a new snapshot ID")
        previous = _read_handoff(root, project_id, supersedes) if supersedes is not None else None
        if previous is None and expected_updated_at is not None:
            raise ValueError("expected_updated_at requires supersedes")
        if previous is not None:
            _check_predecessor(previous, task_id, expected_updated_at)
            task_id = str(previous.header["task_id"])
        task_id = task_id if task_id is not None else document_id
        for existing in root.glob("*.md"):
            current = _read_handoff(root, project_id, existing.stem)
            if (
                current.header["task_id"] == task_id
                and current.header["status"] == "active"
                and current.header["handoff_id"] != supersedes
            ):
                raise ValueError("Task already has an active handoff; specify supersedes")
        now = datetime.now(UTC).isoformat()
        header: dict[str, object] = {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "handoff_id": document_id,
            "project_id": project_id,
            "task_id": task_id,
            "title": title,
            "goal": goal,
            "done_when": done_when,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "archived_at": None,
            "supersedes": supersedes,
            "superseded_by": None,
        }
        _write_handoff(path, header, body)
        if previous is not None:
            try:
                _write_handoff(
                    previous.path, _archive_header(previous, document_id), previous.body
                )
            except OSError:
                # Keep the predecessor authoritative if replacement cannot finish.
                path.unlink()
                raise
        return _read_handoff(root, project_id, document_id)


def archive_handoff_at(
    vault: Path, project_id: str, handoff_id: str, *, expected_updated_at: str
) -> Handoff:
    """Archive one snapshot after verifying the caller's inspected revision."""
    root = _handoff_root(vault, project_id)
    with interprocess_lock(root / "lifecycle"):
        current = _read_handoff(root, project_id, handoff_id)
        if current.header["updated_at"] != expected_updated_at:
            raise ValueError("handoff archive conflict: expected_updated_at is stale")
        if current.header["status"] == "active":
            _write_handoff(current.path, _archive_header(current), current.body)
        return _read_handoff(root, project_id, handoff_id)


def delete_handoff_at(
    vault: Path, project_id: str, handoff_id: str, *, expected_updated_at: str
) -> dict[str, object]:
    """Delete one archived snapshot at the inspected revision, preserving other records."""
    root = _handoff_root(vault, project_id)
    with interprocess_lock(root / "lifecycle"):
        current = _read_handoff(root, project_id, handoff_id)
        if current.header["updated_at"] != expected_updated_at:
            raise ValueError("handoff delete conflict: expected_updated_at is stale")
        if current.header["status"] != "archived":
            raise ValueError("Archive the handoff before deleting it")
        current.path.unlink()
        return {
            "deleted": True,
            "project_id": project_id,
            "handoff_id": handoff_id,
            "path": str(current.path.relative_to(vault.resolve())),
        }


def validate_handoffs_at(vault: Path, project_id: str) -> tuple[int, list[dict[str, str]]]:
    """Audit project handoff schemas, locations, and uniqueness of active task snapshots."""
    expected_root = vault / "projects" / project_id / "handoffs"
    errors: list[dict[str, str]] = []
    checked = 0
    try:
        root = _handoff_root(vault, project_id)
    except (OSError, ValueError, RefineryCliError) as error:
        return 0, [{"path": str(expected_root.relative_to(vault)), "error": str(error)}]
    if not root.exists():
        return 0, []
    active: dict[str, str] = {}
    with interprocess_lock(root / "lifecycle"):
        for path in sorted(root.rglob("*.md")):
            try:
                if path.parent != root:
                    raise ValueError("Handoffs must be directly under projects/<project>/handoffs")
                record = _read_handoff(root, project_id, path.stem)
                task = str(record.header["task_id"])
                if record.header["status"] == "active":
                    if task in active:
                        raise ValueError(
                            f"Duplicate active handoffs for task {task}: {active[task]}"
                        )
                    active[task] = path.stem
                checked += 1
            except (OSError, ValueError, RefineryCliError) as error:
                errors.append({"path": str(path.relative_to(vault)), "error": str(error)})
    return checked, errors
