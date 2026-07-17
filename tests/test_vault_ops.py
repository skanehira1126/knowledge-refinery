from pathlib import Path

import pytest
import yaml

from knowledge_refinery.vault_ops import PROJECT_CONFIG
from knowledge_refinery.vault_ops import PROJECT_METADATA
from knowledge_refinery.vault_ops import VAULT_MARKER
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import enable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import inspect_project
from knowledge_refinery.vault_ops import list_project_metadata
from knowledge_refinery.vault_ops import read_project_config
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import resolve_project_context
from knowledge_refinery.vault_ops import resolve_project_id
from knowledge_refinery.vault_ops import setup_project
from knowledge_refinery.vault_ops import update_project_metadata


def test_init_vault_creates_central_layout(tmp_path: Path) -> None:
    root = tmp_path / "refinery"

    result = init_vault(root)

    assert result.root == root.resolve()
    assert (root / VAULT_MARKER).is_file()
    assert (root / "projects" / ".gitkeep").is_file()
    assert (root / "shared" / "memory" / "AGENTS.md").is_file()
    marker = yaml.safe_load((root / VAULT_MARKER).read_text(encoding="utf-8"))
    assert marker["schema_version"] == 2


def test_init_vault_preserves_user_files_without_force(tmp_path: Path) -> None:
    root = tmp_path / "refinery"
    init_vault(root)
    readme = root / "README.md"
    readme.write_text("personal\n", encoding="utf-8")

    result = init_vault(root)

    assert readme.read_text(encoding="utf-8") == "personal\n"
    assert readme not in result.changed


def test_setup_project_can_add_optional_link(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)

    result = setup_project(project, vault, project_id="pybr", create_link=True)

    assert result.link_path is not None
    assert result.link_path.is_symlink()
    assert result.link_path.resolve() == vault / "projects" / "pybr"
    assert (project / ".gitignore").read_text(encoding="utf-8") == "/.refinery\n"
    config = yaml.safe_load((project / PROJECT_CONFIG).read_text(encoding="utf-8"))
    assert config == {"schema_version": 2, "project_id": "pybr", "enabled": True}
    metadata = yaml.safe_load(
        (vault / "projects" / "pybr" / PROJECT_METADATA).read_text(encoding="utf-8")
    )
    assert metadata["schema_version"] == 1
    assert metadata["project_id"] == "pybr"
    assert metadata["name"] == "pybr"
    assert metadata["summary"] == ""
    assert metadata["tags"] == []
    assert metadata["technologies"] == []
    assert metadata["created_at"] == metadata["updated_at"]
    assert resolve_project_context(project).vault_root == vault.resolve()


def test_setup_project_records_discovery_metadata(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)

    setup_project(
        project,
        vault,
        project_id="product",
        project_name="Product API",
        summary="顧客向けAPI",
        tags=["backend", "customer-facing"],
        technologies=["Python", "FastAPI"],
    )

    metadata = read_project_metadata(vault, "product")
    assert metadata.name == "Product API"
    assert metadata.summary == "顧客向けAPI"
    assert metadata.tags == ("backend", "customer-facing")
    assert metadata.technologies == ("Python", "FastAPI")
    assert list_project_metadata(vault) == [metadata]


