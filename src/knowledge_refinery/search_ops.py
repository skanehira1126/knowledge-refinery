from dataclasses import dataclass
from pathlib import Path

from knowledge_refinery.errors import RefineryFormatError
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.knowledge_ops import ensure_knowledge_id
from knowledge_refinery.knowledge_ops import ensure_knowledge_type
from knowledge_refinery.knowledge_ops import ensure_string
from knowledge_refinery.knowledge_ops import ensure_string_list
from knowledge_refinery.knowledge_ops import extract_session_id
from knowledge_refinery.knowledge_ops import iter_flow_files
from knowledge_refinery.knowledge_ops import iter_raw_files
from knowledge_refinery.knowledge_ops import iter_rejected_review_files
from knowledge_refinery.knowledge_ops import iter_review_files
from knowledge_refinery.knowledge_ops import iter_stock_files
from knowledge_refinery.knowledge_ops import parse_knowledge_document
from knowledge_refinery.knowledge_ops import slugify
from knowledge_refinery.session_metadata import list_sessions


DEFAULT_KNOWLEDGE_SCOPES = ("flow", "stock")
KNOWLEDGE_SCOPES = ("raw", "flow", "review", "stock")


@dataclass(slots=True)
class KnowledgeSearchEntry:
    path: Path
    scope: str
    knowledge_id: str
    knowledge_type: str
    title: str
    summary: str
    tags: list[str]
    source_sessions: list[str]
    search_text: str


@dataclass(slots=True)
class SessionSearchEntry:
    path: Path
    session_id: str
    title: str
    task: str
    status: str
    phase: str
    flow_status: str
    next_action: str
    search_text: str
    domain: str


def _ensure_optional_string(value: object, *, field: str, path: Path) -> str:
    if value is None:
        return ""
    return ensure_string(value, field=field, path=path)


def _ensure_optional_string_list(value: object, *, field: str, path: Path) -> list[str]:
    if value is None:
        return []
    return ensure_string_list(value, field=field, path=path)


def _normalized_terms(terms: list[str]) -> list[str]:
    return [term.strip().lower() for term in terms if term.strip()]


def _matches_terms(search_text: str, terms: list[str]) -> bool:
    haystack = search_text.lower()
    return all(term in haystack for term in _normalized_terms(terms))


def _scope_candidates(root: Path, scope: str, *, include_rejected: bool) -> list[Path]:
    if scope == "raw":
        return iter_raw_files(root)
    if scope == "flow":
        return iter_flow_files(root)
    if scope == "review":
        candidates = iter_review_files(root)
        if include_rejected:
            candidates.extend(iter_rejected_review_files(root))
        return sorted(candidates)
    if scope == "stock":
        return iter_stock_files(root)
    raise ValueError(f"Unknown scope: {scope}")


def _build_knowledge_entry(root: Path, path: Path, scope: str) -> KnowledgeSearchEntry:
    doc = parse_knowledge_document(path)
    header = doc.header
    title = ensure_string(header.get("title"), field="title", path=path)
    description = ensure_string(header.get("description"), field="description", path=path)
    summary = ""
    if scope != "raw":
        summary = ensure_string(header.get("summary"), field="summary", path=path)
    elif header.get("summary") is not None:
        summary = ensure_string(header.get("summary"), field="summary", path=path)

    if header.get("knowledge_id") is not None:
        knowledge_id = ensure_knowledge_id(header.get("knowledge_id"), path=path)
    elif scope == "flow":
        knowledge_id = slugify(path.stem)
    else:
        knowledge_id = ""
    knowledge_type = ""
    if header.get("knowledge_type") is not None:
        knowledge_type = ensure_knowledge_type(header.get("knowledge_type"), path=path)

    tags = _ensure_optional_string_list(header.get("tags"), field="tags", path=path)
    confidence = _ensure_optional_string(header.get("confidence"), field="confidence", path=path)
    source_sessions = _ensure_optional_string_list(
        header.get("source_sessions"), field="source_sessions", path=path
    )
    derived_from = _ensure_optional_string_list(
        header.get("derived_from"), field="derived_from", path=path
    )
    if scope == "review" and "rejected" in path.parts:
        scope_label = "review"
    else:
        scope_label = scope

    search_text = "\n".join(
        [
            path.as_posix(),
            scope_label,
            title,
            description,
            summary,
            knowledge_id,
            knowledge_type,
            confidence,
            "\n".join(tags),
            "\n".join(source_sessions),
            "\n".join(derived_from),
            doc.body,
        ]
    )
    return KnowledgeSearchEntry(
        path=path,
        scope=scope_label,
        knowledge_id=knowledge_id,
        knowledge_type=knowledge_type,
        title=title,
        summary=summary,
        tags=tags,
        source_sessions=source_sessions,
        search_text=search_text,
    )


def _matches_knowledge_filters(
    entry: KnowledgeSearchEntry,
    *,
    root: Path,
    path: Path,
    scope: str,
    terms: list[str],
    session_ids: list[str],
    tags: list[str],
    knowledge_ids: list[str],
    knowledge_types: list[str],
) -> bool:
    if session_ids:
        if scope in {"raw", "flow"}:
            if extract_session_id(root, path) not in session_ids:
                return False
        elif not set(session_ids).intersection(entry.source_sessions):
            return False
    if tags and not set(tags).issubset(set(entry.tags)):
        return False
    if knowledge_ids and entry.knowledge_id not in knowledge_ids:
        return False
    if knowledge_types and entry.knowledge_type not in knowledge_types:
        return False
    if not _matches_terms(entry.search_text, terms):
        return False
    return True


