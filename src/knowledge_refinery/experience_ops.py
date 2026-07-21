from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import re
import secrets

import yaml

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import durable_unlink
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import ProjectContext
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import resolve_project_context


EXPERIENCE_STATUS_CHOICES = ("completed", "inconclusive", "abandoned", "superseded")
CONFIDENCE_CHOICES = ("low", "medium", "high")
MEMORY_SCOPE_CHOICES = ("project", "shared")
MEMORY_STATUS_CHOICES = ("active", "superseded", "retracted")
EVIDENCE_TYPE_CHOICES = ("file", "git", "mlflow", "url", "external")
EVIDENCE_RETENTION_CHOICES = ("reference", "external", "source")
EVIDENCE_GIT_STATE_CHOICES = ("tracked", "untracked", "modified", "staged", "ignored", "deleted")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_TAG_DEPTH = 3
KNOWLEDGE_TAG_FACETS = ("domain", "artifact", "task", "tech", "issue")


@dataclass(frozen=True)
class SearchEntry:
    path: Path
    project_id: str
    document_id: str
    title: str
    kind: str
    summary: str | None
    status: str | None
    scope: str | None
    confidence: str | None
    tags: tuple[str, ...]
    recorded_at: str | None
    updated_at: str


@dataclass(frozen=True)
class SearchFilters:
    document_ids: tuple[str, ...] = ()
    source_experiences: tuple[str, ...] = ()
    related_experiences: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    confidences: tuple[str, ...] = ()
    recorded_from: datetime | None = None
    recorded_to: datetime | None = None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "experience"


