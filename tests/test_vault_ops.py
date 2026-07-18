from pathlib import Path

import pytest
import yaml

from knowledge_refinery.vault_ops import PROJECT_CONFIG
from knowledge_refinery.vault_ops import PROJECT_LOCAL_CONFIG
from knowledge_refinery.vault_ops import PROJECT_METADATA
from knowledge_refinery.vault_ops import VAULT_MARKER
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import enable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import inspect_project
from knowledge_refinery.vault_ops import list_project_metadata
from knowledge_refinery.vault_ops import read_project_config
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import read_vault_id
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


def test_init_vault_force_preserves_immutable_vault_id(tmp_path: Path) -> None:
    root = tmp_path / "refinery"
    init_vault(root)
    vault_id = read_vault_id(root)

    init_vault(root, force=True)

    assert vault_id is not None
    assert read_vault_id(root) == vault_id


def test_setup_project_can_add_optional_link(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)

    result = setup_project(project, vault, project_id="pybr", create_link=True)

    assert result.link_path is not None
    assert result.link_path.is_symlink()
    assert result.link_path.resolve() == vault / "projects" / "pybr"
    assert (project / ".gitignore").read_text(encoding="utf-8") == (
        "/.refinery.local.yaml\n/.refinery\n"
    )
    config = yaml.safe_load((project / PROJECT_CONFIG).read_text(encoding="utf-8"))
    assert config == {
        "schema_version": 2,
        "project_id": "pybr",
        "enabled": True,
    }
    local_config = yaml.safe_load((project / PROJECT_LOCAL_CONFIG).read_text(encoding="utf-8"))
    assert local_config == {"schema_version": 1, "vault_id": read_vault_id(vault)}
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
    assert not (vault / "projects" / "pybr" / "evidence").exists()
    assert resolve_project_context(project).vault_root == vault.resolve()


def test_setup_project_derives_a_slug_from_common_directory_names(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "My.Project Name"
    project.mkdir()
    init_vault(vault)

    result = setup_project(project, vault)

    assert result.project_id == "my-project-name"


def test_setup_project_requires_explicit_id_when_directory_cannot_form_slug(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "日本語"
    project.mkdir()
    init_vault(vault)

    with pytest.raises(ValueError, match="pass --project-id explicitly"):
        setup_project(project, vault)


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


def test_setup_project_rejects_metadata_changes_on_rerun(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(
        project,
        vault,
        project_id="product",
        project_name="Product",
        summary="original",
        tags=["backend"],
        technologies=["Python"],
    )

    setup_project(project, vault, project_id="product")
    setup_project(
        project,
        vault,
        project_id="product",
        project_name="Product",
        summary="original",
        tags=["backend"],
        technologies=["Python"],
    )
    with pytest.raises(ValueError, match="project metadata update"):
        setup_project(project, vault, project_id="product", summary="replacement")

    assert read_project_metadata(vault, "product").summary == "original"


def test_setup_project_does_not_implicitly_enable_disabled_project(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    disable_project(project)

    with pytest.raises(ValueError, match="explicit user request"):
        setup_project(project, vault, project_id="product")

    assert read_project_config(project).enabled is False


def test_project_binding_rejects_another_vault_with_same_project_id(tmp_path: Path) -> None:
    first_vault = tmp_path / "first-vault"
    second_vault = tmp_path / "second-vault"
    first_project = tmp_path / "first-project"
    second_project = tmp_path / "second-project"
    first_project.mkdir()
    second_project.mkdir()
    init_vault(first_vault)
    init_vault(second_vault)
    setup_project(first_project, first_vault, project_id="shared-project")
    setup_project(second_project, second_vault, project_id="shared-project")

    status = inspect_project(first_project, second_vault)

    assert status.vault_match is False
    assert status.ready is False
    with pytest.raises(ValueError, match="different refinery vault"):
        resolve_project_id(first_project, second_vault)
    with pytest.raises(ValueError, match="different refinery vault"):
        setup_project(first_project, second_vault, project_id="shared-project")


def test_legacy_vault_and_project_can_bind_on_explicit_rerun(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    marker = yaml.safe_load((vault / VAULT_MARKER).read_text(encoding="utf-8"))
    del marker["vault_id"]
    (vault / VAULT_MARKER).write_text(yaml.safe_dump(marker), encoding="utf-8")
    (project / PROJECT_LOCAL_CONFIG).unlink()

    assert read_vault_id(vault) is None
    assert read_project_config(project).vault_id is None
    assert inspect_project(project, vault).ready is False

    init_vault(vault)
    setup_project(project, vault, project_id="product")

    assert read_vault_id(vault) is not None
    assert read_project_config(project).vault_id == read_vault_id(vault)
    assert inspect_project(project, vault).ready is True


def test_versioned_project_config_can_bind_each_clone_locally(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    first = tmp_path / "first"
    clone = tmp_path / "clone"
    first.mkdir()
    clone.mkdir()
    init_vault(vault)
    setup_project(first, vault, project_id="product")
    (clone / PROJECT_CONFIG).write_text(
        (first / PROJECT_CONFIG).read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert read_project_config(clone).vault_id is None
    assert inspect_project(clone, vault).ready is False

    setup_project(clone, vault, project_id="product")

    assert read_project_config(clone).vault_id == read_vault_id(vault)
    assert inspect_project(clone, vault).ready is True


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


def test_read_project_config_wraps_malformed_yaml(tmp_path: Path) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / PROJECT_CONFIG).write_text("project_id: [\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid project config YAML"):
        read_project_config(project)


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
