from __future__ import annotations

import os
from pathlib import Path

import yaml

from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.vault_ops import VAULT_MARKER


def config_path() -> Path:
    override = os.environ.get("REFINERY_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return xdg_root / "knowledge-refinery" / "config.yaml"


def set_active_vault(vault: Path) -> Path:
    root = _validate_vault(vault)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        yaml.safe_dump({"vault": str(root)}, sort_keys=False, allow_unicode=True),
    )
    return path


def get_active_vault() -> Path:
    environment = os.environ.get("REFINERY_VAULT")
    if environment:
        return _validate_vault(Path(environment))
    path = config_path()
    if not path.is_file():
        raise ValueError(
            "No active refinery vault. Run `knowledge-refinery vault configure --root <path>`."
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid refinery config: {path}: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("vault"), str):
        raise ValueError(f"Invalid refinery config: {path}")
    return _validate_vault(Path(raw["vault"]))


def _validate_vault(path: Path) -> Path:
    root = path.expanduser().resolve()
    if not (root / VAULT_MARKER).is_file():
        raise ValueError(f"Configured refinery vault does not exist: {root}")
    return root