def search_knowledge(
    root: Path,
    *,
    terms: list[str],
    scopes: list[str],
    session_ids: list[str],
    tags: list[str],
    knowledge_ids: list[str],
    knowledge_types: list[str],
    include_rejected: bool = False,
) -> list[KnowledgeSearchEntry]:
    root = root.resolve()
    selected_scopes = scopes or list(DEFAULT_KNOWLEDGE_SCOPES)
    entries: list[KnowledgeSearchEntry] = []
    for scope in selected_scopes:
        for path in _scope_candidates(root, scope, include_rejected=include_rejected):
            entry = _build_knowledge_entry(root, path, scope)
            if not _matches_knowledge_filters(
                entry,
                root=root,
                path=path,
                scope=scope,
                terms=terms,
                session_ids=session_ids,
                tags=tags,
                knowledge_ids=knowledge_ids,
                knowledge_types=knowledge_types,
            ):
                continue
            entries.append(entry)
    return entries


def search_review(
    root: Path,
    *,
    terms: list[str],
    session_ids: list[str],
    tags: list[str],
    knowledge_ids: list[str],
    knowledge_types: list[str],
    include_rejected: bool = False,
) -> list[KnowledgeSearchEntry]:
    return search_knowledge(
        root,
        terms=terms,
        scopes=["review"],
        session_ids=session_ids,
        tags=tags,
        knowledge_ids=knowledge_ids,
        knowledge_types=knowledge_types,
        include_rejected=include_rejected,
    )


def _parse_state_markdown(path: Path) -> tuple[dict[str, object], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, ""
    except OSError as exc:
        raise RefineryFormatError(
            summary="Session state file could not be read.",
            path=path,
            detail=str(exc),
            expected="A readable state.md Markdown file.",
            suggested_action="Check the file permissions and rerun the same command.",
        ) from exc

    try:
        return split_front_matter(text)
    except RefineryFormatError as exc:
        raise RefineryFormatError(
            summary=exc.summary,
            path=path,
            detail=exc.detail or "invalid state.md file",
            expected=exc.expected or "A valid YAML front matter mapping at the top of state.md.",
            suggested_action=exc.suggested_action
            or "Repair state.md, then rerun the same knowledge-refinery command.",
        ) from exc


def _build_session_entry(meta_path: Path, meta: dict[str, object]) -> SessionSearchEntry:
    state_path = meta_path.parent / "state.md"
    state_header, state_body = _parse_state_markdown(state_path)
    session_id = ensure_string(meta.get("session_id"), field="session_id", path=meta_path)
    title = ensure_string(meta.get("title"), field="title", path=meta_path)
    task = ensure_string(meta.get("task"), field="task", path=meta_path)
    status = ensure_string(meta.get("status"), field="status", path=meta_path)
    phase = ensure_string(meta.get("phase"), field="phase", path=meta_path)
    flow_status = ensure_string(meta.get("flow_status"), field="flow_status", path=meta_path)
    next_action = ensure_string(meta.get("next_action"), field="next_action", path=meta_path)
    domain = _ensure_optional_string(meta.get("domain"), field="domain", path=meta_path)

    meta_fields = [
        session_id,
        _ensure_optional_string(meta.get("kind"), field="kind", path=meta_path),
        title,
        task,
        _ensure_optional_string(meta.get("repository"), field="repository", path=meta_path),
        domain,
        status,
        phase,
        _ensure_optional_string(meta.get("current_step"), field="current_step", path=meta_path),
        next_action,
        _ensure_optional_string(
            meta.get("evidence_status"), field="evidence_status", path=meta_path
        ),
        flow_status,
        _ensure_optional_string(
            meta.get("synthesis_status"), field="synthesis_status", path=meta_path
        ),
        _ensure_optional_string(
            meta.get("coverage_status"), field="coverage_status", path=meta_path
        ),
        _ensure_optional_string(meta.get("confidence"), field="confidence", path=meta_path),
        _ensure_optional_string(state_header.get("title"), field="title", path=state_path),
        _ensure_optional_string(
            state_header.get("description"), field="description", path=state_path
        ),
        state_body,
    ]
    return SessionSearchEntry(
        path=meta_path.parent,
        session_id=session_id,
        title=title,
        task=task,
        status=status,
        phase=phase,
        flow_status=flow_status,
        next_action=next_action,
        domain=domain,
        search_text="\n".join(meta_fields),
    )


def search_sessions(
    root: Path,
    *,
    terms: list[str],
    session_ids: list[str],
    statuses: list[str],
    phases: list[str],
    domains: list[str],
) -> list[SessionSearchEntry]:
    entries: list[SessionSearchEntry] = []
    for meta_path, meta in list_sessions(root.resolve()):
        entry = _build_session_entry(meta_path, meta)
        if session_ids and entry.session_id not in session_ids:
            continue
        if statuses and entry.status not in statuses:
            continue
        if phases and entry.phase not in phases:
            continue
        if domains and entry.domain not in domains:
            continue
        if not _matches_terms(entry.search_text, terms):
            continue
        entries.append(entry)
    return entries
