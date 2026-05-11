from pathlib import Path

import pytest
import yaml

import knowledge_refinery.cli as cli
from tests._support import make_session_meta
from tests._support import write_yaml_data


def test_update_session_updates_selected_fields(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_root = refinery_root / "sessions" / "session-123"
    write_yaml_data(session_root / "meta.yaml", make_session_meta())

    exit_code = cli.main(
        [
            "session",
            "update",
            "--root",
            str(refinery_root),
            "--session-id",
            "session-123",
            "--status",
            "paused",
            "--phase",
            "analysis",
            "--next-action",
            "wait for input",
            "--flow-status",
            "in_progress",
        ]
    )
    captured = capsys.readouterr()
    meta = yaml.safe_load((session_root / "meta.yaml").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert 'session_id="session-123"' in captured.out
    assert 'status="paused"' in captured.out
    assert 'phase="analysis"' in captured.out
    assert 'flow_status="in_progress"' in captured.out
    assert meta["status"] == "paused"
    assert meta["phase"] == "analysis"
    assert meta["next_action"] == "wait for input"
    assert meta["flow_status"] == "in_progress"
    assert meta["title"] == "Initial title"
    assert meta["last_flow_update_at"] is not None


def test_update_session_can_clear_nullable_fields(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_root = refinery_root / "sessions" / "session-123"
    write_yaml_data(
        session_root / "meta.yaml",
        make_session_meta(blocked_reason="blocked", resume_condition="reply"),
    )

    exit_code = cli.main(
        [
            "session",
            "update",
            "--root",
            str(refinery_root),
            "--session-id",
            "session-123",
            "--clear-blocked-reason",
            "--clear-resume-condition",
            "--clear-domain",
            "--clear-repository",
        ]
    )
    capsys.readouterr()
    meta = yaml.safe_load((session_root / "meta.yaml").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert meta["blocked_reason"] is None
    assert meta["resume_condition"] is None
    assert meta["domain"] is None
    assert meta["repository"] is None


def test_update_session_requires_at_least_one_change(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_root = refinery_root / "sessions" / "session-123"
    write_yaml_data(
        session_root / "meta.yaml",
        make_session_meta(repository=None, domain=None),
    )

    exit_code = cli.main(
        [
            "session",
            "update",
            "--root",
            str(refinery_root),
            "--session-id",
            "session-123",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "refinery_error: session_update_required" in captured.err
