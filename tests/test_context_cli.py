import io
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import pytest

from knowledge_refinery.agents_ops import load_agents_snippet
from knowledge_refinery.cli import main
from knowledge_refinery.mcp_server import refinery_deliver_context
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


def test_cli_reads_the_body_and_revision_written_by_mcp(
    project_store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = "PreToolUse/Bash"
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
    assert revisions[target] == saved["revision"] and revisions["SubagentStart"] is None
    assert not any(target.startswith("SessionStart/") for target in revisions)


def test_manifests_route_matching_events_to_the_host_server(project_store: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    codex = json.loads((root / ".codex-plugin/plugin.json").read_text())
    claude = json.loads((root / ".claude-plugin/plugin.json").read_text())
    shared = "./hooks/hooks.json"
    events = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "SubagentStart")
    tools = ("Bash", "apply_patch", "Edit", "Write")
    cwd = str(Path.cwd())
    repo = str(Path.cwd().parent)
    for event in events:
        for name in tools if event in ("PreToolUse", "PostToolUse") else ("",):
            target = f"{event}/{name}" if name else event
            refinery_update_context(repo, target, f"本文 {target}")
    for paths, server in (
        (codex["hooks"], "knowledge-refinery"),
        ([shared, claude["hooks"]], "plugin:knowledge-refinery:knowledge-refinery"),
    ):
        groups: dict[str, list[dict[str, Any]]] = {}
        for path in paths:
            hooks = json.loads((root / path).read_text())["hooks"]
            assert groups.keys().isdisjoint(hooks)
            groups.update(hooks)
        assert set(groups) == {"SessionStart", *events}
        (start,) = groups.pop("SessionStart")
        (fixed,) = start["hooks"]
        assert fixed["type"] == "command"
        assert "matcher" not in start and shared in paths
        for event, (group,) in groups.items():
            (handler,) = group["hooks"]
            assert handler["type"] == "mcp_tool" and handler["server"] == server
            assert handler["tool"] == "refinery_deliver_context"
            uses_tool = event in ("PreToolUse", "PostToolUse")
            assert handler["input"] == {
                "cwd": "${cwd}",
                "target": event + ("/${tool_name}" if uses_tool else ""),
            }
            if uses_tool:
                assert not re.fullmatch(group["matcher"], "Read")
            else:
                assert "matcher" not in group
            for name in tools if uses_tool else ("",):
                if name:
                    assert re.fullmatch(group["matcher"], name)
                target = handler["input"]["target"].replace("${tool_name}", name)
                assert refinery_deliver_context(cwd, target) == {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": f"本文 {target}",
                    }
                }


