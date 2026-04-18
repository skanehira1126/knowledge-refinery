from collections.abc import Mapping
from typing import Any


class DoubleQuotedString(str):
    pass


def require_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SystemExit(
            "PyYAML is required for YAML-based commands. "
            "Install it with `uv add PyYAML` or `pip install PyYAML`."
        ) from exc
    return yaml


def _is_yaml_character(char: str) -> bool:
    code_point = ord(char)
    return (
        code_point in {0x09, 0x0A, 0x0D, 0x85}
        or 0x20 <= code_point <= 0x7E
        or 0xA0 <= code_point <= 0xD7FF
        or 0xE000 <= code_point <= 0xFFFD
        or 0x10000 <= code_point <= 0x10FFFF
    )


def _sanitize_yaml_string(value: str) -> str:
    return "".join(char for char in value if _is_yaml_character(char))


def sanitize_yaml_data(value: object) -> object:
    # YAML rejects some control and surrogate characters. Drop only those bytes and
    # preserve the rest of the structure so CLI-generated files stay readable.
    if isinstance(value, str):
        return DoubleQuotedString(_sanitize_yaml_string(value))
    if isinstance(value, list):
        return [sanitize_yaml_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_yaml_data(item) for item in value)
    if isinstance(value, Mapping):
        return {
            _sanitize_yaml_string(key) if isinstance(key, str) else key: sanitize_yaml_data(item)
            for key, item in value.items()
        }
    return value


def dump_yaml(data: Mapping[str, object]) -> str:
    yaml = require_yaml()

    class _QuotedStringDumper(yaml.SafeDumper):
        pass

    def _represent_double_quoted_string(
        dumper: _QuotedStringDumper, value: DoubleQuotedString
    ) -> Any:
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(value), style='"')

    _QuotedStringDumper.add_representer(DoubleQuotedString, _represent_double_quoted_string)

    rendered = yaml.dump(
        sanitize_yaml_data(data),
        Dumper=_QuotedStringDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return rendered