def _new_id(title: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{_slug(title)[:40]}-{secrets.token_hex(8)}"


def _render(header: dict[str, object], body: str) -> str:
    yaml_text = yaml.safe_dump(header, sort_keys=False, allow_unicode=True).rstrip()
    return f"---\n{yaml_text}\n---\n\n{body.rstrip()}\n"


def _default_experience_body() -> str:
    return (
        "## 試したこと\n\n- \n\n"
        "## 分かったこと\n\n- \n\n"
        "## 微妙だった点・限界\n\n- \n\n"
        "## 次の可能性\n\n- \n"
    )


def _preserved_string_list(
    current: dict[str, object] | None, field: str, supplied: list[str] | None
) -> list[str]:
    if current is not None and supplied is None:
        value = current[field]
        assert isinstance(value, list)
        return [str(item) for item in value]
    return list(supplied or [])


def _effective_confidence(
    current: dict[str, object] | None,
    supplied: str | None,
    *,
    clear: bool,
) -> str | None:
    if clear:
        return None
    if current is not None and supplied is None:
        value = current.get("confidence")
        return str(value) if value is not None else None
    return supplied


def _effective_optional_string(
    current: dict[str, object] | None,
    field: str,
    supplied: str | None,
    *,
    clear: bool,
) -> str | None:
    if clear:
        return None
    if current is not None and supplied is None:
        value = current.get(field)
        return str(value) if value is not None else None
    return supplied


def _memory_status(header: dict[str, object]) -> str:
    return str(header.get("status", "active"))


def _preserved_evidence(
    current: dict[str, object] | None,
    supplied: Sequence[str | dict[str, str]] | None,
) -> list[dict[str, str]]:
    if current is not None and supplied is None:
        value = current["evidence"]
        assert isinstance(value, list)
        return [dict(item) for item in value if isinstance(item, dict)]
    return normalize_evidence(supplied or [])


def _validate_experience_options(
    *,
    status: str,
    document_id: str,
    filename: str | None,
    related_experiences: list[str] | None,
    supersedes: list[str] | None,
    confidence: str | None,
    clear_confidence: bool,
) -> None:
    if status not in EXPERIENCE_STATUS_CHOICES:
        raise ValueError(f"Unsupported experience status: {status}")
    if not SLUG_RE.fullmatch(document_id):
        raise ValueError("experience_id must be a lowercase slug")
    if filename is not None and filename != f"{document_id}.md":
        raise ValueError("experience filename must match experience_id")
    if related_experiences is not None:
        _validate_slugs(related_experiences, field="related_experiences")
    if supersedes is not None:
        _validate_slugs(supersedes, field="supersedes")
    if clear_confidence and confidence is not None:
        raise ValueError("confidence and clear_confidence cannot be used together")
    _validate_confidence(confidence)


def parse_evidence_reference(reference: str) -> dict[str, str]:
    prefix, separator, value = reference.partition(":")
    if not separator or not value:
        raise ValueError(f"Invalid evidence reference: {reference}")
    if prefix == "untracked":
        return {
            "type": "file",
            "path": value,
            "git_state": "untracked",
            "retention": "reference",
        }
    if prefix == "file":
        return {"type": "file", "path": value, "retention": "reference"}
    if prefix == "git":
        commit, commit_separator, path = value.partition(":")
        if not commit_separator or not path:
            raise ValueError("git evidence must use git:<commit>:<path>")
        return {"type": "git", "commit": commit, "path": path, "retention": "source"}
    if prefix == "mlflow":
        return {"type": "mlflow", "uri": value, "retention": "external"}
    if prefix == "url":
        return {"type": "url", "uri": value, "retention": "external"}
    if prefix == "external":
        return {"type": "external", "uri": value, "retention": "external"}
    raise ValueError(f"Unsupported evidence type: {prefix}")


def upsert_experience(
    project: Path,
    *,
    title: str,
    purpose: str,
    status: str,
    experience_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    evidence: list[str] | None,
    related_experiences: list[str] | None,
    supersedes: list[str] | None,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
) -> Path:
    context = resolve_project_context(project)
    return _upsert_experience(
        context,
        title=title,
        purpose=purpose,
        status=status,
        experience_id=experience_id,
        filename=filename,
        tags=tags,
        evidence=evidence,
        related_experiences=related_experiences,
        supersedes=supersedes,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
    )


def upsert_experience_at(
    vault: Path,
    project_id: str,
    *,
    title: str,
    purpose: str,
    status: str,
    experience_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    evidence: list[dict[str, str]] | None,
    related_experiences: list[str] | None,
    supersedes: list[str] | None,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
) -> Path:
    context = context_from_vault(vault, project_id)
    return _upsert_experience(
        context,
        title=title,
        purpose=purpose,
        status=status,
        experience_id=experience_id,
        filename=filename,
        tags=tags,
        evidence=evidence,
        related_experiences=related_experiences,
        supersedes=supersedes,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
    )


def _upsert_experience(
    context: ProjectContext,
    *,
    title: str,
    purpose: str,
    status: str,
    experience_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    evidence: Sequence[str | dict[str, str]] | None,
    related_experiences: list[str] | None,
    supersedes: list[str] | None,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None,
    clear_confidence: bool,
) -> Path:
    document_id = experience_id or _new_id(title)
    expected_filename = f"{document_id}.md"
    _validate_experience_options(
        status=status,
        document_id=document_id,
        filename=filename,
        related_experiences=related_experiences,
        supersedes=supersedes,
        confidence=confidence,
        clear_confidence=clear_confidence,
    )
    path = _document_path(context, "experiences", expected_filename)
    with interprocess_lock(context.vault_root / "knowledge-documents"):
        with interprocess_lock(path):
            created_at = datetime.now(UTC).isoformat()
            current: dict[str, object] | None = None
            if path.exists():
                current, current_body = split_front_matter(
                    path.read_text(encoding="utf-8"), source_path=path
                )
                validate_document_header(current, kind="experiences")
                current_updated_at = str(current.get("updated_at", ""))
                if expected_updated_at is None:
                    raise ValueError(
                        "experience already exists; read it and pass expected_updated_at to update"
                    )
                if expected_updated_at != current_updated_at:
                    raise ValueError("experience update conflict: expected_updated_at is stale")
                created_at = str(current.get("recorded_at", created_at))
                if body is None:
                    body = current_body
            elif expected_updated_at is not None:
                raise ValueError(
                    "experience does not exist; omit expected_updated_at to create it"
                )
            effective_tags = _preserved_string_list(current, "tags", tags)
            structured_evidence = _preserved_evidence(current, evidence)
            effective_related = _preserved_string_list(
                current, "related_experiences", related_experiences
            )
            effective_supersedes = _preserved_string_list(current, "supersedes", supersedes)
            effective_confidence = _effective_confidence(
                current, confidence, clear=clear_confidence
            )
            header: dict[str, object] = {
                "schema_version": 2,
                "experience_id": document_id,
                "project_id": context.project_id,
                "title": title,
                "purpose": purpose,
                "status": status,
                "recorded_at": created_at,
                "updated_at": datetime.now(UTC).isoformat(),
                "tags": effective_tags,
                "evidence": structured_evidence,
                "related_experiences": effective_related,
                "supersedes": effective_supersedes,
                "confidence": effective_confidence,
            }
            validate_document_header(header, kind="experiences")
            validate_experience_references(context.vault_root, header)
            atomic_write_text(path, _render(header, body or _default_experience_body()))
    return path


def upsert_memory(
    project: Path,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    source_experiences: list[str] | None,
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
    status: str | None = None,
    superseded_by: str | None = None,
    clear_superseded_by: bool = False,
) -> Path:
    context = resolve_project_context(project)
    return _upsert_memory(
        context,
        title=title,
        summary=summary,
        memory_id=memory_id,
        filename=filename,
        tags=tags,
        source_experiences=source_experiences,
        shared=shared,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
        status=status,
        superseded_by=superseded_by,
        clear_superseded_by=clear_superseded_by,
    )


def upsert_memory_at(
    vault: Path,
    project_id: str,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    source_experiences: list[str] | None,
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
    status: str | None = None,
    superseded_by: str | None = None,
    clear_superseded_by: bool = False,
) -> Path:
    context = context_from_vault(vault, project_id)
    return _upsert_memory(
        context,
        title=title,
        summary=summary,
        memory_id=memory_id,
        filename=filename,
        tags=tags,
        source_experiences=source_experiences,
        shared=shared,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
        status=status,
        superseded_by=superseded_by,
        clear_superseded_by=clear_superseded_by,
    )


def _validate_memory_options(
    *,
    document_id: str,
    filename: str | None,
    confidence: str | None,
    clear_confidence: bool,
    status: str | None,
    superseded_by: str | None,
    clear_superseded_by: bool,
) -> None:
    if not SLUG_RE.fullmatch(document_id):
        raise ValueError("memory_id must be a lowercase slug")
    if filename is not None and filename != f"{document_id}.md":
        raise ValueError("memory filename must match memory_id")
    if clear_confidence and confidence is not None:
        raise ValueError("confidence and clear_confidence cannot be used together")
    if clear_superseded_by and superseded_by is not None:
        raise ValueError("superseded_by and clear_superseded_by cannot be used together")
    if status is not None and status not in MEMORY_STATUS_CHOICES:
        raise ValueError(f"Unsupported memory status: {status}")
    if superseded_by is not None:
        _validate_slugs([superseded_by], field="superseded_by")
    _validate_confidence(confidence)


def _upsert_memory(
    context: ProjectContext,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str] | None,
    source_experiences: list[str] | None,
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None,
    clear_confidence: bool,
    status: str | None,
    superseded_by: str | None,
    clear_superseded_by: bool,
) -> Path:
    document_id = memory_id or _slug(title)
    _validate_memory_options(
        document_id=document_id,
        filename=filename,
        confidence=confidence,
        clear_confidence=clear_confidence,
        status=status,
        superseded_by=superseded_by,
        clear_superseded_by=clear_superseded_by,
    )
    expected_filename = f"{document_id}.md"
    root = context.vault_root / "shared" / "memory" if shared else context.project_store / "memory"
    path = _safe_child(root, expected_filename)
    with interprocess_lock(context.vault_root / "knowledge-documents"):
        with interprocess_lock(path):
            current: dict[str, object] | None = None
            if path.exists():
                current, current_body = split_front_matter(
                    path.read_text(encoding="utf-8"), source_path=path
                )
                validate_document_header(current, kind="memory")
                current_updated_at = str(current.get("updated_at", ""))
                if expected_updated_at is None:
                    raise ValueError(
                        "memory already exists; read it and pass expected_updated_at to update"
                    )
                if expected_updated_at != current_updated_at:
                    raise ValueError("memory update conflict: expected_updated_at is stale")
                if body is None:
                    body = current_body
            elif expected_updated_at is not None:
                raise ValueError("memory does not exist; omit expected_updated_at to create it")
            effective_sources = _preserved_string_list(
                current, "source_experiences", source_experiences
            )
            if not effective_sources:
                raise ValueError("memory requires at least one --source-experience")
            _validate_memory_sources(context, effective_sources, shared=shared)
            effective_tags = _preserved_string_list(current, "tags", tags)
            effective_confidence = _effective_confidence(
                current, confidence, clear=clear_confidence
            )
            effective_status = status or (_memory_status(current) if current else "active")
            effective_superseded_by = _effective_optional_string(
                current,
                "superseded_by",
                superseded_by,
                clear=clear_superseded_by,
            )
            header: dict[str, object] = {
                "schema_version": 2,
                "memory_id": document_id,
                "scope": "shared" if shared else "project",
                "project_id": None if shared else context.project_id,
                "title": title,
                "summary": summary,
                "status": effective_status,
                "superseded_by": effective_superseded_by,
                "source_experiences": effective_sources,
                "updated_at": datetime.now(UTC).isoformat(),
                "tags": effective_tags,
                "confidence": effective_confidence,
            }
            validate_document_header(header, kind="memory")
            validate_memory_source_references(context.vault_root, header)
            atomic_write_text(path, _render(header, body or summary))
    return path


