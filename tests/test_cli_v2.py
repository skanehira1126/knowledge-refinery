import json
from pathlib import Path

import pytest
import yaml

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
    assert args.summary is None
    assert args.tag is None
    assert args.technology is None

    alias = build_parser().parse_args(
        ["project", "setup", "--project", str(project), "--vault", str(vault)]
    )
    assert alias.target == str(project)
    experience_alias = build_parser().parse_args(
        ["experience", "search", "--target", str(project)]
    )
    assert experience_alias.project == str(project)
    memory_delete = build_parser().parse_args(
        [
            "memory",
            "delete",
            "old-rule",
            "--target",
            str(project),
            "--expected-updated-at",
            "2026-07-21T00:00:00+00:00",
        ]
    )
    assert memory_delete.confirm is False
    assert memory_delete.scope == "project"


def test_project_status_returns_nonzero_when_unconfigured(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "unconfigured"
    project.mkdir()

    assert main(["project", "status", "--target", str(project), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "unconfigured"


def test_vault_configure_reports_previous_vault_and_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert main(["vault", "init", "--root", str(first)]) == 0
    capsys.readouterr()
    assert main(["vault", "init", "--root", str(second)]) == 0
    capsys.readouterr()

    assert main(["vault", "configure", "--root", str(first)]) == 0
    output = capsys.readouterr().out
    assert f"Previous active vault: {second.resolve()}" in output
    assert f"Active vault: {first.resolve()}" in output
    assert f"Config file: {tmp_path / 'config.yaml'}" in output


def test_cli_initializes_and_connects_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()

    assert main(["vault", "init", "--root", str(vault)]) == 0
    initialization = capsys.readouterr().out
    assert f"Active vault: {vault.resolve()}" in initialization
    assert f"Config file: {tmp_path / 'config.yaml'}" in initialization
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
                "--project-name",
                "Pybr",
                "--summary",
                "特徴量選択ツール",
                "--tag",
                "ml",
                "--technology",
                "Python",
            ]
        )
        == 0
    )
    assert not (project / ".refinery").exists()
    assert (vault / "projects" / "pybr" / "experiences").is_dir()
    metadata = yaml.safe_load(
        (vault / "projects" / "pybr" / "project.yaml").read_text(encoding="utf-8")
    )
    assert metadata["name"] == "Pybr"
    assert metadata["summary"] == "特徴量選択ツール"
    assert metadata["tags"] == ["ml"]
    assert metadata["technologies"] == ["Python"]
    assert not (project / "AGENTS.md").exists()


