from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
import re
import secrets

import yaml

from knowledge_refinery import get_version
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock


PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROJECT_TAG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VAULT_ID_RE = re.compile(r"^[a-f0-9]{32}$")
VAULT_MARKER = ".refinery-vault.yaml"
PROJECT_CONFIG = ".refinery.yaml"
PROJECT_LOCAL_CONFIG = ".refinery.local.yaml"
PROJECT_LINK = ".refinery"
PROJECT_METADATA = "project.yaml"
PROJECT_METADATA_SCHEMA_VERSION = 1
VAULT_SCHEMA_VERSION = 2
VAULT_MANAGER = "knowledge-refinery"


@dataclass(frozen=True)
class VaultInitResult:
    root: Path
    changed: tuple[Path, ...]


@dataclass(frozen=True)
class ProjectSetupResult:
    project_id: str
    project_store: Path
    metadata_path: Path
    config_path: Path
    local_config_path: Path
    link_path: Path | None


@dataclass(frozen=True)
class ProjectContext:
    project_root: Path
    project_id: str
    project_store: Path
    vault_root: Path


@dataclass(frozen=True)
class ProjectConfig:
    schema_version: int
    project_id: str
    enabled: bool
    vault_id: str | None


@dataclass(frozen=True)
class ProjectMetadata:
    schema_version: int
    project_id: str
    name: str
    summary: str
    tags: tuple[str, ...]
    technologies: tuple[str, ...]
    created_at: str
    updated_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "summary": self.summary,
            "tags": list(self.tags),
            "technologies": list(self.technologies),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ProjectStatus:
    project_root: Path
    config_path: Path
    config_exists: bool
    config_valid: bool
    config_error: str | None
    project_id: str | None
    enabled: bool | None
    configured_vault_id: str | None
    active_vault_id: str | None
    vault_match: bool | None
    vault_root: Path | None
    vault_registered: bool
    project_store: Path | None
    metadata_path: Path | None
    metadata_valid: bool
    metadata_error: str | None
    link_state: str

    @property
    def state(self) -> str:
        if not self.config_exists:
            return "unconfigured"
        if not self.config_valid:
            return "invalid"
        return "enabled" if self.enabled else "disabled"

    @property
    def ready(self) -> bool:
        return bool(
            self.config_valid
            and self.enabled
            and self.vault_match is True
            and self.vault_root is not None
            and self.vault_registered
            and self.metadata_valid
            and self.link_state in {"absent", "valid"}
        )


def _write_if_needed(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, content)
    return True


