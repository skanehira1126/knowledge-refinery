from argparse import Namespace
from pathlib import Path

import pytest

from knowledge_refinery import __version__
import knowledge_refinery.cli as cli
from knowledge_refinery.errors import RefineryConflictError
from tests._support import write_text


def test_main_warns_when_template_cli_version_differs(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_text(refinery_root / "template-meta.yaml", "cli_version: 9.9.9\n")

    exit_code = cli.main(["skills", "search", "sessions", "--root", str(refinery_root)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "No sessions found." in captured.out
    assert "applied with CLI version 9.9.9" in captured.err
    assert __version__ in captured.err


def test_main_does_not_warn_when_template_cli_version_matches(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_text(refinery_root / "template-meta.yaml", f"cli_version: {__version__}\n")

    exit_code = cli.main(["skills", "search", "sessions", "--root", str(refinery_root)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "No sessions found." in captured.out
    assert captured.err == ""


def test_main_renders_structured_error_for_invalid_front_matter(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad_file = refinery_root / "sessions" / "session-123" / "flow" / "bad.md"
    write_text(bad_file, "---\n- invalid\n---\n")

    exit_code = cli.main(
        ["skills", "search", "knowledge", "--root", str(refinery_root), "--scope", "flow"]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "refinery_error: invalid_file_format" in captured.err
    rendered_path = next(
        line.removeprefix("path: ")
        for line in captured.err.splitlines()
        if line.startswith("path: ")
    )
    assert Path(rendered_path).resolve() == bad_file.resolve()
    assert "repair_skill: refinery-repair" in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_structured_error_for_invalid_meta_yaml(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    meta_path = refinery_root / "sessions" / "session-123" / "meta.yaml"
    write_text(meta_path, "- invalid\n")

    exit_code = cli.main(["skills", "search", "sessions", "--root", str(refinery_root)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "refinery_error: invalid_file_format" in captured.err
    rendered_path = next(
        line.removeprefix("path: ")
        for line in captured.err.splitlines()
        if line.startswith("path: ")
    )
    assert Path(rendered_path).resolve() == meta_path.resolve()
    assert "repair_skill: refinery-repair" in captured.err


def test_main_renders_structured_error_for_refinery_conflict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conflict = RefineryConflictError(
        summary="Multiple flow files resolve to the same review file.",
        path=Path("/repo/.refinery/sessions/s1/flow/topic.md"),
        detail="knowledge_id collision",
        expected="Each flow file in the same session should produce a unique review target.",
        suggested_action="Fix the conflicting knowledge_id and rerun the command.",
    )

    def fake_run_search_sessions(_args: Namespace) -> int:
        raise conflict

    monkeypatch.setattr(cli, "run_search_sessions", fake_run_search_sessions)

    exit_code = cli.main(["skills", "search", "sessions"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "refinery_error: conflicting_knowledge" in captured.err
    assert "repair_skill: refinery-repair" in captured.err


def test_main_renders_structured_error_for_missing_review_file(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_review_path = refinery_root / "shared" / "review" / "missing.md"

    exit_code = cli.main(
        [
            "skills",
            "promote-review",
            "--root",
            str(refinery_root),
            "--review-file",
            str(missing_review_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "refinery_error: invalid_path" in captured.err
    rendered_path = next(
        line.removeprefix("path: ")
        for line in captured.err.splitlines()
        if line.startswith("path: ")
    )
    assert Path(rendered_path).resolve() == missing_review_path.resolve()
    assert "Traceback" not in captured.err