def test_cli_reads_and_updates_project_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
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
                "product",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["project", "metadata", "show", "--target", str(project), "--json"]) == 0
    current = json.loads(capsys.readouterr().out)
    assert current["name"] == "product"
    assert (
        main(
            [
                "project",
                "metadata",
                "update",
                "--target",
                str(project),
                "--name",
                "Product API",
                "--summary",
                "顧客向けAPI",
                "--tag",
                "backend",
                "--technology",
                "Python",
                "--expected-updated-at",
                current["updated_at"],
                "--json",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)
    assert updated["name"] == "Product API"
    assert updated["summary"] == "顧客向けAPI"
    assert updated["tags"] == ["backend"]
    assert updated["technologies"] == ["Python"]

    assert (
        main(
            [
                "project",
                "metadata",
                "update",
                "--target",
                str(project),
                "--tag",
                "customer-facing",
                "--expected-updated-at",
                updated["updated_at"],
                "--json",
            ]
        )
        == 0
    )
    tag_only = json.loads(capsys.readouterr().out)
    assert tag_only["name"] == "Product API"
    assert tag_only["summary"] == "顧客向けAPI"
    assert tag_only["tags"] == ["customer-facing"]
    assert tag_only["technologies"] == ["Python"]

    assert (
        main(
            [
                "project",
                "metadata",
                "update",
                "--target",
                str(project),
                "--clear-technologies",
                "--expected-updated-at",
                tag_only["updated_at"],
                "--json",
            ]
        )
        == 0
    )
    cleared = json.loads(capsys.readouterr().out)
    assert cleared["tags"] == ["customer-facing"]
    assert cleared["technologies"] == []


def test_cli_upsert_preserves_omitted_fields_and_exact_get_returns_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
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
                "product",
            ]
        )
        == 0
    )
    capsys.readouterr()

    for experience_id in ("related", "old"):
        assert (
            main(
                [
                    "experience",
                    "upsert",
                    "--project",
                    str(project),
                    "--experience-id",
                    experience_id,
                    "--title",
                    experience_id,
                    "--purpose",
                    "support relationship validation",
                ]
            )
            == 0
        )
    capsys.readouterr()

    assert (
        main(
            [
                "experience",
                "upsert",
                "--target",
                str(project),
                "--experience-id",
                "source",
                "--title",
                "Source",
                "--purpose",
                "Test updates",
                "--tag",
                "domain/test",
                "--evidence",
                "url:https://example.com",
                "--related-experience",
                "related",
                "--supersedes",
                "old",
                "--confidence",
                "high",
                "--body",
                "original body",
            ]
        )
        == 0
    )
    capsys.readouterr()
    experience_path = vault / "projects" / "product" / "experiences" / "source.md"
    current = yaml.safe_load(experience_path.read_text(encoding="utf-8").split("---")[1])
    assert (
        main(
            [
                "experience",
                "upsert",
                "--project",
                str(project),
                "--experience-id",
                "source",
                "--title",
                "Updated source",
                "--purpose",
                "Test updates",
                "--expected-updated-at",
                current["updated_at"],
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["experience", "get", "source", "--project", str(project)]) == 0
    experience = json.loads(capsys.readouterr().out)
    assert experience["header"]["tags"] == ["domain/test"]
    assert experience["header"]["evidence"][0]["uri"] == "https://example.com"
    assert experience["header"]["related_experiences"] == ["related"]
    assert experience["header"]["supersedes"] == ["old"]
    assert experience["header"]["confidence"] == "high"
    assert experience["body"] == "original body"

    assert (
        main(
            [
                "memory",
                "upsert",
                "--project",
                str(project),
                "--memory-id",
                "rule",
                "--title",
                "Rule",
                "--summary",
                "Original",
                "--source-experience",
                "source",
                "--tag",
                "domain/test",
                "--confidence",
                "high",
            ]
        )
        == 0
    )
    capsys.readouterr()
    memory_path = vault / "projects" / "product" / "memory" / "rule.md"
    current_memory = yaml.safe_load(memory_path.read_text(encoding="utf-8").split("---")[1])
    assert (
        main(
            [
                "memory",
                "upsert",
                "--target",
                str(project),
                "--memory-id",
                "rule",
                "--title",
                "Rule",
                "--summary",
                "Updated",
                "--expected-updated-at",
                current_memory["updated_at"],
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["memory", "get", "rule", "--target", str(project)]) == 0
    memory = json.loads(capsys.readouterr().out)
    assert memory["header"]["source_experiences"] == ["source"]
    assert memory["header"]["tags"] == ["domain/test"]
    assert memory["header"]["confidence"] == "high"


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


def test_cli_browses_searches_and_describes_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
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
                "product",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "experience",
                "upsert",
                "--project",
                str(project),
                "--experience-id",
                "search-timeout",
                "--title",
                "検索timeout",
                "--purpose",
                "原因を調べる",
                "--tag",
                "issue/performance/timeout",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["tag", "browse", "--project", str(project), "--parent", "issue"]) == 0
    browsed = json.loads(capsys.readouterr().out)
    assert [item["tag"] for item in browsed["tags"]] == ["issue/performance"]
    assert (
        main(
            [
                "tag",
                "describe",
                "--project",
                str(project),
                "--tag",
                "issue/performance",
                "--description",
                "実行速度と資源効率の問題",
            ]
        )
        == 0
    )
    described = json.loads(capsys.readouterr().out)
    assert described["taxonomy_updated_at"]
    assert (
        main(
            [
                "tag",
                "search",
                "資源効率",
                "--project",
                str(project),
            ]
        )
        == 0
    )
    searched = json.loads(capsys.readouterr().out)
    assert [item["tag"] for item in searched["tags"]] == ["issue/performance"]


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
    assert status["project_metadata"]["project_id"] == "pybr"
    assert status["project_metadata_valid"] is True
    assert status["project_metadata_error"] is None
    assert status["link_state"] == "absent"
    assert status["managed_guidance"] is False
    assert status["ready_for_tools"] is False

    assert main(["doctor", "--project", str(project), "--json"]) == 0
    disabled_diagnosis = json.loads(capsys.readouterr().out)
    assert disabled_diagnosis["ok"] is True
    assert disabled_diagnosis["project"]["ready_for_tools"] is False
    project_check = next(
        check for check in disabled_diagnosis["runtime"] if check["name"] == "project"
    )
    assert project_check == {
        "name": "project",
        "ok": True,
        "detail": "disabled (healthy opt-out; tools unavailable)",
    }

    assert main(["project", "enable", "--target", str(project)]) == 0
    capsys.readouterr()
    assert not (project / "AGENTS.md").exists()
    assert main(["doctor", "--target", str(project), "--json"]) == 0
    diagnosis = json.loads(capsys.readouterr().out)
    assert diagnosis["ok"] is True
    assert diagnosis["project"]["ready"] is True

    assert main(["project", "disable", "--target", str(project)]) == 0
    capsys.readouterr()
    assert main(["project", "enable", "--target", str(project), "--agents"]) == 0
    capsys.readouterr()
    assert (project / "AGENTS.md").is_file()

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
    assert documents["detail"] == "checked=1, errors=1"
    assert documents["errors"] == [
        {
            "path": "projects/project/experiences/broken.md",
            "error": "Markdown knowledge file is missing YAML front matter.",
        }
    ]


def test_cli_reports_malformed_project_yaml_without_raising(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / ".refinery.yaml").write_text("project_id: [\n", encoding="utf-8")

    assert main(["project", "disable", "--target", str(project)]) == 2
    assert "error: Invalid project config YAML" in capsys.readouterr().err