def test_update_project_metadata_requires_current_revision(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    current = read_project_metadata(vault, "product")

    updated = update_project_metadata(
        vault,
        "product",
        name="Product API",
        summary="顧客向けAPI",
        tags=["backend"],
        technologies=["Python"],
        expected_updated_at=current.updated_at,
    )

    assert updated.created_at == current.created_at
    assert updated.updated_at != current.updated_at
    assert read_project_metadata(vault, "product") == updated
    partial = update_project_metadata(
        vault,
        "product",
        summary="更新した概要",
        expected_updated_at=updated.updated_at,
    )
    assert partial.name == "Product API"
    assert partial.summary == "更新した概要"
    assert partial.tags == ("backend",)
    assert partial.technologies == ("Python",)
    cleared = update_project_metadata(
        vault,
        "product",
        tags=[],
        expected_updated_at=partial.updated_at,
    )
    assert cleared.tags == ()
    assert cleared.technologies == ("Python",)
    with pytest.raises(ValueError, match="at least one changed field"):
        update_project_metadata(
            vault,
            "product",
            expected_updated_at=cleared.updated_at,
        )
    with pytest.raises(ValueError, match="stale"):
        update_project_metadata(
            vault,
            "product",
            name="stale",
            summary="stale",
            tags=[],
            technologies=[],
            expected_updated_at=current.updated_at,
        )


def test_project_metadata_requires_canonical_tags_and_technologies(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)

    with pytest.raises(ValueError, match="lowercase kebab-case"):
        setup_project(project, vault, project_id="product", tags=["Backend"])
    assert not (vault / "projects" / "product").exists()

    second = tmp_path / "product-two"
    second.mkdir()
    with pytest.raises(ValueError, match="case-insensitive duplicates"):
        setup_project(
            second,
            vault,
            project_id="product-two",
            technologies=["Python", "python"],
        )


def test_read_project_metadata_rejects_path_project_mismatch(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    path = vault / "projects" / "product" / PROJECT_METADATA
    path.write_text(
        path.read_text(encoding="utf-8").replace("project_id: product", "project_id: other"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must match path project"):
        read_project_metadata(vault, "product")


def test_setup_project_refuses_conflicting_refinery_path(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    (project / ".refinery").mkdir()
    init_vault(vault)

    try:
        setup_project(project, vault, project_id="pybr", create_link=True)
    except ValueError as error:
        assert "not a symlink" in str(error)
    else:
        raise AssertionError("conflicting .refinery directory must be rejected")


def test_setup_project_does_not_require_symlink(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)

    result = setup_project(project, vault, project_id="pybr")

    assert result.link_path is None
    assert not (project / ".refinery").exists()
    assert result.config_path == project / ".refinery.yaml"


def test_setup_project_refuses_to_replace_project_id(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="first")

    with pytest.raises(ValueError, match="refusing to replace"):
        setup_project(project, vault, project_id="second")


def test_setup_project_refuses_project_id_collision(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    init_vault(vault)
    setup_project(first, vault, project_id="shared-id")

    with pytest.raises(ValueError, match="already registered"):
        setup_project(second, vault, project_id="shared-id")


def test_setup_project_rejects_unsupported_vault_schema(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "project"
    project.mkdir()
    init_vault(vault)
    (vault / VAULT_MARKER).write_text(
        "schema_version: 999\nmanaged_by: knowledge-refinery\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Unsupported refinery vault schema"):
        setup_project(project, vault, project_id="project")


def test_setup_project_requires_separate_directory_trees(tmp_path: Path) -> None:
    project = tmp_path / "product"
    project.mkdir()
    vault = project / "refinery"
    init_vault(vault)

    with pytest.raises(ValueError, match="separate directory trees"):
        setup_project(project, vault, project_id="product")


def test_disable_and_enable_project_preserve_central_knowledge(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="pybr", create_link=True)
    knowledge = vault / "projects" / "pybr" / "experiences" / "retained.md"
    knowledge.write_text("retained\n", encoding="utf-8")

    config = disable_project(project)

    assert config.enabled is False
    assert knowledge.is_file()
    assert not (project / ".refinery").exists()
    assert read_project_config(project).project_id == "pybr"
    with pytest.raises(ValueError, match="is disabled"):
        resolve_project_id(project)

    result = enable_project(project, vault, create_link=True)

    assert result.project_id == "pybr"
    assert resolve_project_id(project) == "pybr"
    assert knowledge.is_file()
    assert (project / ".refinery").is_symlink()


def test_read_project_config_treats_legacy_missing_enabled_as_true(tmp_path: Path) -> None:
    project = tmp_path / "legacy"
    project.mkdir()
    (project / PROJECT_CONFIG).write_text(
        "schema_version: 2\nproject_id: legacy\n", encoding="utf-8"
    )

    assert read_project_config(project).enabled is True
    assert resolve_project_id(project) == "legacy"


def test_inspect_project_reports_registration_and_link_mismatch(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    other_vault = tmp_path / "other"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)
    init_vault(other_vault)
    setup_project(project, vault, project_id="pybr", create_link=True)
    (other_vault / "projects" / "pybr").mkdir(parents=True)

    status = inspect_project(project, other_vault)

    assert status.state == "enabled"
    assert status.vault_registered
    assert status.link_state == "mismatch"
    assert not status.ready
