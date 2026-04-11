from __future__ import annotations

from argparse import Namespace
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile

import pytest

import knowledge_refinery.cli as cli
from knowledge_refinery.template_ops import copy_tree


def test_parser_accepts_update_template() -> None:
    args = cli.build_parser().parse_args(
        ["update-template", "--target", "/tmp/example", "--skill-destination", "agent"]
    )

    assert args.handler is cli.run_update_template
    assert args.target == "/tmp/example"
    assert args.skill_destination == "agent"


def test_run_apply_template_mentions_update_template(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_apply_template(
        target_root: Path, *, force: bool, skill_destination: str
    ) -> tuple[Path, list[Path]]:
        called["target_root"] = target_root
        called["force"] = force
        called["skill_destination"] = skill_destination
        return Path("/template"), [Path("/repo/.codex/skills/refinery-session/SKILL.md")]

    monkeypatch.setattr(cli, "apply_template", fake_apply_template)
    args = Namespace(target="/repo", force=False, skill_destination="codex")

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = cli.run_apply_template(args)

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": False,
        "skill_destination": "codex",
    }
    assert "update-template" in stdout.getvalue()


def test_run_update_template_forces_template_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_apply_template(
        target_root: Path, *, force: bool, skill_destination: str
    ) -> tuple[Path, list[Path]]:
        called["target_root"] = target_root
        called["force"] = force
        called["skill_destination"] = skill_destination
        return Path("/template"), [Path("/repo/.agent/skills/refinery-session/SKILL.md")]

    monkeypatch.setattr(cli, "apply_template", fake_apply_template)
    args = Namespace(target="/repo", skill_destination="agent")

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = cli.run_update_template(args)

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": True,
        "skill_destination": "agent",
    }
    output = stdout.getvalue()
    assert "Updated files: 1" in output
    assert "Skill destination: .agent/skills" in output
    assert "update-agents-md" in output
    assert "state.md is preserved" in output


def test_copy_tree_preserves_existing_shared_state_on_force() -> None:
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = Path(src_dir)
        dst = Path(dst_dir)

        (src / "refinery" / "shared").mkdir(parents=True)
        (src / "refinery" / "shared" / "state.md").write_text("template state\n", encoding="utf-8")
        (dst / ".refinery" / "shared").mkdir(parents=True)
        target_state = dst / ".refinery" / "shared" / "state.md"
        target_state.write_text("live state\n", encoding="utf-8")

        copied = copy_tree(src, dst, force=True)

        assert copied == []
        assert target_state.read_text(encoding="utf-8") == "live state\n"


def test_copy_tree_creates_shared_state_when_missing() -> None:
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = Path(src_dir)
        dst = Path(dst_dir)

        (src / "refinery" / "shared").mkdir(parents=True)
        (src / "refinery" / "shared" / "state.md").write_text("template state\n", encoding="utf-8")

        copied = copy_tree(src, dst, force=True)

        assert copied == [dst / ".refinery" / "shared" / "state.md"]
        assert (dst / ".refinery" / "shared" / "state.md").read_text(
            encoding="utf-8"
        ) == "template state\n"
