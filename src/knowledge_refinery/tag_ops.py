from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import yaml

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import MAX_TAG_DEPTH
from knowledge_refinery.experience_ops import SLUG_RE
from knowledge_refinery.experience_ops import validate_document_header
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import context_from_vault


TAG_TAXONOMY = "knowledge-tags.yaml"
TAG_TAXONOMY_SCHEMA_VERSION = 1
DEFAULT_TAG_DESCRIPTIONS = {
    "domain": "対象となる業務・知識領域",
    "artifact": "作成・変更した成果物の種類",
    "task": "実施した作業の種類",
    "tech": "ナレッジ内で扱う技術",
    "issue": "発生した問題や障害の分類",
}


class TagResult(TypedDict):
    tag: str
    segment: str
    description: str | None
    defined: bool
    direct_count: int
    document_count: int
    experience_count: int
    project_memory_count: int
    shared_memory_count: int
    has_children: bool


class TagBrowseResult(TypedDict):
    parent_tag: str | None
    all_projects: bool
    includes_shared_memory: bool
    taxonomy_updated_at: str | None
    tags: list[TagResult]


class TagSearchResult(TypedDict):
    terms: list[str]
    all_projects: bool
    includes_shared_memory: bool
    taxonomy_updated_at: str | None
    tags: list[TagResult]


@dataclass(frozen=True)
class TagTaxonomy:
    updated_at: str | None
    descriptions: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": TAG_TAXONOMY_SCHEMA_VERSION,
            "updated_at": self.updated_at,
            "tags": {
                tag: {"description": description}
                for tag, description in sorted(self.descriptions.items())
            },
        }


def validate_tag_path(tag: str, *, field: str = "tag") -> None:
    segments = tag.split("/")
    if len(segments) > MAX_TAG_DEPTH or any(
        not SLUG_RE.fullmatch(segment) for segment in segments
    ):
        raise ValueError(f"{field} must use one to three lowercase slug segments separated by /")


def read_tag_taxonomy(vault: Path) -> TagTaxonomy:
    path = vault / TAG_TAXONOMY
    if not path.is_file():
        return TagTaxonomy(updated_at=None, descriptions=dict(DEFAULT_TAG_DESCRIPTIONS))
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_tag_taxonomy(raw)
    assert isinstance(raw, dict)
    tags = raw["tags"]
    assert isinstance(tags, dict)
    descriptions = dict(DEFAULT_TAG_DESCRIPTIONS)
    descriptions.update(
        {
            str(tag): str(definition["description"])
            for tag, definition in tags.items()
            if isinstance(definition, dict)
        }
    )
    return TagTaxonomy(updated_at=str(raw["updated_at"]), descriptions=descriptions)


def update_tag_description(
    vault: Path,
    *,
    tag: str,
    description: str,
    expected_updated_at: str | None,
) -> TagTaxonomy:
    validate_tag_path(tag)
    if not description.strip():
        raise ValueError("tag description must not be empty")
    path = vault / TAG_TAXONOMY
    with interprocess_lock(path):
        current = read_tag_taxonomy(vault)
        if current.updated_at is None:
            if expected_updated_at is not None:
                raise ValueError(
                    "tag taxonomy does not exist; omit expected_updated_at to create it"
                )
        elif expected_updated_at is None:
            raise ValueError(
                "tag taxonomy already exists; browse or search tags and pass expected_updated_at"
            )
        elif expected_updated_at != current.updated_at:
            raise ValueError("tag taxonomy update conflict: expected_updated_at is stale")
        descriptions = dict(current.descriptions)
        descriptions[tag] = description.strip()
        updated = TagTaxonomy(
            updated_at=datetime.now(UTC).isoformat(),
            descriptions=descriptions,
        )
        atomic_write_text(
            path,
            yaml.safe_dump(updated.as_dict(), sort_keys=False, allow_unicode=True),
        )
    return updated


