from pathlib import Path

from knowledge_refinery.agents_ops import END_MARKER
from knowledge_refinery.agents_ops import START_MARKER_PREFIX
from knowledge_refinery.agents_ops import apply_agents_md


def test_apply_agents_md_appends_managed_block_to_existing_file(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("# Existing Guide\n", encoding="utf-8")

    result = apply_agents_md(tmp_path, lang="jp")

    content = result.read_text(encoding="utf-8")
    assert result == agents_path
    assert content.startswith("# Existing Guide\n\n")
    assert f"{START_MARKER_PREFIX} lang=jp -->" in content
    assert content.rstrip().endswith(END_MARKER)


def test_apply_agents_md_replaces_existing_managed_block_in_place(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        f"# Guide\n\n{START_MARKER_PREFIX} lang=jp -->\nold content\n{END_MARKER}\n\nTail\n",
        encoding="utf-8",
    )

    result = apply_agents_md(tmp_path, lang="en")

    content = result.read_text(encoding="utf-8")
    assert result == agents_path
    assert "old content" not in content
    assert content.count(START_MARKER_PREFIX) == 1
    assert f"{START_MARKER_PREFIX} lang=en -->" in content
    assert content.endswith("\n\nTail\n")


def test_apply_agents_md_repairs_truncated_managed_block(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        (
            f"# Guide\n\n{START_MARKER_PREFIX} lang=jp -->\n"
            "broken content without end marker\n\n"
            "## Tail\n\n"
            "Keep this section.\n"
        ),
        encoding="utf-8",
    )

    result = apply_agents_md(tmp_path, lang="en")

    content = result.read_text(encoding="utf-8")
    assert result == agents_path
    assert "broken content without end marker" not in content
    assert content.startswith("# Guide\n\n")
    assert content.count(START_MARKER_PREFIX) == 1
    assert f"{START_MARKER_PREFIX} lang=en -->" in content
    assert "## Tail\n\nKeep this section.\n" in content
