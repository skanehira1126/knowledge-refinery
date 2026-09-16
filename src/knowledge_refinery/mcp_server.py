"""Expose validated Knowledge Refinery domain operations through local stdio MCP."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
import sys
from typing import Any
from typing import Literal
from typing import TypeVar

from mcp.server.fastmcp import FastMCP
import yaml

from knowledge_refinery import get_version
from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.config_ops import get_deep_search_runtime_settings
from knowledge_refinery.config_ops import get_deep_search_settings
from knowledge_refinery.deep_search_ops import DeepSearchResult
from knowledge_refinery.deep_search_ops import run_deep_search
from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import SearchFilters
from knowledge_refinery.experience_ops import parse_datetime_filter
from knowledge_refinery.experience_ops import read_experience_at
from knowledge_refinery.experience_ops import read_memory_at
from knowledge_refinery.experience_ops import search_documents_at
from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.experience_ops import validate_document_header
from knowledge_refinery.experience_ops import validate_experience_references
from knowledge_refinery.experience_ops import validate_memory_source_references
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.handoff_ops import HANDOFF_SCHEMA_VERSION
from knowledge_refinery.handoff_ops import archive_handoff_at
from knowledge_refinery.handoff_ops import create_handoff_at
from knowledge_refinery.handoff_ops import delete_handoff_at
from knowledge_refinery.handoff_ops import list_handoffs_at
from knowledge_refinery.handoff_ops import read_handoff_at
from knowledge_refinery.handoff_ops import validate_handoffs_at
from knowledge_refinery.tag_ops import TAG_TAXONOMY
from knowledge_refinery.tag_ops import TAG_TAXONOMY_SCHEMA_VERSION
from knowledge_refinery.tag_ops import TagBrowseResult
from knowledge_refinery.tag_ops import TagSearchResult
from knowledge_refinery.tag_ops import browse_knowledge_tags
from knowledge_refinery.tag_ops import search_knowledge_tags
from knowledge_refinery.tag_ops import update_tag_description
from knowledge_refinery.tag_ops import validate_tag_taxonomy
from knowledge_refinery.vault_ops import PROJECT_METADATA
from knowledge_refinery.vault_ops import PROJECT_METADATA_SCHEMA_VERSION
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import list_project_metadata
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import read_vault_id
from knowledge_refinery.vault_ops import resolve_project_id
from knowledge_refinery.vault_ops import update_project_metadata


mcp = FastMCP(
    "knowledge-refinery",
    instructions=(
        "ローカルの中央refinery vaultから開発経験と再利用可能なmemoryを検索・記録します。"
        "project単位のtoolには現在のrepository pathを渡してください。serverは"
        ".refinery.yamlと中央project metadataを検証し、連携が無効または不正な"
        "repositoryを拒否します。"
        "判断前はcurrent projectとshared memoryを先に検索し、必要な場合だけselected projectsまたは"
        "vault全体へ広げてください。更新では省略fieldを保持し、空listは明示clearです。"
        "handoffは明示された引き継ぎ操作専用です。通常のknowledge検索・記録には含めません。"
        "handoffの一覧・取得はproject_idによるactive vaultの参照で、repository pathは不要です。"
        "一覧でproject_idを省略すると全projectを対象にします。"
    ),
)

ExperienceStatus = Literal["completed", "inconclusive", "abandoned", "superseded"]
Confidence = Literal["low", "medium", "high"]
MemoryScope = Literal["project", "shared"]
EvidenceType = Literal["file", "git", "mlflow", "url", "external"]
StringValue = TypeVar("StringValue", bound=str)


def _list(value: Sequence[StringValue] | None) -> list[StringValue]:
    return list(value or [])


def _validated_project_id(vault: Path, project_path: str) -> str:
    project_id = resolve_project_id(Path(project_path), vault)
    read_project_metadata(vault, project_id)
    return project_id


def _entry(entry: Any, vault: Path) -> dict[str, object]:
    return {
        "project_id": None if entry.scope == "shared" else entry.project_id,
        "id": entry.document_id,
        "title": entry.title,
        "kind": entry.kind,
        "summary": entry.summary,
        "status": entry.status,
        "scope": entry.scope,
        "confidence": entry.confidence,
        "tags": list(entry.tags),
        "recorded_at": entry.recorded_at,
        "updated_at": entry.updated_at,
        "path": str(entry.path.relative_to(vault)),
    }


@mcp.tool()
def refinery_list_projects() -> list[dict[str, object]]:
    """active vaultに登録されたprojectの識別・検索用metadataを一覧取得します。"""
    return [metadata.as_dict() for metadata in list_project_metadata(get_active_vault())]


@mcp.tool()
def refinery_get_project_metadata(project_path: str) -> dict[str, object]:
    """有効なrepositoryに対応する中央project metadataを取得します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return read_project_metadata(vault, project_id).as_dict()


