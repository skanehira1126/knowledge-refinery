from __future__ import annotations

import datetime as dt
import secrets
import string
from pathlib import Path
from typing import Any


ALPHABET = string.ascii_lowercase + string.digits


def require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SystemExit("PyYAML is required for session metadata commands. Install it with `uv add PyYAML` or `pip install PyYAML`.") from exc
    return yaml


def generate_session_id(now: dt.datetime | None = None, suffix_len: int = 6) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(suffix_len))
    return f"{timestamp}-{suffix}"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_yaml(path: Path, data: dict[str, object]) -> None:
    yaml = require_yaml()
    rendered = yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    write_text(path, rendered)


def build_directory_agents(title: str, description: str, layer: str, body_lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in body_lines)
    return (
        "---\n"
        f"title: {title}\n"
        f"description: {description}\n"
        "kind: directory_rules\n"
        f"layer: {layer}\n"
        "---\n\n"
        f"{body}\n"
    )


def read_yaml_mapping(path: Path) -> dict[str, object]:
    yaml = require_yaml()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"meta.yaml must contain a mapping: {path}")
    return data


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

    created_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
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
                "各ファイルの先頭に YAML front matter を付け、最低でも `title` と `description` を記載する。",
                "raw は一次証拠レイヤーなので、原文・抜粋・観測事実を優先し、要約を盛り込みすぎない。",
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
                "各ファイルの先頭に YAML front matter を付け、最低でも `title`, `description`, `summary` を記載する。",
                "`knowledge_id` は省略可能だが、未指定時はファイル名から導出される。",
                "`source_sessions` は省略可能だが、review 生成時に session_id が補完される。",
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