@pytest.mark.parametrize(
    ("host_root", "cli_version", "expected_message"),
    [
        ("PLUGIN_ROOT", None, "PATH に knowledge-refinery が見つかりません"),
        ("CLAUDE_PLUGIN_ROOT", "0.0.1", "CLI 0.0.1"),
        ("PLUGIN_ROOT", "", "knowledge-refinery --version が失敗"),
        ("CLAUDE_PLUGIN_ROOT", "installed", None),
    ],
)
def test_session_start_reports_cli_problems_or_delivers_guidance(
    tmp_path: Path, host_root: str, cli_version: str | None, expected_message: str | None
) -> None:
    root = Path(__file__).resolve().parents[1]
    plugin = tmp_path / "installed plugin"
    plugin.symlink_to(root, target_is_directory=True)
    manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
    (group,) = json.loads((plugin / "hooks/hooks.json").read_text())["hooks"]["SessionStart"]
    (hook,) = group["hooks"]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("sh", "sed"):
        program = shutil.which(name)
        assert program
        (bin_dir / name).symlink_to(program)
    cli = bin_dir / "knowledge-refinery"
    if cli_version == "installed":
        program = shutil.which("knowledge-refinery")
        assert program
        cli.symlink_to(program)
    elif cli_version is not None:
        response = f"echo {cli_version}" if cli_version else "exit 1"
        cli.write_text(f'#!/bin/sh\n[ "$1" = --version ] || exit 2\n{response}\n')
        cli.chmod(0o755)
    (tmp_path / ".refinery.yaml").write_text("schema_version: 2\nproject_id: product\n")
    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(tmp_path)}
    result = subprocess.run(
        ["/bin/sh", "-c", hook["command"]],
        cwd=tmp_path,
        env={"PATH": str(bin_dir), host_root: str(plugin)},
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    output = json.loads(result.stdout)
    if expected_message:
        assert expected_message in output["systemMessage"]
        assert manifest["version"] in output["systemMessage"]
        assert "hookSpecificOutput" not in output
    else:
        assert output["hookSpecificOutput"]["additionalContext"] == load_agents_snippet("jp")


def test_fixed_guidance_uses_only_local_enablement(
    project_store: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cwd = Path.cwd()
    monkeypatch.setenv("REFINERY_VAULT", str(tmp_path / "unavailable"))
    (cwd.parent / ".refinery.local.yaml").write_text("invalid binding")
    expected = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": load_agents_snippet("jp"),
        }
    }

    def invoke(path: Path, source: str, event: str = "SessionStart") -> str:
        payload = {"cwd": str(path), "hook_event_name": event, "source": source}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        assert main(["context", "guidance-hook"]) == 0
        return capsys.readouterr().out

    for source in ("startup", "compact"):
        assert json.loads(invoke(cwd, source)) == expected
    assert not (cwd.parent / "AGENTS.md").exists() and not (project_store / "context").exists()
    for source in ("resume", "clear", "fork", ""):
        assert not invoke(cwd, source)
    assert not invoke(cwd, "startup", "UserPromptSubmit")
    assert not invoke(tmp_path, "startup")
    (cwd.parent / ".refinery.yaml").write_text(
        "schema_version: 2\nproject_id: data\nenabled: false\n"
    )
    assert not invoke(cwd, "compact")


def test_saved_session_text_can_be_retrieved_and_cleared(
    project_store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project_store / "context/SessionStart/compact.md"
    path.parent.mkdir(parents=True)
    path.write_text("既存の前提")
    repo = str(Path.cwd().parent)
    target = "SessionStart/compact"
    assert refinery_deliver_context(repo, target) == {}
    assert main(["context", "show", target, "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert entry["body"] == "既存の前提"
    with pytest.raises(ValueError, match="SessionStart"):
        refinery_update_context(repo, target, "別の本文", entry["revision"])
    assert refinery_update_context(repo, target, None, entry["revision"])["body"] is None


def test_delivery_respects_missing_entries_project_boundary_and_opt_out(
    project_store: Path,
) -> None:
    cwd = Path.cwd()
    assert refinery_deliver_context(str(cwd), "UserPromptSubmit") == {}
    assert not (project_store / "context").exists()
    path = project_store / "context/UserPromptSubmit.md"
    path.parent.mkdir()
    path.write_text(" \n")
    assert refinery_deliver_context(str(cwd), "UserPromptSubmit") == {}
    path.write_text("parent only")
    nested = cwd / "nested"
    (nested / ".git").mkdir(parents=True)
    assert refinery_deliver_context(str(nested), "UserPromptSubmit") == {}
    disable_project(cwd.parent)
    assert refinery_deliver_context(str(cwd), "UserPromptSubmit") == {}


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
    assert refinery_deliver_context(str(repo), "UserPromptSubmit") == {
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "前提"}
    }
    monkeypatch.setenv("REFINERY_VAULT", str(other))
    with pytest.raises(ValueError, match="different refinery vault"):
        refinery_deliver_context(str(repo), "UserPromptSubmit")
    assert main(["context", "show", "UserPromptSubmit", "--project", str(repo)]) != 0
    assert "different refinery vault" in capsys.readouterr().err


def test_context_rejects_symlinks_for_both_management_and_hooks(
    project_store: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Bash.md").write_text("outside")
    folder = project_store / "context"
    folder.mkdir()
    (folder / "PreToolUse").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        refinery_update_context(str(Path.cwd().parent), "PreToolUse/Edit", "text")
    assert not (outside / "Edit.md").exists()
    with pytest.raises(ValueError, match="symlink"):
        refinery_deliver_context(str(Path.cwd()), "PreToolUse/Bash")