@mcp.tool()
def refinery_update_project_metadata(
    project_path: str,
    expected_updated_at: str,
    name: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    technologies: list[str] | None = None,
) -> dict[str, object]:
    """project metadataを部分更新します。省略fieldは保持し、空listは対象listを消去します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return update_project_metadata(
        vault,
        project_id,
        expected_updated_at=expected_updated_at,
        name=name,
        summary=summary,
        tags=tags,
        technologies=technologies,
    ).as_dict()


@mcp.tool()
def refinery_info() -> dict[str, object]:
    """MCP packageと文書schemaのversionを返し、CLIとのずれを確認できるようにします。"""
    try:
        active_vault_id = read_vault_id(get_active_vault())
    except (OSError, ValueError):
        active_vault_id = None
    return {
        "version": get_version(),
        "schema_version": 2,
        "project_metadata_schema_version": PROJECT_METADATA_SCHEMA_VERSION,
        "tag_taxonomy_schema_version": TAG_TAXONOMY_SCHEMA_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "active_vault_id": active_vault_id,
    }


@mcp.tool()
def refinery_browse_knowledge_tags(
    project_path: str,
    parent_tag: str | None = None,
    all_projects: bool = False,
) -> TagBrowseResult:
    """Knowledge tagを指定階層の直下だけ、説明と利用件数を付けて取得します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return browse_knowledge_tags(
        vault,
        project_id,
        parent_tag=parent_tag,
        all_projects=all_projects,
    )


@mcp.tool()
def refinery_search_knowledge_tags(
    project_path: str,
    terms: list[str],
    all_projects: bool = False,
) -> TagSearchResult:
    """Knowledge tagのpathと説明をAND条件の語句で検索し、利用件数も取得します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return search_knowledge_tags(
        vault,
        project_id,
        terms=terms,
        all_projects=all_projects,
    )


@mcp.tool()
def refinery_update_tag_description(
    project_path: str,
    tag: str,
    description: str,
    expected_updated_at: str | None = None,
) -> dict[str, object]:
    """Knowledge tagの説明をtaxonomyの現在revisionを使って登録・更新します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    context_from_vault(vault, project_id)
    taxonomy = update_tag_description(
        vault,
        tag=tag,
        description=description,
        expected_updated_at=expected_updated_at,
    )
    return {
        "tag": tag,
        "description": taxonomy.descriptions[tag],
        "taxonomy_updated_at": taxonomy.updated_at,
    }