def search_documents(
    project: Path,
    *,
    kind: str,
    terms: list[str],
    project_ids: list[str],
    tags: list[str],
    statuses: list[str],
    all_projects: bool,
    filters: SearchFilters | None = None,
) -> list[SearchEntry]:
    if kind not in {"experiences", "memory"}:
        raise ValueError(f"Unsupported document kind: {kind}")
    context = resolve_project_context(project)
    return _search_documents(
        context,
        kind=kind,
        terms=terms,
        project_ids=project_ids,
        tags=tags,
        statuses=statuses,
        all_projects=all_projects,
        filters=filters,
    )


def search_documents_at(
    vault: Path,
    current_project_id: str,
    *,
    kind: str,
    terms: list[str],
    project_ids: list[str],
    tags: list[str],
    statuses: list[str],
    all_projects: bool,
    filters: SearchFilters | None = None,
) -> list[SearchEntry]:
    context = context_from_vault(vault, current_project_id)
    return _search_documents(
        context,
        kind=kind,
        terms=terms,
        project_ids=project_ids,
        tags=tags,
        statuses=statuses,
        all_projects=all_projects,
        filters=filters,
    )


def _search_documents(
    context: ProjectContext,
    *,
    kind: str,
    terms: list[str],
    project_ids: list[str],
    tags: list[str],
    statuses: list[str],
    all_projects: bool,
    filters: SearchFilters | None,
) -> list[SearchEntry]:
    if kind not in {"experiences", "memory"}:
        raise ValueError(f"Unsupported document kind: {kind}")
    active_filters = filters or SearchFilters()
    _validate_search_inputs(
        kind=kind,
        project_ids=project_ids,
        tags=tags,
        statuses=statuses,
        all_projects=all_projects,
        filters=active_filters,
    )
    for selected_project_id in project_ids:
        context_from_vault(context.vault_root, selected_project_id)
    selected = project_ids or ([context.project_id] if not all_projects else [])
    roots = _search_roots(context, kind, selected, all_projects=all_projects)
    effective_statuses = statuses or (["active"] if kind == "memory" else [])

    entries: list[SearchEntry] = []
    lowered_terms = [term.casefold() for term in terms]
    for project_id, root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == "AGENTS.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
                header, _ = split_front_matter(text, source_path=path)
                validate_document_header(header, kind=kind)
            except (OSError, ValueError, RefineryCliError):
                # Keep healthy knowledge searchable. refinery_validate reports the
                # malformed document with its path and exact reason.
                continue
            haystack = text.casefold()
            if any(term not in haystack for term in lowered_terms):
                continue
            if not _matches_filters(
                header,
                tags=tags,
                statuses=effective_statuses,
                filters=active_filters,
                kind=kind,
            ):
                continue
            id_key = "experience_id" if kind == "experiences" else "memory_id"
            header_tags = header["tags"]
            assert isinstance(header_tags, list)
            entries.append(
                SearchEntry(
                    path=path,
                    project_id=project_id,
                    document_id=str(header.get(id_key, path.stem)),
                    title=str(header.get("title", path.stem)),
                    kind="experience" if kind == "experiences" else "memory",
                    summary=(
                        str(header["summary"]) if kind == "memory" else str(header["purpose"])
                    ),
                    status=(
                        str(header["status"]) if kind == "experiences" else _memory_status(header)
                    ),
                    scope=(str(header["scope"]) if kind == "memory" else None),
                    confidence=(
                        str(header["confidence"]) if header.get("confidence") is not None else None
                    ),
                    tags=tuple(str(tag) for tag in header_tags),
                    recorded_at=(str(header["recorded_at"]) if kind == "experiences" else None),
                    updated_at=str(header["updated_at"]),
                )
            )
    entries.sort(
        key=lambda entry: parse_datetime_filter(entry.updated_at, end_of_day=False),
        reverse=True,
    )
    return entries


