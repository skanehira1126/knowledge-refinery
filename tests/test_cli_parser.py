from argparse import Namespace
from pathlib import Path

import pytest

from knowledge_refinery import __version__
from knowledge_refinery import get_version
import knowledge_refinery.cli as cli


def test_parser_accepts_update_template() -> None:
    args = cli.build_parser().parse_args(
        ["update-template", "--target", "/tmp/example", "--skill-destination", "agent"]
    )

    assert args.handler is cli.run_update_template
    assert args.target == "/tmp/example"
    assert args.skill_destination == "agent"


def test_parser_accepts_skills_search_knowledge() -> None:
    args = cli.build_parser().parse_args(
        [
            "skills",
            "search",
            "knowledge",
            "api",
            "rate",
            "--scope",
            "flow",
            "--tag",
            "domain/api",
        ]
    )

    assert args.handler is cli.run_search_knowledge
    assert args.command == "skills"
    assert args.skills_command == "search"
    assert args.terms == ["api", "rate"]
    assert args.scope == ["flow"]
    assert args.tag == ["domain/api"]


def test_parser_accepts_skills_update_session() -> None:
    args = cli.build_parser().parse_args(
        [
            "skills",
            "update-session",
            "--session-id",
            "session-123",
            "--status",
            "paused",
            "--clear-domain",
        ]
    )

    assert args.handler is cli.run_update_session
    assert args.command == "skills"
    assert args.skills_command == "update-session"
    assert args.session_id == "session-123"
    assert args.status == "paused"
    assert args.clear_domain is True


def test_parser_rejects_legacy_top_level_update_session_alias() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            [
                "update-session",
                "--session-id",
                "session-123",
                "--status",
                "paused",
                "--clear-domain",
            ]
        )


def test_get_version_returns_package_version() -> None:
    assert get_version() == __version__


def test_run_apply_template_mentions_update_template(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    exit_code = cli.run_apply_template(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": False,
        "skill_destination": "codex",
    }
    assert "update-template" in captured.out


def test_run_update_template_forces_template_refresh(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    exit_code = cli.run_update_template(args)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": True,
        "skill_destination": "agent",
    }
    assert "Updated files: 1" in output
    assert "Skill destination: .agent/skills" in output
    assert "update-agents-md" in output
    assert "state.md is preserved" in output