@mcp.tool()
def refinery_search_experiences(
    project_path: str,
    terms: list[str] | None = None,
    project_ids: list[str] | None = None,
    tags: list[str] | None = None,
    statuses: list[ExperienceStatus] | None = None,
    experience_ids: list[str] | None = None,
    related_experiences: list[str] | None = None,
    evidence_types: list[EvidenceType] | None = None,
    confidences: list[Confidence] | None = None,
    recorded_from: str | None = None,
    recorded_to: str | None = None,
    all_projects: bool = False,
) -> list[dict[str, object]]:
    """experienceを新しい順に検索します。project_idsとall_projectsは併用できません。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
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
    """experience IDまたはproject-id/experience-idを指定してexperienceを取得します。"""
    vault = get_active_vault()
    current_project_id = _validated_project_id(vault, project_path)
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
    status: ExperienceStatus,
    body: str,
    evidence: list[dict[str, str]] | None = None,
    tags: list[str] | None = None,
    related_experiences: list[str] | None = None,
    supersedes: list[str] | None = None,
    confidence: Confidence | None = None,
    experience_id: str | None = None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
) -> dict[str, str]:
    """experienceを作成・更新します。更新の省略fieldは保持し、空listはclearします。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    path = upsert_experience_at(
        vault,
        project_id,
        title=title,
        purpose=purpose,
        status=status,
        experience_id=experience_id,
        filename=None,
        tags=tags,
        evidence=evidence,
        related_experiences=related_experiences,
        supersedes=supersedes,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
    )
    header, _ = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
    return {
        "experience_id": str(header["experience_id"]),
        "project_id": str(header["project_id"]),
        "kind": "experience",
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
    scopes: list[MemoryScope] | None = None,
    confidences: list[Confidence] | None = None,
    all_projects: bool = False,
) -> list[dict[str, object]]:
    """project/shared memoryを新しい順に検索します。結果のscopeをexact getへ渡します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
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


async def refinery_deep_search(
    project_path: str,
    question: str,
) -> DeepSearchResult:
    """検証済みvault snapshotをCodexで深く読み、根拠source ID付きで質問へ回答します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    model, reasoning_effort = get_deep_search_runtime_settings()
    return await asyncio.to_thread(
        run_deep_search,
        vault,
        project_id,
        question,
        model,
        reasoning_effort=reasoning_effort,
    )


@mcp.tool()
def refinery_get_memory(
    project_path: str,
    memory_id: str,
    scope: MemoryScope = "project",
    project_id: str | None = None,
) -> dict[str, object]:
    """memory IDとscopeを指定してprojectまたはshared memoryを取得します。"""
    vault = get_active_vault()
    current_project_id = _validated_project_id(vault, project_path)
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
    source_experiences: list[str] | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    confidence: Confidence | None = None,
    shared: bool = False,
    memory_id: str | None = None,
    expected_updated_at: str | None = None,
    clear_confidence: bool = False,
) -> dict[str, object]:
    """memoryを作成・更新します。更新の省略fieldは保持し、空listはclearします。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    path = upsert_memory_at(
        vault,
        project_id,
        title=title,
        summary=summary,
        memory_id=memory_id,
        filename=None,
        tags=tags,
        source_experiences=source_experiences,
        shared=shared,
        confidence=confidence,
        body=body,
        expected_updated_at=expected_updated_at,
        clear_confidence=clear_confidence,
    )
    header, _ = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
    return {
        "memory_id": str(header["memory_id"]),
        "scope": str(header["scope"]),
        "project_id": header.get("project_id"),
        "updated_at": str(header["updated_at"]),
        "path": str(path.relative_to(vault)),
    }


@mcp.tool()
def refinery_create_handoff(
    project_path: str,
    title: str,
    goal: str,
    done_when: str,
    body: str,
    handoff_id: str | None = None,
    task_id: str | None = None,
    supersedes: str | None = None,
    expected_updated_at: str | None = None,
) -> dict[str, object]:
    """引き継ぎを新規保存します。旧版を指定した場合は同じ作業の旧版をアーカイブします。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return create_handoff_at(
        vault,
        project_id,
        title=title,
        goal=goal,
        done_when=done_when,
        body=body,
        handoff_id=handoff_id,
        task_id=task_id,
        supersedes=supersedes,
        expected_updated_at=expected_updated_at,
    ).as_dict(vault)


