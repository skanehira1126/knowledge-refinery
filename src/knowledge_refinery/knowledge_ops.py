from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil

from knowledge_refinery.front_matter import render_front_matter
from knowledge_refinery.front_matter import split_front_matter


GUIDE_FILENAMES = {"AGENTS.md", "README.md"}
REQUIRED_FIELDS = ("title", "description", "summary")
KNOWLEDGE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class CopyResult:
    source: Path
    target: Path
    copied: bool


@dataclass
class KnowledgeDocument:
    path: Path
    header: dict[str, object]
    body: str


@dataclass
class ReviewEntry:
    path: Path
    knowledge_id: str
    title: str
    description: str
    source_sessions: list[str]
    derived_from: list[str]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "knowledge"


def ensure_string(value: object, *, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: `{field}` must be a non-empty string")
    return value.strip()


def ensure_string_list(value: object, *, field: str, path: Path) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [stripped]
    if not isinstance(value, list):
        raise ValueError(f"{path}: `{field}` must be a string or list of strings")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: `{field}` must contain only non-empty strings")
        items.append(item.strip())
    return items


def ensure_knowledge_id(value: object, *, path: Path) -> str:
    text = ensure_string(value, field="knowledge_id", path=path)
    if not KNOWLEDGE_ID_PATTERN.fullmatch(text):
        raise ValueError(f"{path}: `knowledge_id` must match `{KNOWLEDGE_ID_PATTERN.pattern}`")
    return text


def unique_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def parse_knowledge_document(path: Path) -> KnowledgeDocument:
    header, body = split_front_matter(path.read_text(encoding="utf-8"))
    return KnowledgeDocument(path=path, header=dict(header), body=body)


def render_knowledge_document(header: dict[str, object], body: str) -> str:
    front_matter = render_front_matter(header)
    stripped_body = body.rstrip()
    if stripped_body:
        return f"{front_matter}\n{stripped_body}\n"
    return f"{front_matter}\n"


def extract_session_id(root: Path, path: Path) -> str:
    relative_parts = path.resolve().relative_to(root.resolve()).parts
    if len(relative_parts) < 4 or relative_parts[0] != "sessions":
        raise ValueError(
            f"{path}: expected a session knowledge file under "
            "`.refinery/sessions/<session_id>/...`"
        )
    return relative_parts[1]


def relative_to_repository(root: Path, path: Path) -> str:
    repository_root = root.resolve().parent
    return path.resolve().relative_to(repository_root).as_posix()


def normalize_knowledge_header(
    doc: KnowledgeDocument,
    *,
    fallback_session_id: str | None = None,
    derived_from: list[str] | None = None,
) -> dict[str, object]:
    header = dict(doc.header)

    for field in REQUIRED_FIELDS:
        header[field] = ensure_string(header.get(field), field=field, path=doc.path)

    knowledge_id_value = header.get("knowledge_id")
    if knowledge_id_value is None:
        header["knowledge_id"] = slugify(doc.path.stem)
    else:
        header["knowledge_id"] = ensure_knowledge_id(knowledge_id_value, path=doc.path)

    source_sessions = ensure_string_list(
        header.get("source_sessions"), field="source_sessions", path=doc.path
    )
    if fallback_session_id is not None:
        source_sessions = unique_strings([fallback_session_id, *source_sessions])
    header["source_sessions"] = source_sessions

    tags = ensure_string_list(header.get("tags"), field="tags", path=doc.path)
    if tags:
        header["tags"] = tags
    else:
        header.pop("tags", None)

    confidence = header.get("confidence")
    if confidence is not None:
        header["confidence"] = ensure_string(confidence, field="confidence", path=doc.path)

    lineage = ensure_string_list(header.get("derived_from"), field="derived_from", path=doc.path)
    if derived_from:
        lineage = unique_strings([*lineage, *derived_from])
    if lineage:
        header["derived_from"] = lineage
    else:
        header.pop("derived_from", None)

    # Keep only repository-relative strings in lineage fields.
    header["source_sessions"] = unique_strings(source_sessions)
    return header


def iter_flow_files(root: Path, session_id: str | None = None) -> list[Path]:
    root = root.resolve()
    sessions_root = root / "sessions"
    if session_id is not None:
        candidates = sorted((sessions_root / session_id / "flow").rglob("*.md"))
    else:
        candidates = sorted(sessions_root.glob("*/flow/*.md"))
    return [path for path in candidates if path.name not in GUIDE_FILENAMES]


def iter_review_files(root: Path) -> list[Path]:
    root = root.resolve()
    review_root = root / "shared" / "review"
    return [
        path
        for path in sorted(review_root.rglob("*.md"))
        if path.name not in GUIDE_FILENAMES and "rejected" not in path.parts
    ]


def iter_rejected_review_files(root: Path) -> list[Path]:
    root = root.resolve()
    rejected_root = root / "shared" / "review" / "rejected"
    return [
        path for path in sorted(rejected_root.rglob("*.md")) if path.name not in GUIDE_FILENAMES
    ]


def prepare_review(
    root: Path, session_id: str | None = None, force: bool = False
) -> list[CopyResult]:
    root = root.resolve()
    review_root = root / "shared" / "review"
    review_root.mkdir(parents=True, exist_ok=True)

    results: list[CopyResult] = []
    for flow_path in iter_flow_files(root, session_id=session_id):
        doc = parse_knowledge_document(flow_path)
        current_session_id = extract_session_id(root, flow_path)
        derived_from = [relative_to_repository(root, flow_path)]
        header = normalize_knowledge_header(
            doc,
            fallback_session_id=current_session_id,
            derived_from=derived_from,
        )

        knowledge_id = ensure_knowledge_id(header["knowledge_id"], path=flow_path)
        target = review_root / f"{current_session_id}--{knowledge_id}.md"
        if target.exists() and not force:
            results.append(CopyResult(source=flow_path, target=target, copied=False))
            continue

        target.write_text(render_knowledge_document(header, doc.body), encoding="utf-8")
        results.append(CopyResult(source=flow_path, target=target, copied=True))

    return results


def list_review(
    root: Path, include_rejected: bool = False, session_id: str | None = None
) -> list[ReviewEntry]:
    root = root.resolve()
    candidates = iter_review_files(root)
    if include_rejected:
        candidates.extend(iter_rejected_review_files(root))

    entries: list[ReviewEntry] = []
    for review_path in sorted(candidates):
        doc = parse_knowledge_document(review_path)
        header = normalize_knowledge_header(doc)
        entries.append(
            ReviewEntry(
                path=review_path,
                knowledge_id=ensure_knowledge_id(header["knowledge_id"], path=review_path),
                title=ensure_string(header["title"], field="title", path=review_path),
                description=ensure_string(
                    header["description"], field="description", path=review_path
                ),
                source_sessions=ensure_string_list(
                    header.get("source_sessions"), field="source_sessions", path=review_path
                ),
                derived_from=ensure_string_list(
                    header.get("derived_from"), field="derived_from", path=review_path
                ),
            )
        )

    if session_id is None:
        return entries
    return [entry for entry in entries if session_id in entry.source_sessions]


def select_review_files(
    root: Path, *, knowledge_ids: list[str], review_files: list[str], all_files: bool
) -> list[Path]:
    root = root.resolve()
    selected: list[Path] = []

    if all_files:
        selected.extend(iter_review_files(root))

    for review_file in review_files:
        path = Path(review_file)
        selected.append(path if path.is_absolute() else (root.parent / path))

    if knowledge_ids:
        review_paths = iter_review_files(root)
        by_knowledge_id: dict[str, list[Path]] = {}
        for review_path in review_paths:
            doc = parse_knowledge_document(review_path)
            knowledge_id = ensure_string(
                doc.header.get("knowledge_id"), field="knowledge_id", path=review_path
            )
            by_knowledge_id.setdefault(knowledge_id, []).append(review_path)

        for knowledge_id in knowledge_ids:
            matches = by_knowledge_id.get(knowledge_id, [])
            if not matches:
                raise ValueError(f"No review file found for knowledge_id={knowledge_id}")
            if len(matches) > 1:
                raise ValueError(
                    "Multiple review files found for "
                    f"knowledge_id={knowledge_id}; use --review-file "
                    "to select one explicitly"
                )
            selected.append(matches[0])

    unique_paths: list[Path] = []
    for path in selected:
        resolved = path.resolve()
        if resolved not in unique_paths:
            unique_paths.append(resolved)
    return unique_paths


def promote_review(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
    force: bool = False,
) -> list[CopyResult]:
    root = root.resolve()
    stock_root = root / "shared" / "stock"
    stock_root.mkdir(parents=True, exist_ok=True)

    selected = select_review_files(
        root, knowledge_ids=knowledge_ids, review_files=review_files, all_files=all_files
    )
    if not selected:
        raise ValueError("No review files selected. Use --all, --knowledge-id, or --review-file.")

    results: list[CopyResult] = []
    for review_path in selected:
        doc = parse_knowledge_document(review_path)
        header = normalize_knowledge_header(
            doc,
            derived_from=[relative_to_repository(root, review_path)],
        )
        knowledge_id = ensure_knowledge_id(header["knowledge_id"], path=review_path)
        target = stock_root / f"{knowledge_id}.md"

        if target.exists() and not force:
            results.append(CopyResult(source=review_path, target=target, copied=False))
            continue

        if target.exists():
            existing_doc = parse_knowledge_document(target)
            existing_header = normalize_knowledge_header(existing_doc)
            header["source_sessions"] = unique_strings(
                ensure_string_list(
                    existing_header.get("source_sessions"), field="source_sessions", path=target
                )
                + ensure_string_list(
                    header.get("source_sessions"), field="source_sessions", path=review_path
                )
            )
            header["derived_from"] = unique_strings(
                ensure_string_list(
                    existing_header.get("derived_from"), field="derived_from", path=target
                )
                + ensure_string_list(
                    header.get("derived_from"), field="derived_from", path=review_path
                )
            )

        target.write_text(render_knowledge_document(header, doc.body), encoding="utf-8")
        results.append(CopyResult(source=review_path, target=target, copied=True))

    return results


def reject_review(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
    force: bool = False,
) -> list[CopyResult]:
    root = root.resolve()
    rejected_root = root / "shared" / "review" / "rejected"
    rejected_root.mkdir(parents=True, exist_ok=True)

    selected = select_review_files(
        root, knowledge_ids=knowledge_ids, review_files=review_files, all_files=all_files
    )
    if not selected:
        raise ValueError("No review files selected. Use --all, --knowledge-id, or --review-file.")

    results: list[CopyResult] = []
    for review_path in selected:
        target = rejected_root / review_path.name
        if target.exists() and not force:
            results.append(CopyResult(source=review_path, target=target, copied=False))
            continue

        if target.exists():
            target.unlink()
        shutil.move(str(review_path), str(target))
        results.append(CopyResult(source=review_path, target=target, copied=True))

    return results


def resolve_repository_relative_path(root: Path, rel_path: str) -> Path:
    root = root.resolve()
    return (root.parent / rel_path).resolve()


def select_flow_source(root: Path, review_doc: KnowledgeDocument) -> Path:
    derived_from = ensure_string_list(
        review_doc.header.get("derived_from"), field="derived_from", path=review_doc.path
    )
    for rel_path in derived_from:
        candidate = resolve_repository_relative_path(root, rel_path)
        parts = candidate.parts
        if "sessions" in parts and "flow" in parts and candidate.exists():
            return candidate
    raise ValueError(f"{review_doc.path}: no flow source found in `derived_from`")


def refresh_review(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
) -> list[CopyResult]:
    root = root.resolve()
    selected = select_review_files(
        root, knowledge_ids=knowledge_ids, review_files=review_files, all_files=all_files
    )
    if not selected:
        raise ValueError("No review files selected. Use --all, --knowledge-id, or --review-file.")

    results: list[CopyResult] = []
    for review_path in selected:
        current_review = parse_knowledge_document(review_path)
        flow_path = select_flow_source(root, current_review)
        flow_doc = parse_knowledge_document(flow_path)
        session_id = extract_session_id(root, flow_path)
        header = normalize_knowledge_header(
            flow_doc,
            fallback_session_id=session_id,
            derived_from=[relative_to_repository(root, flow_path)],
        )
        review_path.write_text(render_knowledge_document(header, flow_doc.body), encoding="utf-8")
        results.append(CopyResult(source=flow_path, target=review_path, copied=True))

    return results