def _validate_search_inputs(
    *,
    kind: str,
    project_ids: list[str],
    tags: list[str],
    statuses: list[str],
    all_projects: bool,
    filters: SearchFilters,
) -> None:
    if all_projects and project_ids:
        raise ValueError("project_ids and all_projects cannot be used together")
    _validate_slugs(project_ids, field="project_ids")
    _validate_knowledge_tags(tags)
    status_choices = EXPERIENCE_STATUS_CHOICES if kind == "experiences" else MEMORY_STATUS_CHOICES
    invalid_statuses = sorted(set(statuses).difference(status_choices))
    if invalid_statuses:
        label = "experience" if kind == "experiences" else "memory"
        raise ValueError(f"Unsupported {label} statuses: {', '.join(invalid_statuses)}")
    _validate_slugs(list(filters.document_ids), field="document_ids")
    _validate_slugs(list(filters.related_experiences), field="related_experiences")
    invalid_evidence = sorted(set(filters.evidence_types).difference(EVIDENCE_TYPE_CHOICES))
    if invalid_evidence:
        raise ValueError(f"Unsupported evidence types: {', '.join(invalid_evidence)}")
    invalid_scopes = sorted(set(filters.scopes).difference(MEMORY_SCOPE_CHOICES))
    if invalid_scopes:
        raise ValueError(f"Unsupported memory scopes: {', '.join(invalid_scopes)}")
    invalid_confidences = sorted(set(filters.confidences).difference(CONFIDENCE_CHOICES))
    if invalid_confidences:
        raise ValueError(f"Unsupported confidences: {', '.join(invalid_confidences)}")


def read_experience_at(
    vault: Path, project_id: str, experience_id: str
) -> tuple[Path, dict[str, object], str]:
    context = context_from_vault(vault, project_id)
    _validate_slugs([experience_id], field="experience_id")
    path = _find_document_path(context.project_store / "experiences", experience_id)
    header, body = _read_exact_document(path, kind="experiences")
    if header.get("experience_id") != experience_id or header.get("project_id") != project_id:
        raise ValueError("experience ID and project_id must match its path")
    return path, header, body


def read_memory_at(
    vault: Path,
    current_project_id: str,
    memory_id: str,
    *,
    scope: str,
    project_id: str | None = None,
) -> tuple[Path, dict[str, object], str]:
    context = context_from_vault(vault, current_project_id)
    _validate_slugs([memory_id], field="memory_id")
    if scope == "shared":
        if project_id is not None:
            raise ValueError("project_id must be omitted for shared memory")
        root = context.vault_root / "shared" / "memory"
        expected_project_id: str | None = None
    elif scope == "project":
        expected_project_id = project_id or current_project_id
        target = context_from_vault(context.vault_root, expected_project_id)
        root = target.project_store / "memory"
    else:
        raise ValueError("scope must be project or shared")
    path = _find_document_path(root, memory_id)
    header, body = _read_exact_document(path, kind="memory")
    if header.get("memory_id") != memory_id or header.get("scope") != scope:
        raise ValueError("memory ID and scope must match its path")
    if header.get("project_id") != expected_project_id:
        raise ValueError("memory project_id must match its path")
    return path, header, body


