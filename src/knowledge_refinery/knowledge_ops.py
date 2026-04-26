from dataclasses import dataclass
from pathlib import Path
import re
import shutil

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.errors import RefineryFormatError
from knowledge_refinery.errors import RefineryPathError
from knowledge_refinery.front_matter import render_front_matter
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.yaml_utils import dump_yaml


GUIDE_FILENAMES = {"AGENTS.md", "README.md"}
REQUIRED_FIELDS = ("title", "description", "summary")
KNOWLEDGE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
KNOWLEDGE_TYPE_VALUES = ("reference", "constructive")


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
    knowledge_type: str
    title: str
    description: str
    source_sessions: list[str]
    derived_from: list[str]


@dataclass
class UpsertKnowledgeResult:
    path: Path
    created: bool
    header: dict[str, object]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "knowledge"


def ensure_string(value: object, *, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RefineryFormatError(
            summary="Knowledge file has an invalid field value.",
            path=path,
            detail=f"`{field}` must be a non-empty string",
            expected=f"A non-empty string for `{field}`.",
        )
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
        raise RefineryFormatError(
            summary="Knowledge file has an invalid field value.",
            path=path,
            detail=f"`{field}` must be a string or list of strings",
            expected=f"`{field}` must be a string or a YAML list of strings.",
        )

    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RefineryFormatError(
                summary="Knowledge file has an invalid field value.",
                path=path,
                detail=f"`{field}` must contain only non-empty strings",
                expected=f"`{field}` must be a YAML list containing only non-empty strings.",
            )
        items.append(item.strip())
    return items


def ensure_knowledge_id(value: object, *, path: Path) -> str:
    text = ensure_string(value, field="knowledge_id", path=path)
    if not KNOWLEDGE_ID_PATTERN.fullmatch(text):
        raise RefineryFormatError(
            summary="Knowledge file has an invalid knowledge_id.",
            path=path,
            detail=f"`knowledge_id` must match `{KNOWLEDGE_ID_PATTERN.pattern}`",
            expected="A lowercase slug using letters, digits, and hyphens.",
        )
    return text


def ensure_knowledge_type(value: object, *, path: Path) -> str:
    text = ensure_string(value, field="knowledge_type", path=path)
    if text not in KNOWLEDGE_TYPE_VALUES:
        allowed = ", ".join(KNOWLEDGE_TYPE_VALUES)
        raise RefineryFormatError(
            summary="Knowledge file has an invalid knowledge_type.",
            path=path,
            detail=f"`knowledge_type` must be one of: {allowed}",
            expected=f"A string equal to one of: {allowed}.",
        )
    return text


def unique_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def parse_knowledge_document(path: Path) -> KnowledgeDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RefineryPathError(
            summary="Knowledge file was not found.",
            path=path,
            detail="the selected file does not exist",
            expected="An existing Markdown knowledge file.",
            suggested_action="Check the file path and rerun the command.",
        ) from exc
    except OSError as exc:
        raise RefineryPathError(
            summary="Knowledge file could not be read.",
            path=path,
            detail=str(exc),
            expected="A readable Markdown knowledge file.",
            suggested_action="Check file permissions and rerun the command.",
        ) from exc

    try:
        header, body = split_front_matter(text)
    except RefineryFormatError as exc:
        raise RefineryFormatError(
            summary=exc.summary,
            path=path,
            detail=exc.detail or "invalid Markdown knowledge file",
            expected=exc.expected
            or "A valid YAML front matter mapping at the top of the Markdown file.",
            suggested_action=exc.suggested_action
            or "Repair the file format, then rerun the same knowledge-refinery command.",
        ) from exc
    return KnowledgeDocument(path=path, header=dict(header), body=body)


def render_knowledge_document(header: dict[str, object], body: str) -> str:
    front_matter = render_front_matter(header)
    stripped_body = body.rstrip()
    if stripped_body:
        return f"{front_matter}\n{stripped_body}\n"
    return f"{front_matter}\n"


def render_quoted_knowledge_document(header: dict[str, object], body: str) -> str:
    front_matter = f"---\n{dump_yaml(header).strip()}\n---\n"
    stripped_body = body.rstrip()
    if stripped_body:
        return f"{front_matter}\n{stripped_body}\n"
    return f"{front_matter}\n"


def ensure_markdown_filename(value: str, *, path: Path) -> str:
    text = ensure_string(value, field="file", path=path)
    if ".." in Path(text).parts:
        raise RefineryPathError(
            summary="Knowledge file path is outside the target scope.",
            path=path,
            detail="`--file` cannot contain parent directory traversal",
            expected="A relative Markdown path under the selected knowledge scope.",
            suggested_action="Pass a relative path such as `api-rate-limit.md`.",
        )
    if Path(text).suffix != ".md":
        text = f"{text}.md"
    return text


def resolve_upsert_knowledge_path(
    root: Path,
    *,
    scope: str,
    session_id: str | None,
    file: str | None,
    title: str | None,
    knowledge_id: str | None,
    knowledge_type: str | None,
) -> Path:
    root = root.resolve()
    scope_root = resolve_upsert_scope_root(root, scope=scope, session_id=session_id)
    target = infer_upsert_target(
        scope_root,
        scope=scope,
        file=file,
        title=title,
        knowledge_id=knowledge_id,
        knowledge_type=knowledge_type,
    )
    return validate_upsert_target(target, scope_root)


def resolve_upsert_scope_root(root: Path, *, scope: str, session_id: str | None) -> Path:
    if scope in {"raw", "flow"}:
        if session_id is None:
            raise RefineryCliError(
                code="session_id_required",
                summary="Knowledge upsert requires a session_id.",
                detail=f"`--session-id` is required when `--scope {scope}` is used.",
                expected="A session ID for raw or flow knowledge.",
                suggested_action="Rerun with `--session-id <session_id>`.",
            )
        return root / "sessions" / session_id / scope
    if scope == "stock":
        return root / "shared" / "stock"
    raise RefineryCliError(
        code="unsupported_knowledge_scope",
        summary="Knowledge upsert received an unsupported scope.",
        detail=f"`--scope` must be raw, flow, or stock; got {scope}",
        expected="One of: raw, flow, stock.",
    )


def infer_upsert_target(
    scope_root: Path,
    *,
    scope: str,
    file: str | None,
    title: str | None,
    knowledge_id: str | None,
    knowledge_type: str | None,
) -> Path:
    if file is not None:
        target = Path(file)
        if target.is_absolute():
            return target
        return scope_root / ensure_markdown_filename(file, path=scope_root)
    if scope == "stock" and knowledge_id is not None:
        return scope_root / knowledge_target_filename(knowledge_id, knowledge_type)
    if title is not None:
        return scope_root / f"{slugify(title)}.md"
    raise RefineryCliError(
        code="knowledge_target_required",
        summary="Knowledge upsert could not infer a target file.",
        detail="Pass `--file`, `--knowledge-id`, or `--title`.",
        expected="A target Markdown file for the knowledge document.",
    )


def validate_upsert_target(target: Path, scope_root: Path) -> Path:
    target = target.resolve()
    scope_root = scope_root.resolve()
    try:
        target.relative_to(scope_root)
    except ValueError as exc:
        raise RefineryPathError(
            summary="Knowledge file path is outside the target scope.",
            path=target,
            detail="the resolved target path is not under the selected knowledge scope",
            expected=f"A Markdown path under {scope_root.as_posix()}.",
            suggested_action="Pass a relative `--file` path under the selected scope.",
        ) from exc
    if target.name in GUIDE_FILENAMES:
        raise RefineryPathError(
            summary="Knowledge file path points to a guide file.",
            path=target,
            detail="AGENTS.md and README.md are not knowledge documents",
            expected="A Markdown knowledge file path.",
            suggested_action="Choose a different Markdown file name for the knowledge document.",
        )
    if target.suffix != ".md":
        raise RefineryPathError(
            summary="Knowledge file path is not a Markdown file.",
            path=target,
            detail="knowledge files must use the .md extension",
            expected="A Markdown knowledge file path.",
            suggested_action="Pass a file ending in `.md`.",
        )
    return target


def apply_optional_string(
    header: dict[str, object],
    field: str,
    value: str | None,
    *,
    path: Path,
) -> None:
    if value is not None:
        header[field] = ensure_string(value, field=field, path=path)


def validate_required_upsert_fields(
    header: dict[str, object], *, scope: str, path: Path
) -> dict[str, object]:
    required_fields = ["title", "description"]
    if scope in {"flow", "stock"}:
        required_fields.append("summary")
    if scope == "stock":
        required_fields.extend(["knowledge_id", "source_sessions", "derived_from"])

    normalized = dict(header)
    for field in required_fields:
        if field in {"source_sessions", "derived_from"}:
            values = ensure_string_list(normalized.get(field), field=field, path=path)
            if not values:
                raise RefineryFormatError(
                    summary="Knowledge file has an invalid field value.",
                    path=path,
                    detail=f"`{field}` must contain at least one value",
                    expected=f"A non-empty YAML list for `{field}`.",
                )
            normalized[field] = unique_strings(values)
        else:
            normalized[field] = ensure_string(normalized.get(field), field=field, path=path)
    return normalized


def validate_upsert_header(
    header: dict[str, object], *, scope: str, path: Path
) -> dict[str, object]:
    normalized = validate_required_upsert_fields(header, scope=scope, path=path)
    if normalized.get("summary") is not None:
        normalized["summary"] = ensure_string(
            normalized.get("summary"), field="summary", path=path
        )

    if normalized.get("knowledge_id") is not None:
        normalized["knowledge_id"] = ensure_knowledge_id(normalized.get("knowledge_id"), path=path)

    if normalized.get("knowledge_type") is not None:
        normalized["knowledge_type"] = ensure_knowledge_type(
            normalized.get("knowledge_type"), path=path
        )

    for field in ("tags", "source_sessions", "derived_from"):
        values = ensure_string_list(normalized.get(field), field=field, path=path)
        if values:
            normalized[field] = unique_strings(values)
        else:
            normalized.pop(field, None)

    if normalized.get("confidence") is not None:
        normalized["confidence"] = ensure_string(
            normalized.get("confidence"), field="confidence", path=path
        )

    return normalized


def upsert_knowledge(
    root: Path,
    *,
    scope: str,
    session_id: str | None,
    file: str | None,
    title: str | None,
    description: str | None,
    summary: str | None,
    knowledge_id: str | None,
    knowledge_type: str | None,
    tags: list[str],
    source_sessions: list[str],
    derived_from: list[str],
    confidence: str | None,
    body: str | None,
) -> UpsertKnowledgeResult:
    target = resolve_upsert_knowledge_path(
        root,
        scope=scope,
        session_id=session_id,
        file=file,
        title=title,
        knowledge_id=knowledge_id,
        knowledge_type=knowledge_type,
    )
    created = not target.exists()

    if created:
        header: dict[str, object] = {}
        current_body = ""
    else:
        doc = parse_knowledge_document(target)
        header = dict(doc.header)
        current_body = doc.body

    apply_optional_string(header, "title", title, path=target)
    apply_optional_string(header, "description", description, path=target)
    apply_optional_string(header, "summary", summary, path=target)
    apply_optional_string(header, "knowledge_id", knowledge_id, path=target)
    apply_optional_string(header, "knowledge_type", knowledge_type, path=target)
    apply_optional_string(header, "confidence", confidence, path=target)

    if tags:
        header["tags"] = unique_strings(ensure_string_list(tags, field="tags", path=target))
    if source_sessions:
        header["source_sessions"] = unique_strings(
            ensure_string_list(source_sessions, field="source_sessions", path=target)
        )
    if derived_from:
        header["derived_from"] = unique_strings(
            ensure_string_list(derived_from, field="derived_from", path=target)
        )

    if scope in {"raw", "flow"} and session_id is not None:
        existing_sessions = ensure_string_list(
            header.get("source_sessions"), field="source_sessions", path=target
        )
        if existing_sessions:
            header["source_sessions"] = unique_strings(existing_sessions)

    header = validate_upsert_header(header, scope=scope, path=target)
    next_body = current_body if body is None else body

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_quoted_knowledge_document(header, next_body), encoding="utf-8")

    verified = parse_knowledge_document(target)
    validate_upsert_header(verified.header, scope=scope, path=target)
    return UpsertKnowledgeResult(path=target, created=created, header=dict(verified.header))


