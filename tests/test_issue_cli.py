import json
from pathlib import Path

import pytest

from knowledge_refinery.cli import main
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


def test_issue_cli_workflow_outside_a_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vault = tmp_path / "vault"
    init_vault(vault)
    project = tmp_path / "project"
    project.mkdir()
    setup_project(project, vault, project_id="demo")
    monkeypatch.setenv("REFINERY_VAULT", str(vault))
    monkeypatch.chdir(tmp_path)
    assert main(["issue", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert (
        main(
            [
                "issue",
                "create",
                "--title",
                "検索改善",
                "--done-when",
                "試験成功",
                "--project",
                "demo",
                "--tag",
                "改善",
                "--json",
            ]
        )
        == 0
    )
    issue = json.loads(capsys.readouterr().out)
    identifier = issue["id"]
    assert issue["projects"] == ["demo"]
    assert (
        main(
            [
                "issue",
                "update",
                identifier,
                "--expected-revision",
                "1",
                "--status",
                "done",
                "--reason",
                "試験が成功",
                "--remove-project",
                "demo",
                "--add-tag",
                "確認済み",
                "--json",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)
    assert updated["projects"] == []
    assert updated["status"] == "done"
    assert updated["revision"] == 2
    assert main(["issue", "show", identifier, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == updated
    assert main(["issue", "list", "--project", "demo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["issue", "list", "--status", "done", "--tag", "改善", "--json"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing[0]["id"] == identifier
    assert "history" not in listing[0]
    assert main(["issue", "tag", "rename", "改善", "確認済み", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["affected_issues"] == [identifier]
    assert main(["issue", "tag", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"tag": "確認済み", "count": 1}]
    assert main(["issue", "tag", "remove", "確認済み", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 1
    assert main(["issue", "tag", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert (
        main(
            [
                "issue",
                "update",
                identifier,
                "--expected-revision",
                "2",
                "--title",
                "stale",
            ]
        )
        == 2
    )
    error = capsys.readouterr()
    assert not error.out
    assert "issue_revision_conflict" in error.err
    assert main(["issue", "show", "missing"]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_issue_cli_requires_revision_for_updates(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["issue", "update", "issue-id", "--status", "ready"])
    assert error.value.code == 2
    assert "--expected-revision" in capsys.readouterr().err