def init_vault(root: Path, *, force: bool = False) -> VaultInitResult:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    changed: list[Path] = []
    marker = root / VAULT_MARKER
    vault_id = _existing_vault_id(marker) or secrets.token_hex(16)
    files = {
        marker: yaml.safe_dump(
            {
                "schema_version": VAULT_SCHEMA_VERSION,
                "managed_by": VAULT_MANAGER,
                "cli_version": get_version(),
                "vault_id": vault_id,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        root / "AGENTS.md": _vault_agents(),
        root / "README.md": _vault_readme(),
        root / "projects" / ".gitkeep": "",
        root / "shared" / "memory" / "AGENTS.md": _shared_memory_agents(),
    }
    for path, content in files.items():
        migrate_marker = path == marker and marker.is_file() and read_vault_id(root) is None
        if _write_if_needed(path, content, force=force or migrate_marker):
            changed.append(path)
    return VaultInitResult(root=root, changed=tuple(changed))


def setup_project(
    target: Path,
    vault: Path,
    *,
    project_id: str | None = None,
    project_name: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    technologies: list[str] | None = None,
    create_link: bool = False,
    _allow_disabled: bool = False,
) -> ProjectSetupResult:
    target = target.expanduser().resolve()
    vault = vault.expanduser().resolve()
    if not target.is_dir():
        raise ValueError(f"Project repository does not exist: {target}")
    if target == vault or target in vault.parents or vault in target.parents:
        raise ValueError("Project repository and refinery vault must use separate directory trees")
    vault = validate_vault_root(vault)
    vault_id = _ensure_vault_id(vault)
    resolved_id = project_id or _project_id_from_directory(target.name)
    _validate_project_id(resolved_id)

    config_path = target / PROJECT_CONFIG
    _validate_setup_config(
        target,
        config_path,
        project_id=resolved_id,
        vault_id=vault_id,
        allow_disabled=_allow_disabled,
    )

    now = datetime.now(UTC).isoformat()
    metadata = ProjectMetadata(
        schema_version=PROJECT_METADATA_SCHEMA_VERSION,
        project_id=resolved_id,
        name=target.name if project_name is None else project_name,
        summary="" if summary is None else summary,
        tags=tuple(tags or []),
        technologies=tuple(technologies or []),
        created_at=now,
        updated_at=now,
    )
    validate_project_metadata(metadata.as_dict(), expected_project_id=resolved_id)

    project_store = vault / "projects" / resolved_id
    if project_store.exists() and not config_path.is_file():
        raise ValueError(
            f"project_id is already registered in this vault: {resolved_id}. "
            f"Refusing to connect an unconfigured repository to {project_store}"
        )
    metadata_path = project_store / PROJECT_METADATA
    if metadata_path.is_file():
        _validate_setup_metadata(
            vault,
            resolved_id,
            project_name=project_name,
            summary=summary,
            tags=tags,
            technologies=technologies,
        )
    for name in ("experiences", "memory"):
        (project_store / name).mkdir(parents=True, exist_ok=True)
    _write_if_needed(project_store / "AGENTS.md", _project_store_agents(resolved_id), force=False)
    if not metadata_path.is_file():
        _write_if_needed(metadata_path, _render_project_metadata(metadata), force=False)
    read_project_metadata(vault, resolved_id)

    atomic_write_text(
        config_path,
        yaml.safe_dump(
            {
                "schema_version": 2,
                "project_id": resolved_id,
                "enabled": True,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    local_config_path = target / PROJECT_LOCAL_CONFIG
    atomic_write_text(
        local_config_path,
        yaml.safe_dump(
            {"schema_version": 1, "vault_id": vault_id},
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    _ensure_gitignore(target / ".gitignore", f"/{PROJECT_LOCAL_CONFIG}")
    link_path = _ensure_optional_link(target, project_store) if create_link else None
    if link_path is not None:
        _ensure_gitignore(target / ".gitignore", f"/{PROJECT_LINK}")
    return ProjectSetupResult(
        resolved_id,
        project_store,
        metadata_path,
        config_path,
        local_config_path,
        link_path,
    )


def _validate_setup_config(
    target: Path,
    config_path: Path,
    *,
    project_id: str,
    vault_id: str,
    allow_disabled: bool,
) -> None:
    if not config_path.is_file():
        return
    existing = read_project_config(target)
    if existing.project_id != project_id:
        raise ValueError(
            f"Project is already configured as {existing.project_id}; "
            "refusing to replace it with a different project_id"
        )
    if existing.vault_id is not None and existing.vault_id != vault_id:
        raise ValueError(
            "Project is bound to a different refinery vault; refusing to reuse the same "
            "project_id from another vault"
        )
    if not existing.enabled and not allow_disabled:
        raise ValueError(
            "Project is disabled (intentional opt-out); setup will not enable it. "
            "Re-enable only after an explicit user request with "
            "`knowledge-refinery project enable --target <path>`."
        )


def _validate_setup_metadata(
    vault: Path,
    project_id: str,
    *,
    project_name: str | None,
    summary: str | None,
    tags: list[str] | None,
    technologies: list[str] | None,
) -> None:
    current = read_project_metadata(vault, project_id)
    candidates = {
        "name": (project_name, current.name),
        "summary": (summary, current.summary),
        "tags": (tuple(tags) if tags is not None else None, current.tags),
        "technologies": (
            tuple(technologies) if technologies is not None else None,
            current.technologies,
        ),
    }
    changed_fields = [
        field
        for field, (requested, existing) in candidates.items()
        if requested is not None and requested != existing
    ]
    if changed_fields:
        fields = ", ".join(changed_fields)
        raise ValueError(
            f"Project metadata already exists and differs for: {fields}. "
            "Read the current revision with `knowledge-refinery project metadata show` "
            "and use `knowledge-refinery project metadata update`."
        )


def read_project_config(project: Path) -> ProjectConfig:
    config_path = project.expanduser().resolve() / PROJECT_CONFIG
    if not config_path.is_file():
        raise ValueError(f"Missing {PROJECT_CONFIG} in {project}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid project config YAML: {config_path}: {error}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("project_id"), str):
        raise ValueError(f"Invalid project config: {config_path}")
    schema_version = raw.get("schema_version")
    if schema_version != 2:
        raise ValueError(f"Unsupported project config schema in {config_path}: {schema_version}")
    project_id = raw["project_id"]
    _validate_project_id(project_id)
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"Invalid enabled flag in project config: {config_path}")
    vault_id = _read_project_vault_id(project.expanduser().resolve(), legacy=raw.get("vault_id"))
    return ProjectConfig(
        schema_version=2,
        project_id=project_id,
        enabled=enabled,
        vault_id=vault_id,
    )


def resolve_project_id(project: Path, vault: Path | None = None) -> str:
    config = read_project_config(project)
    if not config.enabled:
        raise ValueError(
            f"Knowledge Refinery is disabled (intentional opt-out) for "
            f"{project.expanduser().resolve()}. "
            "Re-enable only after an explicit user request with "
            "`knowledge-refinery project enable --target <path>`."
        )
    if vault is not None:
        _require_matching_vault(config, vault)
    return config.project_id


def set_project_enabled(project: Path, *, enabled: bool) -> ProjectConfig:
    project_root = project.expanduser().resolve()
    config = read_project_config(project_root)
    atomic_write_text(
        project_root / PROJECT_CONFIG,
        yaml.safe_dump(
            {
                "schema_version": config.schema_version,
                "project_id": config.project_id,
                "enabled": enabled,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )
    return ProjectConfig(config.schema_version, config.project_id, enabled, config.vault_id)


def _read_project_vault_id(project_root: Path, *, legacy: object = None) -> str | None:
    path = project_root / PROJECT_LOCAL_CONFIG
    if not path.is_file():
        if legacy is None:
            return None
        if not isinstance(legacy, str) or not VAULT_ID_RE.fullmatch(legacy):
            raise ValueError(f"Invalid legacy vault_id in project config: {project_root}")
        return legacy
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid local project config YAML: {path}: {error}") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError(f"Invalid local project config: {path}")
    vault_id = raw.get("vault_id")
    if not isinstance(vault_id, str) or not VAULT_ID_RE.fullmatch(vault_id):
        raise ValueError(f"Invalid vault_id in local project config: {path}")
    return vault_id


def enable_project(
    target: Path,
    vault: Path,
    *,
    create_link: bool = False,
) -> ProjectSetupResult:
    config = read_project_config(target)
    return setup_project(
        target,
        vault,
        project_id=config.project_id,
        create_link=create_link,
        _allow_disabled=True,
    )


def disable_project(target: Path) -> ProjectConfig:
    project_root = target.expanduser().resolve()
    config = set_project_enabled(project_root, enabled=False)
    link_path = project_root / PROJECT_LINK
    if link_path.is_symlink():
        link_path.unlink()
    return config


def inspect_project(project: Path, vault: Path | None) -> ProjectStatus:
    project_root = project.expanduser().resolve()
    project_config_path = project_root / PROJECT_CONFIG
    try:
        config = read_project_config(project_root)
    except (OSError, ValueError, yaml.YAMLError) as error:
        return ProjectStatus(
            project_root=project_root,
            config_path=project_config_path,
            config_exists=project_config_path.is_file(),
            config_valid=False,
            config_error=str(error),
            project_id=None,
            enabled=None,
            configured_vault_id=None,
            active_vault_id=None,
            vault_match=None,
            vault_root=vault,
            vault_registered=False,
            project_store=None,
            metadata_path=None,
            metadata_valid=False,
            metadata_error=None,
            link_state=_link_state(project_root, None),
        )

    vault_root = vault.expanduser().resolve() if vault is not None else None
    active_vault_id: str | None = None
    vault_match: bool | None = None
    if vault_root is not None:
        try:
            active_vault_id = read_vault_id(vault_root)
        except (OSError, ValueError):
            active_vault_id = None
        vault_match = bool(
            config.vault_id is not None
            and active_vault_id is not None
            and config.vault_id == active_vault_id
        )
    project_store = vault_root / "projects" / config.project_id if vault_root is not None else None
    metadata_path = project_store / PROJECT_METADATA if project_store is not None else None
    metadata_valid = False
    metadata_error: str | None = None
    if vault_root is not None and project_store is not None and project_store.is_dir():
        try:
            read_project_metadata(vault_root, config.project_id)
            metadata_valid = True
        except (OSError, ValueError) as error:
            metadata_error = str(error)
    return ProjectStatus(
        project_root=project_root,
        config_path=project_config_path,
        config_exists=True,
        config_valid=True,
        config_error=None,
        project_id=config.project_id,
        enabled=config.enabled,
        configured_vault_id=config.vault_id,
        active_vault_id=active_vault_id,
        vault_match=vault_match,
        vault_root=vault_root,
        vault_registered=bool(project_store is not None and project_store.is_dir()),
        project_store=project_store,
        metadata_path=metadata_path,
        metadata_valid=metadata_valid,
        metadata_error=metadata_error,
        link_state=_link_state(project_root, project_store),
    )


def _link_state(project_root: Path, expected_store: Path | None) -> str:
    link_path = project_root / PROJECT_LINK
    if link_path.is_symlink():
        if expected_store is None:
            return "unverified"
        return "valid" if link_path.resolve() == expected_store.resolve() else "mismatch"
    if link_path.exists():
        return "not-symlink"
    return "absent"


def context_from_vault(vault: Path, project_id: str) -> ProjectContext:
    vault_root = validate_vault_root(vault)
    _validate_project_id(project_id)
    project_store = vault_root / "projects" / project_id
    if not project_store.is_dir():
        raise ValueError(f"Unknown refinery project: {project_id}")
    return ProjectContext(Path("."), project_id, project_store, vault_root)


def resolve_project_context(project: Path, vault: Path | None = None) -> ProjectContext:
    project_root = project.expanduser().resolve()
    if vault is not None:
        project_id = resolve_project_id(project_root, vault)
        context = context_from_vault(vault, project_id)
        return ProjectContext(project_root, project_id, context.project_store, context.vault_root)

    project_id = resolve_project_id(project_root)

    link_path = project_root / PROJECT_LINK
    if not link_path.is_symlink():
        raise ValueError("No vault supplied and optional .refinery symlink is missing")
    project_store = link_path.resolve()
    vault_root = project_store.parent.parent
    project_id = resolve_project_id(project_root, vault_root)
    context = context_from_vault(vault_root, project_id)
    if context.project_store != project_store:
        raise ValueError("Project config and refinery symlink do not agree")
    return ProjectContext(project_root, project_id, project_store, vault_root)


def list_project_ids(vault: Path) -> list[str]:
    root = validate_vault_root(vault)
    return sorted(path.name for path in (root / "projects").iterdir() if path.is_dir())


def list_project_metadata(vault: Path) -> list[ProjectMetadata]:
    root = validate_vault_root(vault)
    return [read_project_metadata(root, project_id) for project_id in list_project_ids(root)]


def read_project_metadata(vault: Path, project_id: str) -> ProjectMetadata:
    context = context_from_vault(vault, project_id)
    path = context.project_store / PROJECT_METADATA
    if not path.is_file():
        raise ValueError(f"Missing project metadata: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid project metadata: {path}: {error}") from error
    validate_project_metadata(raw, expected_project_id=project_id)
    assert isinstance(raw, dict)
    tags = raw["tags"]
    technologies = raw["technologies"]
    assert isinstance(tags, list)
    assert isinstance(technologies, list)
    return ProjectMetadata(
        schema_version=PROJECT_METADATA_SCHEMA_VERSION,
        project_id=project_id,
        name=str(raw["name"]),
        summary=str(raw["summary"]),
        tags=tuple(str(item) for item in tags),
        technologies=tuple(str(item) for item in technologies),
        created_at=str(raw["created_at"]),
        updated_at=str(raw["updated_at"]),
    )


def update_project_metadata(
    vault: Path,
    project_id: str,
    *,
    expected_updated_at: str,
    name: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    technologies: list[str] | None = None,
) -> ProjectMetadata:
    if name is None and summary is None and tags is None and technologies is None:
        raise ValueError("project metadata update requires at least one changed field")
    context = context_from_vault(vault, project_id)
    path = context.project_store / PROJECT_METADATA
    with interprocess_lock(path):
        current = read_project_metadata(context.vault_root, project_id)
        if expected_updated_at != current.updated_at:
            raise ValueError("project metadata update conflict: expected_updated_at is stale")
        updated = ProjectMetadata(
            schema_version=PROJECT_METADATA_SCHEMA_VERSION,
            project_id=project_id,
            name=current.name if name is None else name,
            summary=current.summary if summary is None else summary,
            tags=current.tags if tags is None else tuple(tags),
            technologies=(current.technologies if technologies is None else tuple(technologies)),
            created_at=current.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )
        validate_project_metadata(updated.as_dict(), expected_project_id=project_id)
        atomic_write_text(path, _render_project_metadata(updated))
    return updated


def validate_project_metadata(raw: object, *, expected_project_id: str | None = None) -> None:
    if not isinstance(raw, dict):
        raise ValueError("project metadata must be a mapping")
    if raw.get("schema_version") != PROJECT_METADATA_SCHEMA_VERSION:
        raise ValueError(f"Unsupported project metadata schema: {raw.get('schema_version')}")
    project_id = raw.get("project_id")
    if not isinstance(project_id, str):
        raise ValueError("project metadata requires project_id")
    _validate_project_id(project_id)
    if expected_project_id is not None and project_id != expected_project_id:
        raise ValueError(
            f"project metadata project_id must match path project: {expected_project_id}"
        )
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project metadata requires a non-empty name")
    summary = raw.get("summary")
    if not isinstance(summary, str):
        raise ValueError("project metadata summary must be a string")
    tags = raw.get("tags")
    technologies = raw.get("technologies")
    _validate_string_list(tags, field="tags")
    _validate_string_list(technologies, field="technologies")
    assert isinstance(tags, list)
    assert isinstance(technologies, list)
    if any(not PROJECT_TAG_RE.fullmatch(tag) for tag in tags):
        raise ValueError("project metadata tags must use lowercase kebab-case")
    if len(technologies) != len({technology.casefold() for technology in technologies}):
        raise ValueError(
            "project metadata technologies must not contain case-insensitive duplicates"
        )
    _validate_timestamp(raw.get("created_at"), field="created_at")
    _validate_timestamp(raw.get("updated_at"), field="updated_at")


def _render_project_metadata(metadata: ProjectMetadata) -> str:
    return yaml.safe_dump(metadata.as_dict(), sort_keys=False, allow_unicode=True)


def _validate_string_list(value: object, *, field: str) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"project metadata {field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"project metadata {field} must not contain duplicates")


def _validate_timestamp(value: object, *, field: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"project metadata {field} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"project metadata {field} must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"project metadata {field} must include a timezone")


def validate_vault_root(vault: Path) -> Path:
    """Return a supported refinery vault root or reject it before any writes."""
    root = vault.expanduser().resolve()
    marker = root / VAULT_MARKER
    if not marker.is_file():
        raise ValueError(f"Not a refinery vault: {root}")
    try:
        raw = yaml.safe_load(marker.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid refinery vault marker: {marker}: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid refinery vault marker: {marker}")
    if raw.get("managed_by") != VAULT_MANAGER:
        raise ValueError(
            f"Unsupported refinery vault manager in {marker}: {raw.get('managed_by')}"
        )
    if raw.get("schema_version") != VAULT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported refinery vault schema in {marker}: {raw.get('schema_version')}"
        )
    vault_id = raw.get("vault_id")
    if vault_id is not None and (
        not isinstance(vault_id, str) or not VAULT_ID_RE.fullmatch(vault_id)
    ):
        raise ValueError(f"Invalid refinery vault_id in {marker}: {vault_id}")
    return root


def read_vault_id(vault: Path) -> str | None:
    root = validate_vault_root(vault)
    raw = yaml.safe_load((root / VAULT_MARKER).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    value = raw.get("vault_id")
    return str(value) if value is not None else None


def _existing_vault_id(marker: Path) -> str | None:
    if not marker.is_file():
        return None
    root = validate_vault_root(marker.parent)
    return read_vault_id(root)


def _ensure_vault_id(vault: Path) -> str:
    root = validate_vault_root(vault)
    current = read_vault_id(root)
    if current is not None:
        return current
    marker = root / VAULT_MARKER
    raw = yaml.safe_load(marker.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    current = secrets.token_hex(16)
    raw["vault_id"] = current
    atomic_write_text(marker, yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    return current


def _require_matching_vault(config: ProjectConfig, vault: Path) -> None:
    active_vault_id = read_vault_id(vault)
    if config.vault_id is None or active_vault_id is None:
        raise ValueError(
            "Project and vault are not identity-bound yet. Rerun `vault init` for the vault, "
            "then explicitly rerun `project setup` or `project enable` for this repository."
        )
    if config.vault_id != active_vault_id:
        raise ValueError("Project is bound to a different refinery vault")


def _validate_project_id(project_id: str) -> None:
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError(
            "project_id must be a lowercase slug containing letters, digits, and hyphens"
        )


def _project_id_from_directory(name: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not candidate:
        raise ValueError(
            "Cannot derive project_id from the repository directory; pass --project-id explicitly"
        )
    _validate_project_id(candidate)
    return candidate


def _ensure_optional_link(target: Path, project_store: Path) -> Path:
    link_path = target / PROJECT_LINK
    if link_path.is_symlink():
        if link_path.resolve() != project_store.resolve():
            raise ValueError(f"{link_path} already links to {link_path.resolve()}")
        return link_path
    if link_path.exists():
        raise ValueError(f"{link_path} already exists and is not a symlink")
    link_path.symlink_to(project_store, target_is_directory=True)
    return link_path


def _ensure_gitignore(path: Path, entry: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if entry in current.splitlines():
        return
    separator = "" if not current or current.endswith("\n") else "\n"
    atomic_write_text(path, f"{current}{separator}{entry}\n")


def _vault_readme() -> str:
    return """# Refinery

Personal, cross-project experience repository managed by knowledge-refinery.

- `projects/<project_id>/project.yaml`: project identity and discovery metadata
- `projects/<project_id>/experiences`: integrated attempt and outcome records
- `projects/<project_id>/memory`: reusable project-specific principles
- `shared/memory`: principles supported across projects
- `knowledge-tags.yaml`: optional descriptions for the shared Knowledge tag taxonomy
"""


def _vault_agents() -> str:
    return """# Refinery vault rules

- Treat each experience as one integrated account of purpose, attempts, observations,
  evaluation, and future hypotheses.
- Do not require product code or evidence files to be committed before recording an
  experience.
- Keep one experience per Markdown file and avoid a global mutable index.
- Promote only repeatedly useful principles into memory.
- Use `shared/memory` only for cross-project principles.
- Keep Knowledge tag descriptions stable and factual in `knowledge-tags.yaml`.
"""


def _project_store_agents(project_id: str) -> str:
    return f"""# {project_id} refinery rules

- `project.yaml` stores the project name, summary, tags, and technologies.
- `experiences/` stores integrated attempts and conclusions.
- Experience `evidence` entries store reference metadata only; do not copy source files or secrets.
- `memory/` stores reusable principles supported by experiences.
- Product implementation and refinery history have independent Git lifecycles.
"""


def _shared_memory_agents() -> str:
    return """# Shared memory rules

- Store only principles that are useful across projects.
- Every memory document must list supporting experience IDs.
- Keep project-specific details in the originating project memory.
"""