def extract_session_id(root: Path, path: Path) -> str:
    relative_parts = path.resolve().relative_to(root.resolve()).parts
    if len(relative_parts) < 4 or relative_parts[0] != "sessions":
        raise RefineryFormatError(
            summary="Knowledge file is outside the expected refinery session layout.",
            path=path,
            detail="expected a session knowledge file under `.refinery/sessions/<session_id>/...`",
            expected="A path under `.refinery/sessions/<session_id>/raw/` or `flow/`.",
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

    knowledge_type = header.get("knowledge_type")
    if knowledge_type is not None:
        header["knowledge_type"] = ensure_knowledge_type(knowledge_type, path=doc.path)
    else:
        header.pop("knowledge_type", None)

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


def knowledge_target_filename(knowledge_id: str, knowledge_type: str | None = None) -> str:
    if knowledge_type:
        return f"{knowledge_type}--{knowledge_id}.md"
    return f"{knowledge_id}.md"


def review_target_filename(
    session_id: str, knowledge_id: str, knowledge_type: str | None = None
) -> str:
    if knowledge_type:
        return f"{session_id}--{knowledge_type}--{knowledge_id}.md"
    return f"{session_id}--{knowledge_id}.md"


def iter_flow_files(root: Path, session_id: str | None = None) -> list[Path]:
    root = root.resolve()
    sessions_root = root / "sessions"
    if session_id is not None:
        flow_roots = [sessions_root / session_id / "flow"]
    else:
        flow_roots = sorted(sessions_root.glob("*/flow"))
    candidates = sorted(
        path for flow_root in flow_roots if flow_root.exists() for path in flow_root.rglob("*.md")
    )
    return [path for path in candidates if path.name not in GUIDE_FILENAMES]


def iter_raw_files(root: Path, session_id: str | None = None) -> list[Path]:
    root = root.resolve()
    sessions_root = root / "sessions"
    if session_id is not None:
        raw_roots = [sessions_root / session_id / "raw"]
    else:
        raw_roots = sorted(sessions_root.glob("*/raw"))
    candidates = sorted(
        path for raw_root in raw_roots if raw_root.exists() for path in raw_root.rglob("*.md")
    )
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


def iter_stock_files(root: Path) -> list[Path]:
    root = root.resolve()
    stock_root = root / "shared" / "stock"
    return [path for path in sorted(stock_root.rglob("*.md")) if path.name not in GUIDE_FILENAMES]


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
        knowledge_type = header.get("knowledge_type")
        target = review_root / review_target_filename(
            current_session_id,
            knowledge_id,
            knowledge_type if isinstance(knowledge_type, str) else None,
        )
        if target.exists():
            existing_doc = parse_knowledge_document(target)
            existing_lineage = ensure_string_list(
                existing_doc.header.get("derived_from"), field="derived_from", path=target
            )
            current_lineage = relative_to_repository(root, flow_path)
            if current_lineage not in existing_lineage:
                raise RefineryConflictError(
                    summary="Multiple flow files resolve to the same review file.",
                    path=flow_path,
                    detail=f"`knowledge_id={knowledge_id}` already maps to {target.as_posix()}",
                    expected=(
                        "Each flow file in the same session should produce a unique review target."
                    ),
                    suggested_action=(
                        "Set a distinct `knowledge_id` or rename one of the flow files, "
                        "then rerun `knowledge-refinery skills prepare-review`."
                    ),
                )
            if not force:
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
                knowledge_type=(
                    ensure_knowledge_type(header["knowledge_type"], path=review_path)
                    if header.get("knowledge_type") is not None
                    else ""
                ),
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


def resolve_selected_review_file(root: Path, review_file: str) -> Path:
    path = Path(review_file)
    resolved = path if path.is_absolute() else (root.parent / path)
    review_root = (root / "shared" / "review").resolve()
    if not resolved.exists():
        raise RefineryPathError(
            summary="Selected review file was not found.",
            path=resolved,
            detail="`--review-file` points to a path that does not exist",
            expected="An existing review Markdown file.",
            suggested_action="Check the review file path and rerun the command.",
        )
    if not resolved.is_file():
        raise RefineryPathError(
            summary="Selected review path is not a file.",
            path=resolved,
            detail="`--review-file` must point to a Markdown file",
            expected="An existing review Markdown file.",
            suggested_action="Pass a file path to `--review-file` and rerun the command.",
        )
    try:
        relative = resolved.resolve().relative_to(review_root)
    except ValueError as exc:
        raise RefineryPathError(
            summary="Selected review file is outside the active review queue.",
            path=resolved,
            detail="`--review-file` must point to a file under `.refinery/shared/review/`",
            expected="An active review Markdown file inside `.refinery/shared/review/`.",
            suggested_action=(
                "Select a file from `.refinery/shared/review/` and rerun the command."
            ),
        ) from exc
    if relative.parts[:1] == ("rejected",):
        raise RefineryPathError(
            summary="Selected review file is not in the active review queue.",
            path=resolved,
            detail="`--review-file` cannot point to `.refinery/shared/review/rejected/`",
            expected="An active review Markdown file inside `.refinery/shared/review/`.",
            suggested_action=(
                "Move or recreate the review under `.refinery/shared/review/`, then retry."
            ),
        )
    return resolved


def build_review_index(root: Path) -> dict[str, list[tuple[str, Path]]]:
    by_knowledge_id: dict[str, list[tuple[str, Path]]] = {}
    for review_path in iter_review_files(root):
        doc = parse_knowledge_document(review_path)
        knowledge_id = ensure_knowledge_id(doc.header.get("knowledge_id"), path=review_path)
        knowledge_type = ""
        if doc.header.get("knowledge_type") is not None:
            knowledge_type = ensure_knowledge_type(
                doc.header.get("knowledge_type"), path=review_path
            )
        by_knowledge_id.setdefault(knowledge_id, []).append((knowledge_type, review_path))
    return by_knowledge_id


def select_review_files_by_knowledge_id(
    root: Path, knowledge_ids: list[str], knowledge_types: list[str] | None = None
) -> list[Path]:
    knowledge_types = knowledge_types or []
    by_knowledge_id = build_review_index(root)
    selected: list[Path] = []
    for knowledge_id in knowledge_ids:
        matches = [
            review_path
            for knowledge_type, review_path in by_knowledge_id.get(knowledge_id, [])
            if not knowledge_types or knowledge_type in knowledge_types
        ]
        if not matches:
            raise RefineryCliError(
                code="review_not_found",
                summary="No review file matched the requested knowledge_id.",
                path=root / "shared" / "review",
                detail=(
                    f"No review file found for knowledge_id={knowledge_id}"
                    + (
                        f" and knowledge_type in {', '.join(knowledge_types)}"
                        if knowledge_types
                        else ""
                    )
                ),
                expected=(
                    "An existing review file selected by `--knowledge-id` or `--review-file`."
                ),
                suggested_action=(
                    "Check `knowledge-refinery skills search review` and rerun with a "
                    "valid selector."
                ),
            )
        if len(matches) > 1:
            raise RefineryConflictError(
                summary="Multiple review files matched the requested knowledge_id.",
                path=root / "shared" / "review",
                detail=(
                    f"Multiple review files found for knowledge_id={knowledge_id}; "
                    "use `--knowledge-type` or `--review-file` to select one explicitly"
                ),
                expected="A single unambiguous review file for the selected knowledge_id.",
                suggested_action=(
                    "Rerun with `--knowledge-type` when the type disambiguates the match, "
                    "or use `--review-file` and pick the exact review file."
                ),
            )
        selected.append(matches[0])
    return selected


def select_review_files(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
    knowledge_types: list[str] | None = None,
) -> list[Path]:
    root = root.resolve()
    selected: list[Path] = []

    if all_files:
        selected.extend(iter_review_files(root))

    for review_file in review_files:
        selected.append(resolve_selected_review_file(root, review_file))

    if knowledge_ids:
        selected.extend(select_review_files_by_knowledge_id(root, knowledge_ids, knowledge_types))

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
    knowledge_types: list[str] | None = None,
) -> list[CopyResult]:
    root = root.resolve()
    stock_root = root / "shared" / "stock"
    stock_root.mkdir(parents=True, exist_ok=True)

    selected = select_review_files(
        root,
        knowledge_ids=knowledge_ids,
        review_files=review_files,
        all_files=all_files,
        knowledge_types=knowledge_types,
    )
    if not selected:
        raise RefineryCliError(
            code="review_selection_required",
            summary="No review files were selected.",
            detail="Use `--all`, `--knowledge-id`, or `--review-file`.",
            expected="At least one review file selected for the command.",
            suggested_action="Choose which review files to operate on, then rerun the command.",
        )

    results: list[CopyResult] = []
    for review_path in selected:
        doc = parse_knowledge_document(review_path)
        header = normalize_knowledge_header(
            doc,
            derived_from=[relative_to_repository(root, review_path)],
        )
        knowledge_id = ensure_knowledge_id(header["knowledge_id"], path=review_path)
        knowledge_type = header.get("knowledge_type")
        target = stock_root / knowledge_target_filename(
            knowledge_id,
            knowledge_type if isinstance(knowledge_type, str) else None,
        )

        if target.exists():
            results.append(CopyResult(source=review_path, target=target, copied=False))
            continue

        target.write_text(render_knowledge_document(header, doc.body), encoding="utf-8")
        results.append(CopyResult(source=review_path, target=target, copied=True))

    return results


