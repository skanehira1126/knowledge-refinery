"""Read and update user-wide Knowledge Refinery settings without dropping unknown keys."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.vault_ops import validate_vault_root


def config_path() -> Path:
    """Resolve the user config path, honoring the test and automation override."""
    override = os.environ.get("REFINERY_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return xdg_root / "knowledge-refinery" / "config.yaml"


def set_active_vault(vault: Path) -> Path:
    """Validate and persist the active vault while preserving unrelated settings."""
    root = _validate_vault(vault)
    raw = _read_config(required=False)
    raw["vault"] = str(root)
    return _write_config(raw)


def _write_config(raw: dict[str, object]) -> Path:
    """Atomically render the complete user config mapping as YAML."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
    )
    return path


def get_active_vault() -> Path:
    """Resolve and validate the environment override or persisted active vault."""
    environment = os.environ.get("REFINERY_VAULT")
    if environment:
        return _validate_vault(Path(environment))
    raw = _read_config(required=True)
    vault = raw.get("vault")
    if not isinstance(vault, str):
        raise ValueError(f"Invalid refinery config: {config_path()}")
    return _validate_vault(Path(vault))


def _read_config(*, required: bool) -> dict[str, object]:
    """Load the YAML config as a string-keyed mapping.

    ``required=False`` permits a missing file when configuring the first vault,
    but malformed existing files are always rejected.
    """
    path = config_path()
    if not path.is_file():
        if required:
            raise ValueError(
                "No active refinery vault. Run `knowledge-refinery vault configure --root <path>`."
            )
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid refinery config: {path}: {error}") from error
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise ValueError(f"Invalid refinery config: {path}")
    return dict(raw)


def _validate_vault(path: Path) -> Path:
    """Validate a vault and add user-config context to domain validation errors."""
    try:
        return validate_vault_root(path)
    except ValueError as error:
        raise ValueError(f"Configured refinery vault is invalid: {error}") from error
