from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from knowledge_refinery import get_version
from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import SearchFilters
from knowledge_refinery.experience_ops import parse_datetime_filter
from knowledge_refinery.experience_ops import read_experience_at
from knowledge_refinery.experience_ops import read_memory_at
from knowledge_refinery.experience_ops import search_documents_at
from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.experience_ops import validate_document_header
from knowledge_refinery.experience_ops import validate_memory_source_references
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.vault_ops import PROJECT_METADATA
from knowledge_refinery.vault_ops import PROJECT_METADATA_SCHEMA_VERSION
from knowledge_refinery.vault_ops import list_project_metadata
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import resolve_project_id
from knowledge_refinery.vault_ops import update_project_metadata


mcp = FastMCP(
    "knowledge-refinery",
    instructions=(
        "Search and record integrated development experiences in a local central refinery vault. "
        "Pass the current repository path to project-scoped tools; the server reads "
        ".refinery.yaml and rejects repositories where integration is disabled."
    ),
)


def _list(value: list[str] | None) -> list[str]:
    return value or []


def _entry(entry: Any, vault: Path) -> dict[str, str]:
    return {
        "project_id": entry.project_id,
        "id": entry.document_id,
        "title": entry.title,
        "path": str(entry.path.relative_to(vault)),
    }


@mcp.tool()
def refinery_list_projects() -> list[dict[str, object]]:
    """List project identity and discovery metadata from the active local vault."""
    return [metadata.as_dict() for metadata in list_project_metadata(get_active_vault())]


@mcp.tool()
def refinery_get_project_metadata(project_path: str) -> dict[str, object]:
    """Read central metadata for an enabled repository."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    return read_project_metadata(vault, project_id).as_dict()


@mcp.tool()
def refinery_update_project_metadata(
    project_path: str,
    name: str,
    summary: str,
    tags: list[str],
    technologies: list[str],
    expected_updated_at: str,
) -> dict[str, object]:
    """Update project metadata using the revision returned by a prior read or list."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    return update_project_metadata(
        vault,
        project_id,
        name=name,
        summary=summary,
        tags=tags,
        technologies=technologies,
        expected_updated_at=expected_updated_at,
    ).as_dict()


@mcp.tool()
def refinery_info() -> dict[str, object]:
    """Return the MCP package and document schema versions for drift checks."""
    return {
        "version": get_version(),
        "schema_version": 2,
        "project_metadata_schema_version": PROJECT_METADATA_SCHEMA_VERSION,
    }


@mcp.tool()
def refinery_search_experiences(
    project_path: str,
    terms: list[str] | None = None,
    project_ids: list[str] | None = None,
    tags: list[str] | None = None,
    statuses: list[str] | None = None,
    experience_ids: list[str] | None = None,
    related_experiences: list[str] | None = None,
    evidence_types: list[str] | None = None,
    confidences: list[str] | None = None,
    recorded_from: str | None = None,
    recorded_to: str | None = None,
    all_projects: bool = False,
) -> list[dict[str, str]]:
    """Search experiences for an enabled repository, optionally across the local vault."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    filters = SearchFilters(
        document_ids=tuple(_list(experience_ids)),
        related_experiences=tuple(_list(related_experiences)),
        evidence_types=tuple(_list(evidence_types)),
        confidences=tuple(_list(confidences)),
        recorded_from=(
            parse_datetime_filter(recorded_from, end_of_day=False) if recorded_from else None
        ),
        recorded_to=(parse_datetime_filter(recorded_to, end_of_day=True) if recorded_to else None),
    )
    entries = search_documents_at(
        vault,
        project_id,
        kind="experiences",
        terms=_list(terms),
        project_ids=_list(project_ids),
        tags=_list(tags),
        statuses=_list(statuses),
        all_projects=all_projects,
        filters=filters,
    )
    return [_entry(entry, vault) for entry in entries]


@mcp.tool()
def refinery_get_experience(project_path: str, source: str) -> dict[str, object]:
    """Read an exact local or project-id/experience-id source from an enabled repository."""
    vault = get_active_vault()
    current_project_id = resolve_project_id(Path(project_path))
    source_project_id, separator, experience_id = source.partition("/")
    if not separator:
        source_project_id = current_project_id
        experience_id = source
    elif not source_project_id or not experience_id or "/" in experience_id:
        raise ValueError("source must use experience-id or project-id/experience-id")
    path, header, body = read_experience_at(vault, source_project_id, experience_id)
    return {"header": header, "body": body, "path": str(path.relative_to(vault))}


@mcp.tool()
def refinery_record_experience(
    project_path: str,
    title: str,
    purpose: str,
    status: str,
    body: str,
    evidence: list[dict[str, str]] | None = None,
    tags: list[str] | None = None,
    related_experiences: list[str] | None = None,
    supersedes: list[str] | None = None,
    confidence: str | None = None,
    experience_id: str | None = None,
    expected_updated_at: str | None = None,
) -> dict[str, str]:
    """Create an experience, or update it with the revision returned by a prior read."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    path = upsert_experience_at(
        vault,
        project_id,
        title=title,
        purpose=purpose,
        status=status,
        experience_id=experience_id,
        filename=None,
        tags=_list(tags),
        evidence=evidence or [],
        related_experiences=_list(related_experiences),
        supersedes=_list(supersedes),
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
    )
    header, _ = split_front_matter(path.read_text(encoding="utf-8"))
    return {
        "experience_id": str(header["experience_id"]),
        "updated_at": str(header["updated_at"]),
        "path": str(path.relative_to(vault)),
    }


