from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


def require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SystemExit("PyYAML is required for front matter commands. Install it with `uv add PyYAML` or `pip install PyYAML`.") from exc
    return yaml


def _split_front_matter_block(text: str) -> tuple[str, str] | None:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return None

    closing_index = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing_index is None:
        return None

    block = "\n".join(lines[1:closing_index]).strip()
    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return block, body


def parse_front_matter(text: str) -> dict[str, object]:
    split = _split_front_matter_block(text)
    if split is None:
        return {}

    block, _body = split
    if not block:
        return {}

    yaml = require_yaml()
    data = yaml.safe_load(block)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("front matter must contain a YAML mapping")
    return data


def split_front_matter(text: str) -> tuple[dict[str, object], str]:
    split = _split_front_matter_block(text)
    if split is None:
        raise ValueError("markdown file must start with YAML front matter")

    block, body = split
    header = parse_front_matter(text)
    if not header:
        raise ValueError("markdown file must contain a YAML mapping in front matter")
    return header, body


def render_front_matter(header: dict[str, object]) -> str:
    yaml = require_yaml()
    rendered = yaml.safe_dump(
        header,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{rendered}\n---\n"


def list_headers(root: Path) -> list[tuple[Path, dict[str, object]]]:
    return list_headers_filtered(root)


def list_headers_filtered(
    root: Path,
    *,
    scopes: Iterable[str] | None = None,
    session_id: str | None = None,
) -> list[tuple[Path, dict[str, object]]]:
    results: list[tuple[Path, dict[str, object]]] = []
    normalized_root = root.resolve()
    scope_set = set(scopes or [])

    for path in sorted(normalized_root.rglob("*.md")):
        if not matches_scope(normalized_root, path, scopes=scope_set, session_id=session_id):
            continue
        try:
            header = parse_front_matter(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        if header:
            results.append((path, header))
    return results


def matches_scope(root: Path, path: Path, *, scopes: set[str], session_id: str | None) -> bool:
    if not scopes:
        return True

    rel_parts = path.resolve().relative_to(root.resolve()).parts
    if not rel_parts:
        return False

    if rel_parts[0] == "sessions" and len(rel_parts) >= 4:
        current_session_id = rel_parts[1]
        layer = rel_parts[2]
        if layer not in {"raw", "flow"}:
            return False
        if layer not in scopes:
            return False
        if session_id is not None and current_session_id != session_id:
            return False
        return True

    if rel_parts[:2] == ("shared", "review"):
        return "review" in scopes and "rejected" not in rel_parts

    if rel_parts[:2] == ("shared", "stock"):
        return "stock" in scopes

    return False
