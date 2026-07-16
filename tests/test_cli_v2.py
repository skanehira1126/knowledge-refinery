import json
from pathlib import Path

import pytest

from knowledge_refinery.cli import build_parser
from knowledge_refinery.cli import main


def test_parser_exposes_v2_commands(tmp_path: Path) -> None:
    project = tmp_path / "pybr"
    vault = tmp_path / "refinery"
    args = build_parser().parse_args(
        [
            "project",
            "setup",
            "--target",
            str(project),
            "--vault",
            str(vault),
            "--project-id",
            "pybr",
        ]
    )

    assert args.command == "project"
    assert args.project_command == "setup"
    assert args.project_id == "pybr"
    assert args.agents is False


def test_project_status_returns_nonzero_when_unconfigured(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "unconfigured"
    project.mkdir()

    assert main(["project", "status", "--target", str(project), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "unconfigured"


def test_cli_initializes_and_connects_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()

    assert main(["vault", "init", "--root", str(vault)]) == 0
    assert (
        main(
            [
                "project",
                "setup",
                "--target",
                str(project),
                "--vault",
                str(vault),
                "--project-id",
                "pybr",
            ]
        )
        == 0
    )
    assert not (project / ".refinery").exists()
    assert (vault / "projects" / "pybr" / "experiences").is_dir()
    assert not (project / "AGENTS.md").exists()


def test_cli_setup_can_append_managed_guidance_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    agents_path = project / "AGENTS.md"
    agents_path.write_text("# Project Guide\n", encoding="utf-8")

    assert main(["vault", "init", "--root", str(vault)]) == 0
    assert (
        main(
            [
                "project",
                "setup",
                "--target",
                str(project),
                "--vault",
                str(vault),
                "--project-id",
                "pybr",
                "--agents",
            ]
        )
        == 0
    )

    content = agents_path.read_text(encoding="utf-8")
    assert content.startswith("# Project Guide\n")
    assert "knowledge-refinery:agents:start" in content


def test_cli_can_disable_status_and_reenable_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    assert main(["vault", "init", "--root", str(vault)]) == 0
    assert (
        main(
            [
                "project",
                "setup",
                "--target",
                str(project),
                "--vault",
                str(vault),
                "--project-id",
                "pybr",
                "--link",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["project", "disable", "--target", str(project)]) == 0
    assert not (project / ".refinery").exists()
    assert not (project / "AGENTS.md").exists()
    capsys.readouterr()

    assert main(["project", "status", "--target", str(project), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["state"] == "disabled"
    assert status["enabled"] is False
    assert status["vault_registered"] is True
    assert status["link_state"] == "absent"
    assert status["managed_guidance"] is False

    assert main(["project", "enable", "--target", str(project)]) == 0
    capsys.readouterr()
    assert main(["doctor", "--target", str(project), "--json"]) == 0
    diagnosis = json.loads(capsys.readouterr().out)
    assert diagnosis["ok"] is True
    assert diagnosis["project"]["ready"] is True

    assert (
        main(
            [
                "doctor",
                "--target",
                str(project),
                "--mcp-version",
                "0.1.0",
                "--json",
            ]
        )
        == 1
    )
    drift = json.loads(capsys.readouterr().out)
    assert drift["ok"] is False
    assert drift["runtime"][-1] == {
        "name": "version_match",
        "ok": False,
        "detail": "cli=0.2.0, mcp=0.1.0",
    }


def test_doctor_reports_malformed_vault_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "project"
    project.mkdir()
    assert main(["vault", "init", "--root", str(vault)]) == 0
    assert (
        main(
            [
                "project",
                "setup",
                "--target",
                str(project),
                "--vault",
                str(vault),
                "--project-id",
                "project",
            ]
        )
        == 0
    )
    (vault / "projects" / "project" / "experiences" / "broken.md").write_text(
        "not front matter\n", encoding="utf-8"
    )
    capsys.readouterr()

    assert main(["doctor", "--target", str(project), "--json"]) == 1
    diagnosis = json.loads(capsys.readouterr().out)
    documents = next(check for check in diagnosis["runtime"] if check["name"] == "vault_documents")
    assert documents["ok"] is False
    assert documents["detail"] == "checked=0, errors=1"
