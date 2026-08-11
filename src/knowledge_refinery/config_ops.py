from __future__ import annotations

import os
from pathlib import Path
import re

import yaml

from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.vault_ops import validate_vault_root


MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def config_path() -> Path:
    override = os.environ.get("REFINERY_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return xdg_root / "knowledge-refinery" / "config.yaml"


def set_active_vault(vault: Path) -> Path:
    root = _validate_vault(vault)
    raw = _read_config(required=False)
    raw["vault"] = str(root)
    return _write_config(raw)


def set_deep_search_enabled(enabled: bool, *, model: str | None = None) -> Path:
    raw = _read_config(required=True)
    if not isinstance(raw.get("vault"), str):
        raise ValueError(
            "No active refinery vault. Run `knowledge-refinery vault configure --root <path>`."
        )
    current = raw.get("deep_search")
    deep_search = dict(current) if isinstance(current, dict) else {}
    if model is not None:
        deep_search["model"] = _validate_model_name(model)
    deep_search["enabled"] = enabled
    if enabled:
        configured_model = deep_search.get("model")
        if not isinstance(configured_model, str):
            raise ValueError("deep_search.model is required when deep search is enabled")
        deep_search["model"] = _validate_model_name(configured_model)
    raw["deep_search"] = deep_search
    return _write_config(raw)


def set_deep_search_model(model: str) -> Path:
    raw = _read_config(required=True)
    if not isinstance(raw.get("vault"), str):
        raise ValueError(
            "No active refinery vault. Run `knowledge-refinery vault configure --root <path>`."
        )
    current = raw.get("deep_search")
    deep_search = dict(current) if isinstance(current, dict) else {"enabled": False}
    deep_search.setdefault("enabled", False)
    deep_search["model"] = _validate_model_name(model)
    raw["deep_search"] = deep_search
    return _write_config(raw)


def get_deep_search_settings() -> tuple[bool, str | None]:
    raw = _read_config(required=False)
    deep_search = raw.get("deep_search")
    if deep_search is None:
        return False, None
    if not isinstance(deep_search, dict) or not isinstance(deep_search.get("enabled"), bool):
        raise ValueError(
            f"Invalid deep_search configuration: {config_path()}: "
            "expected deep_search.enabled to be true or false"
        )
    model = deep_search.get("model")
    if model is not None:
        if not isinstance(model, str):
            raise ValueError(
                f"Invalid deep_search configuration: {config_path()}: "
                "expected deep_search.model to be a non-empty string"
            )
        model = _validate_model_name(model)
    if deep_search["enabled"] and model is None:
        raise ValueError(
            f"Invalid deep_search configuration: {config_path()}: "
            "deep_search.model is required when enabled"
        )
    return deep_search["enabled"], model


def is_deep_search_enabled() -> bool:
    enabled, _ = get_deep_search_settings()
    return enabled


def get_deep_search_model() -> str:
    enabled, model = get_deep_search_settings()
    if not enabled or model is None:
        raise ValueError("Deep search is disabled or has no configured model")
    return model


def _write_config(raw: dict[str, object]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
    )
    return path


def get_active_vault() -> Path:
    environment = os.environ.get("REFINERY_VAULT")
    if environment:
        return _validate_vault(Path(environment))
    raw = _read_config(required=True)
    vault = raw.get("vault")
    if not isinstance(vault, str):
        raise ValueError(f"Invalid refinery config: {config_path()}")
    return _validate_vault(Path(vault))


def _read_config(*, required: bool) -> dict[str, object]:
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
    try:
        return validate_vault_root(path)
    except ValueError as error:
        raise ValueError(f"Configured refinery vault is invalid: {error}") from error


def _validate_model_name(model: str) -> str:
    normalized = model.strip()
    if not normalized or normalized != model or not MODEL_NAME_RE.fullmatch(model):
        raise ValueError(
            "deep search model must use only letters, numbers, dot, underscore, and hyphen"
        )
    return normalized