@mcp.tool()
def refinery_list_handoffs(
    project_id: str | None = None,
    include_archived: bool = False,
    task_id: str | None = None,
    archived_before: str | None = None,
) -> list[dict[str, object]]:
    """引き継ぎmetadataを一覧します。project_id省略時はactive vaultの全projectが対象です。

    既定はactiveのみで本文を含みません。ローカルrepoは不要です。
    """
    vault = get_active_vault()
    return [
        record.as_dict(vault, include_body=False)
        for record in list_handoffs_at(
            vault,
            project_id,
            include_archived=include_archived,
            task_id=task_id,
            archived_before=archived_before,
        )
    ]


@mcp.tool()
def refinery_get_handoff(project_id: str, handoff_id: str) -> dict[str, object]:
    """active vaultからproject_idとhandoff_idで取得します。ローカルrepoは不要です。

    読み込みによる状態変更や削除は行いません。
    """
    vault = get_active_vault()
    return read_handoff_at(vault, project_id, handoff_id).as_dict(vault)


@mcp.tool()
def refinery_archive_handoff(
    project_path: str,
    handoff_id: str,
    expected_updated_at: str,
) -> dict[str, object]:
    """確認済みrevisionの引き継ぎをアーカイブし、内容を保持します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return archive_handoff_at(
        vault,
        project_id,
        handoff_id,
        expected_updated_at=expected_updated_at,
    ).as_dict(vault)


@mcp.tool()
def refinery_delete_handoff(
    project_path: str,
    handoff_id: str,
    expected_updated_at: str,
) -> dict[str, object]:
    """明示された削除対象として確認済みrevisionのarchived引き継ぎ1件を削除します。"""
    vault = get_active_vault()
    project_id = _validated_project_id(vault, project_path)
    return delete_handoff_at(
        vault,
        project_id,
        handoff_id,
        expected_updated_at=expected_updated_at,
    )


@mcp.tool()
def refinery_validate() -> dict[str, object]:
    """active vaultのtaxonomy、project metadata、experience、memory、handoffを検証します。"""
    vault = get_active_vault()
    errors: list[dict[str, str]] = []
    checked = 0
    seen_ids: dict[tuple[str, str, str], Path] = {}
    taxonomy_path = vault / TAG_TAXONOMY
    if taxonomy_path.is_file():
        try:
            validate_tag_taxonomy(yaml.safe_load(taxonomy_path.read_text(encoding="utf-8")))
            checked += 1
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append({"path": str(taxonomy_path.relative_to(vault)), "error": str(error)})
    for project_store in sorted((vault / "projects").iterdir()):
        if not project_store.is_dir():
            continue
        path = project_store / PROJECT_METADATA
        try:
            read_project_metadata(vault, project_store.name)
            checked += 1
            handoff_checked, handoff_errors = validate_handoffs_at(vault, project_store.name)
            checked += handoff_checked
            errors.extend(handoff_errors)
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
            header, _ = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
            validate_document_header(header, kind=kind)
            _validate_document_location(path, vault, header, kind=kind, seen_ids=seen_ids)
            if kind == "experiences":
                validate_experience_references(vault, header)
            else:
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


def register_configured_tools(server: FastMCP = mcp) -> bool:
    """Publish optional tools from validated startup configuration.

    Deep search configuration errors are reported to stderr and leave the rest of the
    MCP server available. The return value indicates whether the optional tool was added.
    """
    try:
        enabled, _, _ = get_deep_search_settings()
    except (OSError, ValueError) as error:
        print(
            f"warning: deep search tool is disabled because its configuration is invalid: {error}",
            file=sys.stderr,
        )
        return False
    if not enabled:
        return False
    server.add_tool(refinery_deep_search, structured_output=True)
    return True


def serve() -> None:
    """Register optional tools once, then run the default MCP server over stdio."""
    register_configured_tools()
    mcp.run(transport="stdio")
