from pathlib import Path

import yaml

from knowledge_refinery import __version__
from knowledge_refinery.template_ops import TEMPLATE_METADATA_RELATIVE_PATH
from knowledge_refinery.template_ops import apply_template
from knowledge_refinery.template_ops import copy_tree
from tests._support import write_text


def test_copy_tree_preserves_existing_shared_state_on_force(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    (src / "refinery" / "shared").mkdir(parents=True)
    write_text(src / "refinery" / "shared" / "state.md", "template state\n")
    (dst / ".refinery" / "shared").mkdir(parents=True)
    target_state = dst / ".refinery" / "shared" / "state.md"
    write_text(target_state, "live state\n")

    copied = copy_tree(src, dst, force=True)

    assert copied == []
    assert target_state.read_text(encoding="utf-8") == "live state\n"


def test_copy_tree_preserves_existing_experiences_index_on_force(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    (src / "refinery" / "shared" / "experiences").mkdir(parents=True)
    write_text(
        src / "refinery" / "shared" / "experiences" / "EXPERIENCES.md",
        "template index\n",
    )
    (dst / ".refinery" / "shared" / "experiences").mkdir(parents=True)
    target_index = dst / ".refinery" / "shared" / "experiences" / "EXPERIENCES.md"
    write_text(target_index, "live index\n")

    copied = copy_tree(src, dst, force=True)

    assert copied == []
    assert target_index.read_text(encoding="utf-8") == "live index\n"


def test_copy_tree_creates_shared_state_when_missing(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    (src / "refinery" / "shared").mkdir(parents=True)
    write_text(src / "refinery" / "shared" / "state.md", "template state\n")

    copied = copy_tree(src, dst, force=True)

    assert copied == [dst / ".refinery" / "shared" / "state.md"]
    assert (dst / ".refinery" / "shared" / "state.md").read_text(encoding="utf-8") == (
        "template state\n"
    )


def test_apply_template_writes_template_metadata(tmp_path: Path) -> None:
    _, copied = apply_template(tmp_path, force=False, skill_destination="codex")

    metadata_path = tmp_path / TEMPLATE_METADATA_RELATIVE_PATH
    assert metadata_path in copied
    assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
        "cli_version": __version__,
    }


def test_apply_template_distributes_core_skills(tmp_path: Path) -> None:
    _, copied = apply_template(tmp_path, force=False, skill_destination="codex")

    expected = [
        tmp_path / ".codex" / "skills" / "refinery-session" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "refinery-capture" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "refinery-curation" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "refinery-shared" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "refinery-experiences" / "SKILL.md",
        tmp_path / ".codex" / "skills" / "refinery-repair" / "SKILL.md",
    ]

    for path in expected:
        assert path.exists()
        assert path in copied

    assert (tmp_path / ".refinery" / "shared" / "experiences" / "AGENTS.md").exists()
    assert (tmp_path / ".refinery" / "shared" / "experiences" / "EXPERIENCES.md").exists()


def test_apply_template_preserves_existing_metadata_without_force(tmp_path: Path) -> None:
    metadata_path = tmp_path / TEMPLATE_METADATA_RELATIVE_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(metadata_path, "cli_version: 0.0.1\n")

    _, copied = apply_template(tmp_path, force=False, skill_destination="codex")

    assert metadata_path not in copied
    assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
        "cli_version": "0.0.1",
    }


def test_apply_template_overwrites_existing_metadata_with_force(tmp_path: Path) -> None:
    metadata_path = tmp_path / TEMPLATE_METADATA_RELATIVE_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(metadata_path, "cli_version: 0.0.1\n")

    _, copied = apply_template(tmp_path, force=True, skill_destination="codex")

    assert metadata_path in copied
    assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
        "cli_version": __version__,
    }
