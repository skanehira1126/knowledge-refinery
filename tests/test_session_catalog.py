from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

import pytest

from knowledge_refinery.cli import main
from knowledge_refinery.session_catalog import list_sessions


def log(path: Path, chat_id: str, updated: str, **metadata: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": chat_id, **metadata}})
        + "\nBODY_IS_NOT_JSON_OR_READ_FOR_LISTING\n",
        encoding="utf-8",
    )
    timestamp = datetime.fromisoformat(updated).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def test_cli_list_range_sorting_paging_and_parent_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    logs = tmp_path / "sessions"
    log(logs / "a.jsonl", "a", "2026-11-07T00:00:00Z", cwd="/project")
    log(logs / "b.jsonl", "b", "2026-11-07T12:00:00Z")
    log(logs / "end.jsonl", "end", "2026-11-08T00:00:00Z")
    log(logs / "old.jsonl", "old", "2026-11-06T23:59:59Z")
    log(logs / "child.jsonl", "child", "2026-11-07T12:30:00Z", parent_thread_id="a")
    log(tmp_path / "archived_sessions" / "archive.jsonl", "archive", "2026-11-07T13:00:00Z")
    args = [
        "session",
        "list",
        "--updated-since",
        "2026-11-07T09:00:00+09:00",
        "--updated-before",
        "2026-11-08",
        "--limit",
        "1",
    ]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["updated_at_source"] == "file_mtime"
    assert first["total"] == 2 and first["next_offset"] == 1
    assert first["chats"][0]["chat_id"] == "b"
    assert main([*args, "--offset", "1"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["chats"][0]["chat_id"] == "a"
    assert second["chats"][0]["cwd"] == "/project"
    assert second["next_offset"] is None


def test_list_deduplicates_chat_before_date_filtering(tmp_path: Path) -> None:
    log(tmp_path / "old.jsonl", "same", "2026-11-07T00:00:00Z")
    latest = log(tmp_path / "new.jsonl", "same", "2026-11-09T00:00:00Z")
    listing = list_sessions([tmp_path, tmp_path])
    assert listing["total"] == 1
    assert listing["scanned_files"] == 2
    assert listing["chats"][0]["path"] == str(latest)
    assert len(listing["chats"][0]["paths"]) == 2
    assert list_sessions([tmp_path], updated_before="2026-11-08")["total"] == 0


def test_cli_list_explicit_archive_and_skipped_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archived_sessions"
    log(archive / "a.jsonl", "a", "2026-11-07T00:00:00Z")
    (archive / "bad.jsonl").write_text("invalid\n")
    (archive / "bad-payload.jsonl").write_text('{"type":"session_meta","payload":[]}\n')
    assert main(["session", "list", "--sessions-dir", str(archive)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["total"] == 1 and result["skipped_files"] == 2


@pytest.mark.parametrize(
    "options",
    [
        ["--updated-since", "invalid"],
        ["--updated-since", "2026-11-07T12:00:00"],
        ["--updated-since", "2026-11-08", "--updated-before", "2026-11-07"],
        ["--updated-since", "2026-11-07", "--updated-before", "2026-11-07"],
        ["--limit", "0"],
        ["--offset", "-1"],
    ],
)
def test_cli_list_rejects_invalid_range_and_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], options: list[str]
) -> None:
    assert main(["session", "list", "--sessions-dir", str(tmp_path), *options]) == 2
    assert capsys.readouterr().err
