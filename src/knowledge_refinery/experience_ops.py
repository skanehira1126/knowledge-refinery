from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
import re
import secrets

import yaml

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import ProjectContext
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import resolve_project_context


EXPERIENCE_STATUS_CHOICES = ("completed", "inconclusive", "abandoned", "superseded")
CONFIDENCE_CHOICES = ("low", "medium", "high")
MEMORY_SCOPE_CHOICES = ("project", "shared")
EVIDENCE_TYPE_CHOICES = ("file", "git", "mlflow", "url", "external")
EVIDENCE_RETENTION_CHOICES = ("reference", "snapshot", "external", "source")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class SearchEntry:
    path: Path
    project_id: str
    document_id: str
    title: str


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
    return """## 試したこと\n\n- \n\n## 分かったこと\n\n- \n\n## 次の可能性\n\n- \n"""


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
    tags: list[str],
    evidence: list[str],
    related_experiences: list[str],
    supersedes: list[str],
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
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
    tags: list[str],
    evidence: list[dict[str, str]],
    related_experiences: list[str],
    supersedes: list[str],
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
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
    )


def _upsert_experience(
    context: ProjectContext,
    *,
    title: str,
    purpose: str,
    status: str,
    experience_id: str | None,
    filename: str | None,
    tags: list[str],
    evidence: Sequence[str | dict[str, str]],
    related_experiences: list[str],
    supersedes: list[str],
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None,
) -> Path:
    if status not in EXPERIENCE_STATUS_CHOICES:
        raise ValueError(f"Unsupported experience status: {status}")
    document_id = experience_id or _new_id(title)
    if not SLUG_RE.fullmatch(document_id):
        raise ValueError("experience_id must be a lowercase slug")
    expected_filename = f"{document_id}.md"
    if filename is not None and filename != expected_filename:
        raise ValueError("experience filename must match experience_id")
    _validate_slugs(related_experiences, field="related_experiences")
    _validate_slugs(supersedes, field="supersedes")
    _validate_confidence(confidence)
    structured_evidence = normalize_evidence(evidence)
    path = _document_path(context, "experiences", expected_filename)
    with interprocess_lock(path):
        created_at = datetime.now(UTC).isoformat()
        if path.exists():
            current, current_body = split_front_matter(path.read_text(encoding="utf-8"))
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
            raise ValueError("experience does not exist; omit expected_updated_at to create it")
        header: dict[str, object] = {
            "schema_version": 2,
            "experience_id": document_id,
            "project_id": context.project_id,
            "title": title,
            "purpose": purpose,
            "status": status,
            "recorded_at": created_at,
            "updated_at": datetime.now(UTC).isoformat(),
            "tags": tags,
            "evidence": structured_evidence,
            "related_experiences": related_experiences,
            "supersedes": supersedes,
            "confidence": confidence,
        }
        validate_document_header(header, kind="experiences")
        atomic_write_text(path, _render(header, body or _default_experience_body()))
    return path


def upsert_memory(
    project: Path,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str],
    source_experiences: list[str],
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
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
    )


def upsert_memory_at(
    vault: Path,
    project_id: str,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str],
    source_experiences: list[str],
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None = None,
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
    )


def _upsert_memory(
    context: ProjectContext,
    *,
    title: str,
    summary: str,
    memory_id: str | None,
    filename: str | None,
    tags: list[str],
    source_experiences: list[str],
    shared: bool,
    confidence: str | None,
    body: str | None,
    expected_updated_at: str | None,
) -> Path:
    document_id = memory_id or _slug(title)
    if not SLUG_RE.fullmatch(document_id):
        raise ValueError("memory_id must be a lowercase slug")
    expected_filename = f"{document_id}.md"
    if filename is not None and filename != expected_filename:
        raise ValueError("memory filename must match memory_id")
    if not source_experiences:
        raise ValueError("memory requires at least one --source-experience")
    _validate_memory_sources(context, source_experiences, shared=shared)
    _validate_confidence(confidence)
    root = context.vault_root / "shared" / "memory" if shared else context.project_store / "memory"
    path = _safe_child(root, expected_filename)
    with interprocess_lock(path):
        if path.exists():
            current, current_body = split_front_matter(path.read_text(encoding="utf-8"))
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
        header: dict[str, object] = {
            "schema_version": 2,
            "memory_id": document_id,
            "scope": "shared" if shared else "project",
            "project_id": None if shared else context.project_id,
            "title": title,
            "summary": summary,
            "source_experiences": source_experiences,
            "updated_at": datetime.now(UTC).isoformat(),
            "tags": tags,
            "confidence": confidence,
        }
        validate_document_header(header, kind="memory")
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
    selected = project_ids or ([context.project_id] if not all_projects else [])
    roots = _search_roots(context, kind, selected, all_projects=all_projects)

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
                header, _ = split_front_matter(text)
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
                statuses=statuses,
                filters=active_filters,
                kind=kind,
            ):
                continue
            id_key = "experience_id" if kind == "experiences" else "memory_id"
            entries.append(
                SearchEntry(
                    path=path,
                    project_id=project_id,
                    document_id=str(header.get(id_key, path.stem)),
                    title=str(header.get("title", path.stem)),
                )
            )
    return entries


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


def _read_exact_document(path: Path, *, kind: str) -> tuple[dict[str, object], str]:
    header, body = split_front_matter(path.read_text(encoding="utf-8"))
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
    if not isinstance(current_tags, list) or any(tag not in current_tags for tag in tags):
        return False
    if statuses and header.get("status") not in statuses:
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
        ("experience_id", "project_id", "title", "purpose", "status", "recorded_at")
        if kind == "experiences"
        else ("memory_id", "scope", "title", "summary")
    )
    for field in required:
        if not isinstance(header.get(field), str) or not str(header[field]).strip():
            raise ValueError(f"{kind} header requires non-empty string field: {field}")
    _validate_string_list(header, "tags")
    if kind == "experiences":
        status = header["status"]
        if status not in EXPERIENCE_STATUS_CHOICES:
            raise ValueError(f"Unsupported experience status: {status}")
        _validate_string_list(header, "related_experiences")
        _validate_string_list(header, "supersedes")
        _validate_evidence(header.get("evidence"))
        parse_datetime_filter(str(header["recorded_at"]), end_of_day=False)
    else:
        _validate_memory_header(header)
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


def _validate_memory_header(header: dict[str, object]) -> None:
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


def _validate_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("evidence must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be a mapping")
        evidence_type = item.get("type")
        retention = item.get("retention")
        if evidence_type not in EVIDENCE_TYPE_CHOICES:
            raise ValueError(f"Unsupported evidence type: {evidence_type}")
        if retention not in EVIDENCE_RETENTION_CHOICES:
            raise ValueError(f"Unsupported evidence retention: {retention}")
        location_key = "path" if evidence_type in {"file", "git"} else "uri"
        if not isinstance(item.get(location_key), str) or not item[location_key]:
            raise ValueError(f"evidence type {evidence_type} requires {location_key}")
        if evidence_type == "git" and (
            not isinstance(item.get("commit"), str) or not item["commit"]
        ):
            raise ValueError("evidence type git requires commit")


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
            header, _ = split_front_matter(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if header.get("project_id") == project_id and header.get("experience_id") == experience_id:
            return True
    return False


def validate_memory_source_references(vault: Path, header: dict[str, object]) -> None:
    """Validate that every syntactically valid memory source still exists."""
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