def delete_experience_at(
    vault: Path,
    project_id: str,
    experience_id: str,
    *,
    expected_updated_at: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Inspect or delete an experience only when no structured references remain."""
    context = context_from_vault(vault, project_id)
    _validate_slugs([experience_id], field="experience_id")
    path = _safe_child(context.project_store / "experiences", f"{experience_id}.md")
    return _delete_document_at(
        vault,
        path,
        kind="experience",
        document_id=experience_id,
        project_id=project_id,
        scope=None,
        expected_updated_at=expected_updated_at,
        confirm=confirm,
    )


def delete_memory_at(
    vault: Path,
    current_project_id: str,
    memory_id: str,
    *,
    scope: str,
    project_id: str | None,
    expected_updated_at: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Inspect or delete a memory only when no predecessor references it."""
    path, header, _ = read_memory_at(
        vault,
        current_project_id,
        memory_id,
        scope=scope,
        project_id=project_id,
    )
    owner = header.get("project_id")
    return _delete_document_at(
        vault,
        path,
        kind="memory",
        document_id=memory_id,
        project_id=str(owner) if owner is not None else None,
        scope=scope,
        expected_updated_at=expected_updated_at,
        confirm=confirm,
    )


def _delete_document_at(
    vault: Path,
    path: Path,
    *,
    kind: str,
    document_id: str,
    project_id: str | None,
    scope: str | None,
    expected_updated_at: str,
    confirm: bool,
) -> dict[str, object]:
    validation_kind = "experiences" if kind == "experience" else "memory"
    with interprocess_lock(vault / "knowledge-documents"):
        with interprocess_lock(path):
            header, _ = _read_exact_document(path, kind=validation_kind)
            _validate_delete_target(
                header,
                kind=kind,
                document_id=document_id,
                project_id=project_id,
                scope=scope,
            )
            if str(header.get("updated_at", "")) != expected_updated_at:
                raise ValueError(f"{kind} delete conflict: expected_updated_at is stale")
            references, validation_errors = _scan_delete_dependencies(
                vault,
                target_path=path,
                kind=kind,
                document_id=document_id,
                project_id=project_id,
                scope=scope,
            )
            can_delete = not references and not validation_errors
            deleted = bool(confirm and can_delete)
            if deleted:
                durable_unlink(path)
            return {
                "kind": kind,
                "id": document_id,
                "project_id": project_id,
                "scope": scope,
                "path": str(path.relative_to(vault)),
                "updated_at": str(header["updated_at"]),
                "can_delete": can_delete,
                "confirmation_required": bool(can_delete and not confirm),
                "deleted": deleted,
                "references": references,
                "validation_errors": validation_errors,
            }


def _validate_delete_target(
    header: dict[str, object],
    *,
    kind: str,
    document_id: str,
    project_id: str | None,
    scope: str | None,
) -> None:
    if kind == "experience":
        if header.get("experience_id") != document_id or header.get("project_id") != project_id:
            raise ValueError("experience ID and project_id must match its delete target")
        return
    if header.get("memory_id") != document_id or header.get("scope") != scope:
        raise ValueError("memory ID and scope must match its delete target")
    if header.get("project_id") != project_id:
        raise ValueError("memory project_id must match its delete target")


def _scan_delete_dependencies(
    vault: Path,
    *,
    target_path: Path,
    kind: str,
    document_id: str,
    project_id: str | None,
    scope: str | None,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    references: list[dict[str, object]] = []
    validation_errors: list[dict[str, str]] = []
    for path, document_kind in _iter_knowledge_documents(vault):
        if path == target_path:
            continue
        try:
            header, _ = _read_exact_document(path, kind=document_kind)
            if document_kind == "experiences":
                validate_experience_references(vault, header)
            else:
                validate_memory_source_references(vault, header)
        except (OSError, ValueError, RefineryCliError) as error:
            validation_errors.append({"path": str(path.relative_to(vault)), "error": str(error)})
            continue
        fields = _dependency_fields(
            header,
            document_kind=document_kind,
            target_kind=kind,
            document_id=document_id,
            project_id=project_id,
            scope=scope,
        )
        for field in fields:
            references.append(
                {
                    "kind": "experience" if document_kind == "experiences" else "memory",
                    "id": header.get(
                        "experience_id" if document_kind == "experiences" else "memory_id"
                    ),
                    "project_id": header.get("project_id"),
                    "scope": header.get("scope"),
                    "field": field,
                    "path": str(path.relative_to(vault)),
                }
            )
    return references, validation_errors


def _dependency_fields(
    header: dict[str, object],
    *,
    document_kind: str,
    target_kind: str,
    document_id: str,
    project_id: str | None,
    scope: str | None,
) -> list[str]:
    if target_kind == "memory":
        is_same_scope = (
            document_kind == "memory"
            and header.get("scope") == scope
            and header.get("project_id") == project_id
        )
        has_successor = header.get("superseded_by") == document_id
        return ["superseded_by"] if is_same_scope and has_successor else []
    if document_kind == "memory":
        return (
            ["source_experiences"]
            if _memory_uses_experience(header, project_id, document_id)
            else []
        )
    if header.get("project_id") != project_id:
        return []
    fields: list[str] = []
    for field in ("related_experiences", "supersedes"):
        values = header.get(field)
        if isinstance(values, list) and document_id in values:
            fields.append(field)
    return fields


def _iter_knowledge_documents(vault: Path) -> list[tuple[Path, str]]:
    documents: list[tuple[Path, str]] = []
    projects_root = vault / "projects"
    if projects_root.is_dir():
        for project in sorted(projects_root.iterdir()):
            if not project.is_dir():
                continue
            for directory, kind in (("experiences", "experiences"), ("memory", "memory")):
                root = project / directory
                if root.is_dir():
                    documents.extend(
                        (path, kind)
                        for path in sorted(root.rglob("*.md"))
                        if path.name != "AGENTS.md"
                    )
    shared_root = vault / "shared" / "memory"
    if shared_root.is_dir():
        documents.extend(
            (path, "memory")
            for path in sorted(shared_root.rglob("*.md"))
            if path.name != "AGENTS.md"
        )
    return documents


def _memory_uses_experience(
    header: dict[str, object], project_id: str | None, experience_id: str
) -> bool:
    sources = header.get("source_experiences", [])
    if not isinstance(sources, list):
        return False
    for source in sources:
        if not isinstance(source, str):
            continue
        qualified_project, source_id = _split_source_reference(source)
        owner = qualified_project or header.get("project_id")
        if owner == project_id and source_id == experience_id:
            return True
    return False


def _read_exact_document(path: Path, *, kind: str) -> tuple[dict[str, object], str]:
    header, body = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
    validate_document_header(header, kind=kind)
    return header, body


def _find_document_path(root: Path, document_id: str) -> Path:
    direct = _safe_child(root, f"{document_id}.md")
    if direct.is_file():
        return direct
    candidates = sorted(root.rglob(f"{document_id}.md")) if root.is_dir() else []
    if not candidates:
        raise ValueError(f"Unknown refinery document: {document_id}")
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous refinery document ID: {document_id}")
    return candidates[0]


def _search_roots(
    context: ProjectContext, kind: str, selected: list[str], *, all_projects: bool
) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    for project_dir in sorted((context.vault_root / "projects").iterdir()):
        if not project_dir.is_dir() or (selected and project_dir.name not in selected):
            continue
        roots.append((project_dir.name, project_dir / kind))
    if kind == "memory":
        roots.append(("shared", context.vault_root / "shared" / "memory"))
    return roots


def _matches_filters(
    header: dict[str, object],
    *,
    tags: list[str],
    statuses: list[str],
    filters: SearchFilters,
    kind: str,
) -> bool:
    current_tags = header.get("tags", [])
    if not isinstance(current_tags, list) or any(
        not any(_tag_matches(current, requested) for current in current_tags) for requested in tags
    ):
        return False
    current_status = header.get("status") if kind == "experiences" else _memory_status(header)
    if statuses and current_status not in statuses:
        return False
    id_key = "experience_id" if kind == "experiences" else "memory_id"
    if filters.document_ids and header.get(id_key) not in filters.document_ids:
        return False
    if not _contains_all(header, "source_experiences", filters.source_experiences):
        return False
    if not _contains_all(header, "related_experiences", filters.related_experiences):
        return False
    if filters.scopes and header.get("scope") not in filters.scopes:
        return False
    if filters.confidences and header.get("confidence") not in filters.confidences:
        return False
    if filters.evidence_types and not _matches_evidence_types(header, filters.evidence_types):
        return False
    return _matches_recorded_range(header, filters)


def _tag_matches(current: object, requested: str) -> bool:
    return isinstance(current, str) and (
        current == requested or current.startswith(f"{requested}/")
    )


def _contains_all(header: dict[str, object], key: str, expected: tuple[str, ...]) -> bool:
    if not expected:
        return True
    current = header.get(key, [])
    return isinstance(current, list) and all(value in current for value in expected)


def _matches_evidence_types(header: dict[str, object], expected: tuple[str, ...]) -> bool:
    evidence = header.get("evidence", [])
    if not isinstance(evidence, list):
        return False
    current_types = {
        item.get("type")
        for item in evidence
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    }
    return all(value in current_types for value in expected)


def _matches_recorded_range(header: dict[str, object], filters: SearchFilters) -> bool:
    if filters.recorded_from is None and filters.recorded_to is None:
        return True
    value = header.get("recorded_at", header.get("updated_at"))
    if not isinstance(value, str):
        return False
    recorded_at = parse_datetime_filter(value, end_of_day=False)
    if filters.recorded_from is not None and recorded_at < filters.recorded_from:
        return False
    return filters.recorded_to is None or recorded_at <= filters.recorded_to


def parse_datetime_filter(value: str, *, end_of_day: bool) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"Invalid ISO date or datetime: {value}") from error
    if len(value) == 10:
        parsed = parsed.replace(
            hour=23 if end_of_day else 0,
            minute=59 if end_of_day else 0,
            second=59 if end_of_day else 0,
            microsecond=999999 if end_of_day else 0,
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def validate_document_header(header: dict[str, object], *, kind: str) -> None:
    if header.get("schema_version") != 2:
        raise ValueError("refinery document requires schema_version: 2")
    required = (
        (
            "experience_id",
            "project_id",
            "title",
            "purpose",
            "status",
            "recorded_at",
            "updated_at",
        )
        if kind == "experiences"
        else ("memory_id", "scope", "title", "summary", "updated_at")
    )
    for field in required:
        if not isinstance(header.get(field), str) or not str(header[field]).strip():
            raise ValueError(f"{kind} header requires non-empty string field: {field}")
    _validate_string_list(header, "tags")
    _validate_knowledge_tags(header["tags"])
    if kind == "experiences":
        _validate_slugs(
            [str(header["experience_id"]), str(header["project_id"])],
            field="experience_id and project_id",
        )
        status = header["status"]
        if status not in EXPERIENCE_STATUS_CHOICES:
            raise ValueError(f"Unsupported experience status: {status}")
        _validate_string_list(header, "related_experiences")
        _validate_string_list(header, "supersedes")
        related = header["related_experiences"]
        supersedes = header["supersedes"]
        assert isinstance(related, list)
        assert isinstance(supersedes, list)
        _validate_slugs([str(value) for value in related], field="related_experiences")
        _validate_slugs([str(value) for value in supersedes], field="supersedes")
        _validate_evidence(header.get("evidence"))
        _validate_document_timestamp(header["recorded_at"], field="recorded_at")
    else:
        _validate_memory_header(header)
    _validate_document_timestamp(header["updated_at"], field="updated_at")
    confidence = header.get("confidence")
    if confidence is not None and confidence not in CONFIDENCE_CHOICES:
        raise ValueError(f"Unsupported confidence: {confidence}")


def _validate_string_list(
    header: dict[str, object], field: str, *, require_nonempty: bool = False
) -> None:
    value = header.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    if require_nonempty and not value:
        raise ValueError(f"{field} must not be empty")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")


def _validate_knowledge_tags(value: object) -> None:
    assert isinstance(value, list)
    tags = [str(tag) for tag in value]
    if len(tags) != len(set(tags)):
        raise ValueError("tags must not contain duplicates")
    for tag in tags:
        segments = tag.split("/")
        if len(segments) > MAX_TAG_DEPTH or any(
            not SLUG_RE.fullmatch(segment) for segment in segments
        ):
            raise ValueError("tags must use one to three lowercase slug segments separated by /")
        if segments[0] not in KNOWLEDGE_TAG_FACETS:
            raise ValueError(
                "tags must start with a standard facet: " + ", ".join(KNOWLEDGE_TAG_FACETS)
            )


def _validate_memory_header(header: dict[str, object]) -> None:
    _validate_slugs([str(header["memory_id"])], field="memory_id")
    _validate_memory_lifecycle(header)
    scope = header["scope"]
    if scope not in MEMORY_SCOPE_CHOICES:
        raise ValueError(f"Unsupported memory scope: {scope}")
    _validate_string_list(header, "source_experiences", require_nonempty=True)
    source_experiences = header["source_experiences"]
    assert isinstance(source_experiences, list)
    if scope == "shared":
        _validate_shared_source_format(source_experiences)
        if header.get("project_id") is not None:
            raise ValueError("shared memory project_id must be null")
        return
    project_id = header.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("project memory requires non-empty project_id")
    _validate_project_source_format(source_experiences, project_id)


def _validate_memory_lifecycle(header: dict[str, object]) -> None:
    status = _memory_status(header)
    if status not in MEMORY_STATUS_CHOICES:
        raise ValueError(f"Unsupported memory status: {status}")
    superseded_by = header.get("superseded_by")
    if superseded_by is not None:
        if not isinstance(superseded_by, str):
            raise ValueError("superseded_by must be a lowercase memory slug or null")
        _validate_slugs([superseded_by], field="superseded_by")
        if superseded_by == header["memory_id"]:
            raise ValueError("superseded_by must not reference the memory itself")
    if status == "superseded" and superseded_by is None:
        raise ValueError("superseded memory requires superseded_by")
    if status != "superseded" and superseded_by is not None:
        raise ValueError("superseded_by is only valid when memory status is superseded")


def _validate_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("evidence must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be a mapping")
        _validate_evidence_item(item)


def _validate_evidence_item(item: dict[object, object]) -> None:
    evidence_type = item.get("type")
    retention = item.get("retention")
    if evidence_type not in EVIDENCE_TYPE_CHOICES:
        raise ValueError(f"Unsupported evidence type: {evidence_type}")
    if retention not in EVIDENCE_RETENTION_CHOICES:
        raise ValueError(f"Unsupported evidence retention: {retention}")

    allowed_retentions = {
        "file": {"reference"},
        "git": {"source"},
        "mlflow": {"external"},
        "url": {"external"},
        "external": {"external"},
    }
    if retention not in allowed_retentions[str(evidence_type)]:
        raise ValueError(f"evidence type {evidence_type} does not support retention: {retention}")

    location_key = "path" if evidence_type in {"file", "git"} else "uri"
    if not isinstance(item.get(location_key), str) or not item[location_key]:
        raise ValueError(f"evidence type {evidence_type} requires {location_key}")
    _validate_evidence_fields(item, str(evidence_type))
    if location_key == "path":
        _validate_evidence_path(str(item[location_key]))
    if evidence_type == "git" and (not isinstance(item.get("commit"), str) or not item["commit"]):
        raise ValueError("evidence type git requires commit")
    git_state = item.get("git_state")
    if (
        evidence_type == "file"
        and git_state is not None
        and (not isinstance(git_state, str) or git_state not in EVIDENCE_GIT_STATE_CHOICES)
    ):
        expected = ", ".join(EVIDENCE_GIT_STATE_CHOICES)
        raise ValueError(
            f"Unsupported file evidence git_state: {git_state!r}; expected one of: {expected}"
        )


def _validate_evidence_fields(item: dict[object, object], evidence_type: str) -> None:
    allowed_fields = {
        "file": {"type", "path", "retention", "git_state"},
        "git": {"type", "path", "commit", "retention"},
        "mlflow": {"type", "uri", "retention"},
        "url": {"type", "uri", "retention"},
        "external": {"type", "uri", "retention"},
    }
    unexpected = sorted(
        str(field) for field in set(item).difference(allowed_fields[evidence_type])
    )
    if unexpected:
        raise ValueError(
            f"evidence type {evidence_type} has unsupported fields: {', '.join(unexpected)}"
        )


def _validate_evidence_path(value: str) -> None:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        raise ValueError("evidence path must be repository-relative and must not contain ..")


def normalize_evidence(
    evidence: Sequence[str | dict[str, str]],
) -> list[dict[str, str]]:
    normalized = [
        parse_evidence_reference(item) if isinstance(item, str) else dict(item)
        for item in evidence
    ]
    _validate_evidence(normalized)
    return normalized


def _validate_slugs(values: list[str], *, field: str) -> None:
    if any(not SLUG_RE.fullmatch(value) for value in values):
        raise ValueError(f"{field} values must be lowercase slugs")


def _validate_document_timestamp(value: object, *, field: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO 8601 timestamp with timezone")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO 8601 timestamp with timezone") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must be an ISO 8601 timestamp with timezone")


def _split_source_reference(reference: str) -> tuple[str | None, str]:
    project_id, separator, experience_id = reference.partition("/")
    if not separator:
        _validate_slugs([reference], field="source_experiences")
        return None, reference
    if not project_id or not experience_id or "/" in experience_id:
        raise ValueError("qualified source_experiences must use project-id/experience-id")
    _validate_slugs([project_id, experience_id], field="source_experiences")
    return project_id, experience_id


def _validate_shared_source_format(source_experiences: list[object]) -> None:
    qualified: list[tuple[str, str]] = []
    for source in source_experiences:
        if not isinstance(source, str):
            raise ValueError("source_experiences must be a list of strings")
        project_id, experience_id = _split_source_reference(source)
        if project_id is None:
            raise ValueError("shared memory source_experiences must use project-id/experience-id")
        qualified.append((project_id, experience_id))
    if len(qualified) < 2 or len({project_id for project_id, _ in qualified}) < 2:
        raise ValueError("shared memory requires experiences from at least two projects")


def _validate_project_source_format(
    source_experiences: list[object], current_project_id: str
) -> None:
    for source in source_experiences:
        if not isinstance(source, str):
            raise ValueError("source_experiences must be a list of strings")
        project_id, _ = _split_source_reference(source)
        if project_id is not None and project_id != current_project_id:
            raise ValueError("project memory cannot reference another project's experience")


def _validate_memory_sources(
    context: ProjectContext, source_experiences: list[str], *, shared: bool
) -> None:
    if shared:
        _validate_shared_source_format(list(source_experiences))
    else:
        _validate_project_source_format(list(source_experiences), context.project_id)

    for source in source_experiences:
        qualified_project, experience_id = _split_source_reference(source)
        project_id = qualified_project or context.project_id
        if not _experience_exists(context.vault_root, project_id, experience_id):
            raise ValueError(f"Unknown source experience: {project_id}/{experience_id}")


def _experience_exists(vault: Path, project_id: str, experience_id: str) -> bool:
    root = vault / "projects" / project_id / "experiences"
    direct = root / f"{experience_id}.md"
    candidates = [direct] if direct.is_file() else sorted(root.glob("*.md"))
    for path in candidates:
        try:
            header, _ = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
        except (OSError, ValueError):
            continue
        if header.get("project_id") == project_id and header.get("experience_id") == experience_id:
            return True
    return False


def validate_memory_source_references(vault: Path, header: dict[str, object]) -> None:
    """Validate source experiences and an optional same-scope active successor."""
    validate_document_header(header, kind="memory")
    sources = header["source_experiences"]
    assert isinstance(sources, list)
    scope = header["scope"]
    current_project_id = header.get("project_id")
    for source in sources:
        assert isinstance(source, str)
        qualified_project, experience_id = _split_source_reference(source)
        if qualified_project is not None:
            project_id = qualified_project
        elif scope == "project" and isinstance(current_project_id, str):
            project_id = current_project_id
        else:
            raise ValueError(f"Ambiguous source experience: {source}")
        if not _experience_exists(vault, project_id, experience_id):
            raise ValueError(f"Unknown source experience: {project_id}/{experience_id}")
    successor_id = header.get("superseded_by")
    if successor_id is None:
        return
    assert isinstance(successor_id, str)
    if scope == "shared":
        successor_root = vault / "shared" / "memory"
    else:
        assert isinstance(current_project_id, str)
        successor_root = vault / "projects" / current_project_id / "memory"
    successor_path = _safe_child(successor_root, f"{successor_id}.md")
    if not successor_path.is_file():
        raise ValueError(f"Unknown superseded_by memory: {successor_id}")
    successor, _ = _read_exact_document(successor_path, kind="memory")
    if successor.get("scope") != scope or successor.get("project_id") != current_project_id:
        raise ValueError("superseded_by must reference a memory in the same scope")
    if _memory_status(successor) != "active":
        raise ValueError("superseded_by must reference an active memory")


def validate_experience_references(vault: Path, header: dict[str, object]) -> None:
    """Validate related and superseded experience references in the same project."""
    validate_document_header(header, kind="experiences")
    project_id = str(header["project_id"])
    experience_id = str(header["experience_id"])
    related = header["related_experiences"]
    supersedes = header["supersedes"]
    assert isinstance(related, list)
    assert isinstance(supersedes, list)
    overlapping = sorted(set(related).intersection(supersedes))
    if overlapping:
        raise ValueError(
            "related_experiences and supersedes must not overlap: " + ", ".join(overlapping)
        )
    for field, references in (
        ("related_experiences", related),
        ("supersedes", supersedes),
    ):
        for reference in references:
            assert isinstance(reference, str)
            if reference == experience_id:
                raise ValueError(f"{field} must not reference the experience itself")
            if not _experience_exists(vault, project_id, reference):
                raise ValueError(f"Unknown {field} experience: {project_id}/{reference}")


def _validate_confidence(confidence: str | None) -> None:
    if confidence is not None and confidence not in CONFIDENCE_CHOICES:
        raise ValueError(f"Unsupported confidence: {confidence}")


def _document_path(context: ProjectContext, kind: str, filename: str) -> Path:
    path = _safe_child(context.project_store / kind, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _safe_child(root: Path, filename: str) -> Path:
    path = (root / filename).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("document path must remain inside the selected refinery directory")
    if path.suffix != ".md":
        raise ValueError("refinery documents must use the .md extension")
    return path