def validate_tag_taxonomy(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ValueError("tag taxonomy must be a mapping")
    if raw.get("schema_version") != TAG_TAXONOMY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported tag taxonomy schema: {raw.get('schema_version')}")
    _validate_updated_at(raw.get("updated_at"))
    tags = raw.get("tags")
    if not isinstance(tags, dict):
        raise ValueError("tag taxonomy tags must be a mapping")
    for tag, definition in tags.items():
        _validate_tag_definition(tag, definition)


def _validate_updated_at(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("tag taxonomy updated_at must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("tag taxonomy updated_at must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("tag taxonomy updated_at must include a timezone")


def _validate_tag_definition(tag: object, definition: object) -> None:
    if not isinstance(tag, str):
        raise ValueError("tag taxonomy keys must be strings")
    validate_tag_path(tag, field="tag taxonomy key")
    if not isinstance(definition, dict):
        raise ValueError(f"tag taxonomy definition must be a mapping: {tag}")
    description = definition.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"tag taxonomy description must not be empty: {tag}")


def browse_knowledge_tags(
    vault: Path,
    project_id: str,
    *,
    parent_tag: str | None = None,
    all_projects: bool = False,
) -> TagBrowseResult:
    if parent_tag is not None:
        validate_tag_path(parent_tag, field="parent_tag")
    context_from_vault(vault, project_id)
    taxonomy = read_tag_taxonomy(vault)
    usage = _collect_tag_usage(vault, project_id, all_projects=all_projects)
    known_tags = _known_tags(taxonomy.descriptions, usage)
    children = sorted(tag for tag in known_tags if _parent_tag(tag) == parent_tag)
    return {
        "parent_tag": parent_tag,
        "all_projects": all_projects,
        "includes_shared_memory": True,
        "taxonomy_updated_at": taxonomy.updated_at,
        "tags": [_tag_result(tag, known_tags, taxonomy.descriptions, usage) for tag in children],
    }


def search_knowledge_tags(
    vault: Path,
    project_id: str,
    *,
    terms: list[str],
    all_projects: bool = False,
) -> TagSearchResult:
    if not terms or any(not term.strip() for term in terms):
        raise ValueError("tag search requires one or more non-empty terms")
    context_from_vault(vault, project_id)
    taxonomy = read_tag_taxonomy(vault)
    usage = _collect_tag_usage(vault, project_id, all_projects=all_projects)
    known_tags = _known_tags(taxonomy.descriptions, usage)
    lowered_terms = [term.casefold() for term in terms]
    matches = []
    for tag in sorted(known_tags):
        description = taxonomy.descriptions.get(tag, "")
        haystack = f"{tag}\n{description}".casefold()
        if all(term in haystack for term in lowered_terms):
            matches.append(_tag_result(tag, known_tags, taxonomy.descriptions, usage))
    return {
        "terms": terms,
        "all_projects": all_projects,
        "includes_shared_memory": True,
        "taxonomy_updated_at": taxonomy.updated_at,
        "tags": matches,
    }


def _collect_tag_usage(
    vault: Path, project_id: str, *, all_projects: bool
) -> dict[str, dict[str, set[str]]]:
    usage: dict[str, dict[str, set[str]]] = {}
    projects_root = vault / "projects"
    project_dirs = (
        sorted(path for path in projects_root.iterdir() if path.is_dir())
        if all_projects
        else [projects_root / project_id]
    )
    roots: list[tuple[str, Path, str]] = []
    for project_dir in project_dirs:
        roots.extend(
            [
                ("experiences", project_dir / "experiences", "experiences"),
                ("project_memory", project_dir / "memory", "memory"),
            ]
        )
    roots.append(("shared_memory", vault / "shared" / "memory", "memory"))
    for category, root, kind in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == "AGENTS.md":
                continue
            try:
                header, _ = split_front_matter(path.read_text(encoding="utf-8"), source_path=path)
                validate_document_header(header, kind=kind)
            except (OSError, ValueError, RefineryCliError):
                continue
            document_key = str(path.relative_to(vault))
            tags = header.get("tags", [])
            assert isinstance(tags, list)
            for tag in tags:
                assert isinstance(tag, str)
                usage.setdefault(tag, {}).setdefault(category, set()).add(document_key)
    return usage


def _known_tags(descriptions: dict[str, str], usage: dict[str, dict[str, set[str]]]) -> set[str]:
    known: set[str] = set()
    for tag in descriptions.keys() | usage.keys():
        segments = tag.split("/")
        known.update("/".join(segments[:index]) for index in range(1, len(segments) + 1))
    return known


def _parent_tag(tag: str) -> str | None:
    parent, separator, _ = tag.rpartition("/")
    return parent if separator else None


def _tag_result(
    tag: str,
    known_tags: set[str],
    descriptions: dict[str, str],
    usage: dict[str, dict[str, set[str]]],
) -> TagResult:
    direct = _documents_for_tag(tag, usage, include_descendants=False)
    total = _documents_for_tag(tag, usage, include_descendants=True)
    return {
        "tag": tag,
        "segment": tag.rsplit("/", 1)[-1],
        "description": descriptions.get(tag),
        "defined": tag in descriptions,
        "direct_count": len(set().union(*direct.values())) if direct else 0,
        "document_count": len(set().union(*total.values())) if total else 0,
        "experience_count": len(total.get("experiences", set())),
        "project_memory_count": len(total.get("project_memory", set())),
        "shared_memory_count": len(total.get("shared_memory", set())),
        "has_children": any(_parent_tag(candidate) == tag for candidate in known_tags),
    }


def _documents_for_tag(
    requested: str,
    usage: dict[str, dict[str, set[str]]],
    *,
    include_descendants: bool,
) -> dict[str, set[str]]:
    documents: dict[str, set[str]] = {}
    for current, categories in usage.items():
        if current != requested and not (
            include_descendants and current.startswith(f"{requested}/")
        ):
            continue
        for category, paths in categories.items():
            documents.setdefault(category, set()).update(paths)
    return documents