def reject_review(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
    knowledge_types: list[str] | None = None,
    force: bool = False,
) -> list[CopyResult]:
    root = root.resolve()
    rejected_root = root / "shared" / "review" / "rejected"
    rejected_root.mkdir(parents=True, exist_ok=True)

    selected = select_review_files(
        root,
        knowledge_ids=knowledge_ids,
        review_files=review_files,
        all_files=all_files,
        knowledge_types=knowledge_types,
    )
    if not selected:
        raise RefineryCliError(
            code="review_selection_required",
            summary="No review files were selected.",
            detail="Use `--all`, `--knowledge-id`, or `--review-file`.",
            expected="At least one review file selected for the command.",
            suggested_action="Choose which review files to operate on, then rerun the command.",
        )

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
    raise RefineryFormatError(
        summary="Review file cannot be refreshed because its flow source is missing.",
        path=review_doc.path,
        detail="no flow source found in `derived_from`",
        expected="At least one existing flow file path in `derived_from`.",
        suggested_action=(
            "Repair `derived_from` or restore the missing flow file, then rerun refresh."
        ),
    )


def refresh_review(
    root: Path,
    *,
    knowledge_ids: list[str],
    review_files: list[str],
    all_files: bool,
    knowledge_types: list[str] | None = None,
) -> list[CopyResult]:
    root = root.resolve()
    selected = select_review_files(
        root,
        knowledge_ids=knowledge_ids,
        review_files=review_files,
        all_files=all_files,
        knowledge_types=knowledge_types,
    )
    if not selected:
        raise RefineryCliError(
            code="review_selection_required",
            summary="No review files were selected.",
            detail="Use `--all`, `--knowledge-id`, or `--review-file`.",
            expected="At least one review file selected for the command.",
            suggested_action="Choose which review files to operate on, then rerun the command.",
        )

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
