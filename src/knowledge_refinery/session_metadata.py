from collections.abc import Mapping
import datetime as dt
from pathlib import Path
import secrets
import string
from typing import Any

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.errors import RefineryFormatError
from knowledge_refinery.errors import RefineryPathError
from knowledge_refinery.yaml_utils import dump_yaml


ALPHABET = string.ascii_lowercase + string.digits
SESSION_UPDATE_FIELDS = (
    "title",
    "task",
    "status",
    "phase",
    "current_step",
    "next_action",
    "blocked_reason",
    "resume_condition",
    "domain",
    "repository",
    "evidence_status",
    "flow_status",
    "synthesis_status",
    "coverage_status",
    "confidence",
)
SESSION_CLEARABLE_FIELDS = ("blocked_reason", "resume_condition", "domain", "repository")


def require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SystemExit(
            "PyYAML is required for session metadata commands. "
            "Install it with `uv add PyYAML` or `pip install PyYAML`."
        ) from exc
    return yaml


def generate_session_id(now: dt.datetime | None = None, suffix_len: int = 6) -> str:
    now = now or dt.datetime.now(dt.UTC)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(suffix_len))
    return f"{timestamp}-{suffix}"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_yaml(path: Path, data: Mapping[str, object]) -> None:
    rendered = dump_yaml(data)
    write_text(path, rendered)


def build_directory_agents(title: str, description: str, layer: str, body_lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in body_lines)
    header = dump_yaml(
        {
            "title": title,
            "description": description,
            "kind": "directory_rules",
            "layer": layer,
        }
    ).strip()
    return f"---\n{header}\n---\n\n{body}\n"


def read_yaml_mapping(path: Path) -> dict[str, object]:
    yaml = require_yaml()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RefineryFormatError(
            summary="Session metadata file has invalid YAML syntax.",
            path=path,
            detail=str(exc),
            expected="Valid YAML syntax in `meta.yaml`.",
            suggested_action="Repair the YAML syntax in meta.yaml, then rerun the same command.",
        ) from exc
    if not isinstance(data, dict):
        raise RefineryFormatError(
            summary="Session metadata file has invalid YAML structure.",
            path=path,
            detail="meta.yaml must contain a YAML mapping",
            expected="A top-level YAML mapping with keys such as `session_id` and `status`.",
            suggested_action="Repair the meta.yaml structure, then rerun the same command.",
        )
    return data


