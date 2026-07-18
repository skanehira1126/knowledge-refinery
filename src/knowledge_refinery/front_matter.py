from pathlib import Path
from typing import Any

from knowledge_refinery.errors import RefineryFormatError


def require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SystemExit(
            "PyYAML is required for front matter commands. "
            "Install it with `uv add PyYAML` or `pip install PyYAML`."
        ) from exc
    return yaml


def _split_front_matter_block(text: str) -> tuple[str, str] | None:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return None

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None
    )
    if closing_index is None:
        return None

    block = "\n".join(lines[1:closing_index]).strip()
    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return block, body


def parse_front_matter(text: str, *, source_path: Path | None = None) -> dict[str, object]:
    error_path = source_path or Path("<memory>")
    split = _split_front_matter_block(text)
    if split is None:
        return {}

    block, _body = split
    if not block:
        return {}

    yaml = require_yaml()
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise RefineryFormatError(
            summary="Markdown knowledge file has invalid YAML front matter.",
            path=error_path,
            detail=str(exc),
            expected="Valid YAML syntax inside the `---` front matter block.",
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RefineryFormatError(
            summary="Markdown knowledge file has invalid YAML front matter.",
            path=error_path,
            detail="front matter must contain a YAML mapping",
            expected="A `---` block at the top of the Markdown file that parses to a mapping.",
        )
    return data


def split_front_matter(
    text: str, *, source_path: Path | None = None
) -> tuple[dict[str, object], str]:
    error_path = source_path or Path("<memory>")
    split = _split_front_matter_block(text)
    if split is None:
        raise RefineryFormatError(
            summary="Markdown knowledge file is missing YAML front matter.",
            path=error_path,
            detail="markdown file must start with YAML front matter",
            expected="A `---` block at the top of the Markdown file.",
        )

    block, body = split
    header = parse_front_matter(text, source_path=source_path)
    if not header:
        raise RefineryFormatError(
            summary="Markdown knowledge file has empty YAML front matter.",
            path=error_path,
            detail="markdown file must contain a YAML mapping in front matter",
            expected="A non-empty YAML mapping with fields such as `title` and `description`.",
        )
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