@mcp.tool()
def refinery_search_memory(
    project_path: str,
    terms: list[str] | None = None,
    project_ids: list[str] | None = None,
    tags: list[str] | None = None,
    memory_ids: list[str] | None = None,
    source_experiences: list[str] | None = None,
    scopes: list[str] | None = None,
    confidences: list[str] | None = None,
    all_projects: bool = False,
) -> list[dict[str, str]]:
    """Search memory from an enabled repository by typed fields and full text."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    entries = search_documents_at(
        vault,
        project_id,
        kind="memory",
        terms=_list(terms),
        project_ids=_list(project_ids),
        tags=_list(tags),
        statuses=[],
        all_projects=all_projects,
        filters=SearchFilters(
            document_ids=tuple(_list(memory_ids)),
            source_experiences=tuple(_list(source_experiences)),
            scopes=tuple(_list(scopes)),
            confidences=tuple(_list(confidences)),
        ),
    )
    return [_entry(entry, vault) for entry in entries]


@mcp.tool()
def refinery_get_memory(
    project_path: str,
    memory_id: str,
    scope: str = "project",
    project_id: str | None = None,
) -> dict[str, object]:
    """Read exact project or shared memory from an enabled repository."""
    vault = get_active_vault()
    current_project_id = resolve_project_id(Path(project_path))
    path, header, body = read_memory_at(
        vault,
        current_project_id,
        memory_id,
        scope=scope,
        project_id=project_id,
    )
    return {"header": header, "body": body, "path": str(path.relative_to(vault))}


@mcp.tool()
def refinery_record_memory(
    project_path: str,
    title: str,
    summary: str,
    source_experiences: list[str],
    body: str | None = None,
    tags: list[str] | None = None,
    confidence: str | None = None,
    shared: bool = False,
    memory_id: str | None = None,
    expected_updated_at: str | None = None,
) -> dict[str, str]:
    """Create memory, or update it with the revision returned by refinery_get_memory."""
    vault = get_active_vault()
    project_id = resolve_project_id(Path(project_path))
    path = upsert_memory_at(
        vault,
        project_id,
        title=title,
        summary=summary,
        memory_id=memory_id,
        filename=None,
        tags=_list(tags),
        source_experiences=source_experiences,
        shared=shared,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
    )
    header, _ = split_front_matter(path.read_text(encoding="utf-8"))
    return {
        "memory_id": str(header["memory_id"]),
        "updated_at": str(header["updated_at"]),
        "path": str(path.relative_to(vault)),
    }


@mcp.tool()
def refinery_validate() -> dict[str, object]:
    """Validate project metadata, experience, and memory documents in the active vault."""
    vault = get_active_vault()
    errors: list[dict[str, str]] = []
    checked = 0
    seen_ids: dict[tuple[str, str, str], Path] = {}
    for project_store in sorted((vault / "projects").iterdir()):
        if not project_store.is_dir():
            continue
        path = project_store / PROJECT_METADATA
        try:
            read_project_metadata(vault, project_store.name)
            checked += 1
        except (OSError, ValueError, RefineryCliError) as error:
            errors.append({"path": str(path.relative_to(vault)), "error": str(error)})
    for path in sorted(vault.rglob("*.md")):
        relative = path.relative_to(vault)
        parts = relative.parts
        is_experience = len(parts) >= 4 and parts[0] == "projects" and parts[2] == "experiences"
        is_project_memory = len(parts) >= 4 and parts[0] == "projects" and parts[2] == "memory"
        is_shared_memory = len(parts) >= 3 and parts[:2] == ("shared", "memory")
        if path.name == "AGENTS.md" or not (
            is_experience or is_project_memory or is_shared_memory
        ):
            continue
        kind = "experiences" if is_experience else "memory"
        try:
            header, _ = split_front_matter(path.read_text(encoding="utf-8"))
            validate_document_header(header, kind=kind)
            _validate_document_location(path, vault, header, kind=kind, seen_ids=seen_ids)
            if kind == "memory":
                validate_memory_source_references(vault, header)
            checked += 1
        except (OSError, ValueError, RefineryCliError) as error:
            errors.append({"path": str(path.relative_to(vault)), "error": str(error)})
    return {"valid": not errors, "checked": checked, "errors": errors}


def _validate_document_location(
    path: Path,
    vault: Path,
    header: dict[str, object],
    *,
    kind: str,
    seen_ids: dict[tuple[str, str, str], Path],
) -> None:
    relative = path.relative_to(vault)
    if kind == "experiences":
        expected_project = relative.parts[1]
        if header.get("project_id") != expected_project:
            raise ValueError(f"experience project_id must match path project: {expected_project}")
        namespace = expected_project
        document_id = str(header["experience_id"])
    else:
        scope = str(header["scope"])
        if relative.parts[:2] == ("shared", "memory"):
            if scope != "shared":
                raise ValueError("memory under shared/memory must use scope: shared")
            namespace = "shared"
        else:
            expected_project = relative.parts[1]
            if scope != "project" or header.get("project_id") != expected_project:
                raise ValueError("project memory scope and project_id must match its path")
            namespace = expected_project
        document_id = str(header["memory_id"])

    key = (kind, namespace, document_id)
    if path.name != f"{document_id}.md":
        raise ValueError(f"{kind} filename must match document ID: {document_id}.md")
    previous = seen_ids.get(key)
    if previous is not None:
        raise ValueError(
            f"duplicate {kind} ID {document_id}: {previous.relative_to(vault)} and {relative}"
        )
    seen_ids[key] = path


def serve() -> None:
    mcp.run(transport="stdio")