def _validate_session_update_value(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RefineryCliError(
            code="invalid_session_update",
            summary="Session update contains an invalid field value.",
            detail=f"`{field}` must be a non-empty string",
            expected=f"A non-empty string for `{field}`.",
            suggested_action="Pass a non-empty value or use the appropriate `--clear-*` option.",
        )
    return value.strip()


def resolve_session_meta_path(root: Path, session_id: str) -> Path:
    meta_path = root.resolve() / "sessions" / session_id / "meta.yaml"
    if not meta_path.is_file():
        raise RefineryPathError(
            summary="Session metadata file was not found.",
            path=meta_path,
            detail="no session matched the selected session_id",
            expected="An existing `.refinery/sessions/<session_id>/meta.yaml` file.",
            suggested_action=(
                "Check the session ID with `knowledge-refinery session search` and retry."
            ),
        )
    return meta_path


def update_session(
    root: Path,
    *,
    session_id: str,
    updates: Mapping[str, object],
    clear_fields: list[str],
) -> tuple[Path, dict[str, object]]:
    meta_path = resolve_session_meta_path(root, session_id)
    meta = read_yaml_mapping(meta_path)

    invalid_fields = sorted(set(updates) - set(SESSION_UPDATE_FIELDS))
    if invalid_fields:
        joined = ", ".join(invalid_fields)
        raise RefineryCliError(
            code="invalid_session_update",
            summary="Session update contains unsupported fields.",
            path=meta_path,
            detail=f"unsupported update fields: {joined}",
            expected=f"Supported fields: {', '.join(SESSION_UPDATE_FIELDS)}",
            suggested_action=(
                "Use one of the supported `knowledge-refinery session update` options and retry."
            ),
        )

    invalid_clear_fields = sorted(set(clear_fields) - set(SESSION_CLEARABLE_FIELDS))
    if invalid_clear_fields:
        joined = ", ".join(invalid_clear_fields)
        raise RefineryCliError(
            code="invalid_session_update",
            summary="Session update contains unsupported clear operations.",
            path=meta_path,
            detail=f"unsupported clear fields: {joined}",
            expected=f"Clearable fields: {', '.join(SESSION_CLEARABLE_FIELDS)}",
            suggested_action="Use one of the supported `--clear-*` options and retry.",
        )

    conflicting_fields = sorted(set(updates).intersection(clear_fields))
    if conflicting_fields:
        joined = ", ".join(conflicting_fields)
        raise RefineryCliError(
            code="invalid_session_update",
            summary="Session update mixes setting and clearing the same field.",
            path=meta_path,
            detail=f"field specified in both update and clear: {joined}",
            expected="Each field should either be updated or cleared, but not both.",
            suggested_action="Remove the conflicting option and retry.",
        )

    if not updates and not clear_fields:
        raise RefineryCliError(
            code="session_update_required",
            summary="No session fields were selected for update.",
            path=meta_path,
            detail="provide at least one update option or `--clear-*` option",
            expected="At least one session metadata field selected for update.",
            suggested_action=(
                "Pass one or more `knowledge-refinery session update` options and retry."
            ),
        )

    for field in clear_fields:
        meta[field] = None

    normalized_updates = {
        field: _validate_session_update_value(field, value) for field, value in updates.items()
    }
    meta.update(normalized_updates)

    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["last_updated_at"] = now
    if "flow_status" in normalized_updates:
        meta["last_flow_update_at"] = now

    write_yaml(meta_path, meta)
    updated = read_yaml_mapping(meta_path)
    return meta_path, updated


def init_session(
    root: Path,
    task: str,
    kind: str,
    title: str,
    created_by: str,
    repository: str | None,
    domain: str | None,
) -> Path:
    session_id = generate_session_id()
    session_root = root / "sessions" / session_id

    for rel in ("raw", "flow"):
        (session_root / rel).mkdir(parents=True, exist_ok=True)

    created_at = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta: dict[str, object] = {
        "session_id": session_id,
        "kind": kind,
        "title": title,
        "task": task,
        "created_at": created_at,
        "created_by": created_by,
        "repository": repository,
        "domain": domain,
        "status": "active",
        "phase": "capture",
        "current_step": "session initialized",
        "next_action": "raw に初期証拠を追加する",
        "last_updated_at": created_at,
        "closed_at": None,
        "blocked_reason": None,
        "resume_condition": None,
        "parent_session_id": None,
        "child_session_ids": [],
        "related_sessions": [],
        "depends_on": [],
        "supersedes": [],
        "superseded_by": None,
        "evidence_status": "collecting",
        "flow_status": "not_started",
        "synthesis_status": "not_started",
        "coverage_status": "unknown",
        "confidence": "low",
        "raw_item_count": 0,
        "flow_item_count": 0,
        "last_flow_update_at": None,
    }
    write_yaml(session_root / "meta.yaml", meta)

    state_md = (
        "---\n"
        f"title: Session State ({session_id})\n"
        "description: このセッションの現在地\n"
        "---\n\n"
        "- 目的:\n"
        "- 進捗:\n"
        "- 次アクション:\n"
    )
    write_text(session_root / "state.md", state_md)
    write_text(
        session_root / "raw" / "AGENTS.md",
        build_directory_agents(
            title="Raw Directory Rules",
            description="このセッションの raw ディレクトリ運用ルール",
            layer="raw",
            body_lines=[
                "このディレクトリの知識ファイルは原則 Markdown (`.md`) で管理する。",
                "各ファイルの先頭に YAML front matter を付け、"
                "最低でも `title` と `description` を記載する。",
                "`tags` は任意だが、局所検索に役立つなら "
                "`artifact/...` や `tech/...` を少数付けてよい。",
                "raw は一次証拠レイヤーなので、原文・抜粋・観測事実を優先し、"
                "要約を盛り込みすぎない。",
                "1ファイル1トピックを基本とし、原文・抜粋・観測事実を優先して記録する。",
            ],
        ),
    )
    write_text(
        session_root / "flow" / "AGENTS.md",
        build_directory_agents(
            title="Flow Directory Rules",
            description="このセッションの flow ディレクトリ運用ルール",
            layer="flow",
            body_lines=[
                "このディレクトリの知識ファイルは原則 Markdown (`.md`) で管理する。",
                "各ファイルの先頭に YAML front matter を付け、"
                "最低でも `title`, `description`, `summary` を記載する。",
                "`knowledge_id` は省略可能だが、未指定時はファイル名から導出される。",
                "`source_sessions` は省略可能だが、review 生成時に session_id が補完される。",
                "再利用検索と重複防止のため、`tags` を 2-4 個程度付け、"
                "`domain/...` または `artifact/...` を少なくとも 1 つ含める。",
                "1ファイル1トピックを基本とし、解釈・仮説・要約は証拠への参照と一緒に整理する。",
            ],
        ),
    )

    return session_root


def list_sessions(root: Path) -> list[tuple[Path, dict[str, object]]]:
    results: list[tuple[Path, dict[str, object]]] = []
    sessions_root = root / "sessions"
    if not sessions_root.exists():
        return results

    for meta_path in sorted(sessions_root.glob("*/meta.yaml")):
        results.append((meta_path, read_yaml_mapping(meta_path)))
    return results
