import io
import json
from pathlib import Path
import re

import pytest

from knowledge_refinery.cli import main
from knowledge_refinery.mcp_server import refinery_update_context
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


@pytest.fixture
def project_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "data"
    subdir = repo / "analysis"
    subdir.mkdir(parents=True)
    vault = tmp_path / "vault"
    init_vault(vault)
    monkeypatch.setenv("REFINERY_VAULT", str(vault))
    monkeypatch.chdir(subdir)
    return setup_project(repo, vault, project_id="data").project_store


def fire_hook(monkeypatch: pytest.MonkeyPatch, cwd: Path, event: str, **fields: str) -> int:
    payload = {"cwd": str(cwd), "hook_event_name": event, **fields}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["context", "hook"])


def test_cli_reads_the_body_and_revision_written_by_mcp(
    project_store: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = "SessionStart/startup"
    assert main(["context", "show", target, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "target": target,
        "body": None,
        "revision": None,
    }
    assert not (project_store / "context").exists()

    body = "注文数の空欄は未収集。\r\n\r\n  集計時にゼロ補完しない。"
    saved = refinery_update_context(str(Path.cwd().parent), target, body)
    assert main(["context", "show", target]) == 0
    assert capsys.readouterr() == (body, "")
    assert main(["context", "show", target, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == saved
    assert main(["context", "list", "--json"]) == 0
    revisions = {row["target"]: row["revision"] for row in json.loads(capsys.readouterr().out)}
    assert revisions[target] == saved["revision"] and revisions["SessionStart/compact"] is None
    assert fire_hook(monkeypatch, Path.cwd(), "SessionStart", source="compact") == 0
    assert capsys.readouterr() == ("", "")


def test_registered_hooks_deliver_only_the_addressed_markdown(
    project_store: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = Path(__file__).resolve().parents[1] / "hooks/hooks.json"
    hooks = json.loads(manifest.read_text(encoding="utf-8"))["hooks"]
    cases = [
        ("SessionStart", {"source": source})
        for source in ("startup", "compact", "resume", "clear", "fork")
    ] + [
        ("UserPromptSubmit", {}),
        ("SubagentStart", {}),
        ("PreToolUse", {"tool_name": "Bash"}),
        ("PostToolUse", {"tool_name": "Bash"}),
        ("PreToolUse", {"tool_name": "apply_patch"}),
        ("PostToolUse", {"tool_name": "apply_patch"}),
    ]
    cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)
    for event, fields in cases:
        target = "/".join([event, *fields.values()])
        refinery_update_context(str(cwd.parent), target, f"本文 {target}")
    for event, fields in cases:
        (group,) = hooks[event]
        if fields:
            assert re.fullmatch(group["matcher"], next(iter(fields.values())))
        else:
            assert "matcher" not in group
        target = "/".join([event, *fields.values()])
        assert (
            fire_hook(monkeypatch, cwd, event, **fields, prompt="入力", tool_response="結果") == 0
        )
        assert json.loads(capsys.readouterr().out) == {
            "hookSpecificOutput": {"hookEventName": event, "additionalContext": f"本文 {target}"}
        }
    for event, fields in [
        ("Stop", {}),
        ("PreToolUse", {"tool_name": "../Bash"}),
        ("SessionStart", {"source": "future"}),
    ]:
        assert fire_hook(monkeypatch, cwd, event, **fields) == 0
        assert capsys.readouterr() == ("", "")


def test_hook_respects_missing_entries_project_boundary_and_local_opt_out(
    project_store: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cwd = Path.cwd()
    assert fire_hook(monkeypatch, cwd, "UserPromptSubmit") == 0
    assert capsys.readouterr() == ("", "")
    assert not (project_store / "context").exists()
    path = project_store / "context/UserPromptSubmit.md"
    path.parent.mkdir()
    path.write_text(" \n")
    assert fire_hook(monkeypatch, cwd, "UserPromptSubmit") == 0
    assert capsys.readouterr() == ("", "")
    path.write_text("parent only")
    nested = cwd / "nested"
    (nested / ".git").mkdir(parents=True)
    assert fire_hook(monkeypatch, nested, "UserPromptSubmit") == 0
    assert capsys.readouterr() == ("", "")
    disable_project(cwd.parent)
    assert fire_hook(monkeypatch, cwd, "UserPromptSubmit") == 0
    assert capsys.readouterr() == ("", "")
    assert main(["context", "show", "SubagentStart"]) != 0
    assert "disabled" in capsys.readouterr().err


def test_context_uses_only_verified_vault_and_explicit_project(
    project_store: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vault = tmp_path / "vault"
    other = tmp_path / "other"
    init_vault(other)
    cmd = ["context", "show", "UserPromptSubmit"]
    for location in (
        ["--project-id", "data"],
        ["--vault", str(vault)],
        ["--vault", str(other), "--project-id", "data"],
        ["--vault", str(vault), "--project-id", "../data"],
    ):
        assert main([*cmd, *location]) != 0
        assert capsys.readouterr().err
    assert not (project_store / "context").exists()
    repo = tmp_path / "data"
    refinery_update_context(str(repo), "UserPromptSubmit", "前提")
    monkeypatch.chdir(tmp_path)
    assert main([*cmd, "--vault", str(vault), "--project-id", "data"]) == 0
    assert capsys.readouterr() == ("前提", "")
    assert fire_hook(monkeypatch, repo, "UserPromptSubmit") == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"] == "前提"
    monkeypatch.setenv("REFINERY_VAULT", str(other))
    assert fire_hook(monkeypatch, repo, "UserPromptSubmit") != 0
    out, err = capsys.readouterr()
    assert not out and "different refinery vault" in err


def test_context_rejects_symlinks_for_both_management_and_hooks(
    project_store: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "startup.md").write_text("outside")
    folder = project_store / "context"
    folder.mkdir()
    (folder / "SessionStart").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        refinery_update_context(str(Path.cwd().parent), "SessionStart/compact", "text")
    assert not (outside / "compact.md").exists()
    assert fire_hook(monkeypatch, Path.cwd(), "SessionStart", source="startup") != 0
    out, err = capsys.readouterr()
    assert not out and "symlink" in err
