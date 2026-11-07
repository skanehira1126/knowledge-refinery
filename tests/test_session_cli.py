import json
from pathlib import Path
from typing import Any

import pytest

from knowledge_refinery.cli import main
from knowledge_refinery.session_ops import _Extractor
from knowledge_refinery.session_ops import extract_session
from knowledge_refinery.session_query import load_analysis
from knowledge_refinery.session_query import search_records
from knowledge_refinery.session_query import session_stats
from knowledge_refinery.session_query import show_records


def record(kind: str, **payload: Any) -> dict[str, Any]:
    return {"type": kind, "timestamp": "2026-11-07T00:00:00Z", "payload": payload}


def meta(chat: str, parent: str | None = None, agent: str = "/root/worker") -> dict[str, Any]:
    source: Any = "cli"
    if parent:
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent, "agent_path": agent}}}
    return record("session_meta", id=chat, session_id="shared", source=source, cli_version="test")


def call(cid: str = "c1", name: str = "exec_command", **extra: Any) -> dict[str, Any]:
    return record(
        "response_item",
        type="function_call",
        call_id=cid,
        name=name,
        arguments='{"cmd":"pytest"}',
        **extra,
    )


def output(cid: str = "c1", text: str = "ok", **extra: Any) -> dict[str, Any]:
    return record("response_item", type="function_call_output", call_id=cid, output=text, **extra)


def write_log(path: Path, *records: dict[str, Any] | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(r if isinstance(r, str) else json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )
    return path


def test_full_storage_bounded_search_and_no_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = tmp_path / "must-not-exist"
    long_text = "long text " * 1000 + "TAIL"
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        record("event_msg", type="task_started", turn_id="t1"),
        record(
            "response_item",
            type="function_call",
            name="exec_command",
            call_id="c1",
            arguments=json.dumps({"cmd": f"touch {marker}; cat /skills/demo/SKILL.md"}),
        ),
        output(text=long_text),
        record(
            "response_item",
            type="message",
            role="assistant",
            phase="final_answer",
            content=[{"type": "output_text", "text": "done"}],
        ),
        record("event_msg", type="task_complete", turn_id="t1"),
    )
    target = tmp_path / "analysis.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REFINERY_VAULT", str(tmp_path / "absent"))
    assert main(["session", "extract", str(source), "--output", str(target)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["calls"] == 1 and receipt["records"] == 6
    bundle = load_analysis(target)
    assert bundle["records"][3]["data"]["output"] == long_text
    assert bundle["records"][4]["data"]["phase"] == "final_answer"
    assert target.stat().st_mode & 0o777 == 0o600
    before = target.read_bytes()
    assert main(["session", "search", str(target), "--text", "TAIL", "--max-chars", "20"]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view["total"] == 1 and view["records"][0]["truncated"] is True
    assert len(view["records"][0]["preview"]) == 20
    assert target.read_bytes() == before
    assert not marker.exists()


def test_pairs_duplicates_retries_ambiguous_and_unmatched(tmp_path: Path) -> None:
    original = call(id="item-1")
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        original,
        original,
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "CommandExecution",
                "id": "item-1",
                "command": "pytest",
                "exit_code": 0,
                "status": "completed",
            },
        ),
        output(),
        call("retry"),
        output("retry"),
        call("ambiguous", id="a1"),
        call("ambiguous", id="a2"),
        output("ambiguous"),
        output("orphan"),
        call("missing"),
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "CommandExecution",
                "id": "unlinked",
                "command": "pytest",
                "exit_code": 0,
            },
        ),
    )
    bundle = extract_session(source)
    stats = session_stats(bundle)
    assert stats["calls"] == 5  # one exact duplicate omitted; retry and ambiguous requests remain
    assert stats["duplicate_records"] == 1
    assert stats["execution_events"] == 2 and stats["unlinked_execution_events"] == 1
    assert stats["tools"][0] == {
        "tool": "exec_command",
        "calls": 5,
        "with_result": 2,
        "missing_result": 3,
        "ambiguous": 2,
    }
    assert bundle["calls"][0]["execution_records"] == ["root:L4"]
    assert bundle["calls"][0]["result_records"] == ["root:L5"]
    assert len(search_records(bundle, filters={"tool": "exec_command"})["records"]) == 5
    assert (
        search_records(bundle, filters={"tool": "exec_command", "include_duplicates": True})[
            "total"
        ]
        == 6
    )
    assert any(w["code"] == "ambiguous_link" for w in bundle["warnings"])


def test_unknown_fields_invalid_json_and_reasoning_exclusion(tmp_path: Path) -> None:
    unknown = '{ "type": "future", "payload": {"new_key": "retain this"} }'
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        unknown,
        "broken JSON",
        record(
            "response_item",
            type="message",
            role="user",
            content="known",
            future_key="UNKNOWN_EXTRA",
        ),
        record("response_item", type="reasoning", summary="PRIVATE", encrypted_content="SECRET"),
        record(
            "event_msg",
            type="item_completed",
            item={"type": "Reasoning", "raw_content": "PRIVATE"},
        ),
        record("future", unknown={"type": "reasoning", "summary": "PRIVATE"}),
        record(
            "response_item",
            type="message",
            role="assistant",
            channel="analysis",
            content="PRIVATE",
        ),
        '{"type":"reasoning","text":"PRIVATE"',
        record("response_item", type=["not-a-type"], data="retain"),
    )
    bundle = extract_session(source)
    text = json.dumps(bundle)
    assert "PRIVATE" not in text and "SECRET" not in text
    assert bundle["records"][1]["unparsed"]["raw_text"] == unknown
    assert bundle["records"][2]["unparsed"]["raw_text"] == "broken JSON"
    assert "UNKNOWN_EXTRA" in text
    assert "UNKNOWN_EXTRA" not in json.dumps(search_records(bundle))
    assert search_records(bundle, filters={"text": "retain this"})["total"] == 0
    assert (
        search_records(bundle, filters={"text": "retain this", "include_unparsed": True})["total"]
        == 1
    )
    assert bundle["records"][6]["unparsed"]["raw_exact"] is False


def test_event_only_messages_and_skill_references(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        record("event_msg", type="user_message", message="$plugin:demo を使って"),
        record("event_msg", type="agent_message", message="done"),
        record(
            "response_item",
            type="custom_tool_call",
            name="functions.exec",
            call_id="c1",
            input="cat /skills/demo/SKILL.md",
        ),
        record("response_item", type="custom_tool_call_output", call_id="c1", output="ok"),
        record(
            "response_item",
            type="message",
            role="user",
            content="<skill><name>other</name>body</skill>",
        ),
        record(
            "response_item",
            type="message",
            role="user",
            content="- third: description (file: /skills/third/SKILL.md)",
        ),
    )
    bundle = extract_session(source)
    assert bundle["records"][1]["data"]["message"].startswith("$plugin:demo")
    assert bundle["records"][2]["data"]["message"] == "done"
    assert search_records(bundle, filters={"skill": "demo"})["total"] == 2
    assert search_records(bundle, filters={"skill": "plugin:demo"})["total"] == 1
    assert (
        search_records(bundle, filters={"skill": "demo", "skill_kind": "read_candidate"})["total"]
        == 1
    )
    kinds = {(m["skill"], m["kind"]) for m in bundle["skill_mentions"]}
    assert ("other", "body_provided") in kinds and ("third", "catalog_entry") in kinds


def test_subagents_scope_missing_logs_and_same_call_ids(tmp_path: Path) -> None:
    logs = tmp_path / "sessions"
    parent = write_log(
        logs / "parent.jsonl",
        meta("parent"),
        call("spawn", "spawn_agent"),
        output("spawn", '{"task_name":"/root/worker"}'),
        call(),
        output(),
    )
    child = write_log(
        logs / "child.jsonl",
        meta("child", "parent"),
        call(),
        output(),
        call("spawn", "spawn_agent"),
        output("spawn", '{"agent_id":"grand"}'),
    )
    write_log(logs / "grand.jsonl", meta("grand", "child", "/root/worker/leaf"), call(), output())
    write_log(logs / "unrelated.jsonl", meta("unrelated"), call())
    missing = extract_session(parent)
    assert session_stats(missing)["child_links"][0]["status"] == "not_loaded"
    bundle = extract_session(parent, discovery_roots=[logs])
    assert {c["chat_id"] for c in bundle["chats"]} == {"parent", "child", "grand"}
    assert {c["session_id"] for c in bundle["chats"]} == {"shared"}
    assert all(link["status"] == "matched" for link in bundle["child_links"])
    assert session_stats(bundle)["calls"] == 2
    assert session_stats(bundle, include_children=True)["calls"] == 5
    assert session_stats(bundle, chat_id="child", include_children=True)["calls"] == 3
    result = search_records(bundle, filters={"call_id": "c1"}, include_children=True)
    assert result["total"] == 6
    explicit = extract_session(parent, children=[child])
    assert len(explicit["chats"]) == 2
    assert any(link["status"] == "not_loaded" for link in explicit["child_links"])


def test_show_neighbors_related_ids_and_paging(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        record("event_msg", type="task_started", turn_id="t1"),
        call(id="item1"),
        record("event_msg", type="agent_message", message="between"),
        output(),
        record("event_msg", type="task_complete", turn_id="t1"),
    )
    bundle = extract_session(source)
    view = show_records(bundle, filters={"record_id": "root:L3"}, before=1, after=1)
    assert [r["line"] for r in view["neighbors"]] == [2, 4]
    assert [r["line"] for r in view["related"]] == [5]
    assert search_records(bundle, filters={"item_id": "item1"})["total"] == 1
    assert search_records(bundle, filters={"turn_id": "t1"})["total"] == 5
    page = search_records(bundle, limit=2)
    assert page["next_offset"] == 2
    next_page = search_records(bundle, limit=2, offset=2)
    assert next_page["records"][0]["record_id"] == "root:L3"


@pytest.mark.parametrize("records", [[], ["bad JSON"], [meta("")], [meta("one"), meta("two")]])
def test_identity_errors_do_not_create_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], records: list[Any]
) -> None:
    source = write_log(tmp_path / "bad.jsonl", *records)
    target = tmp_path / "out.json"
    assert main(["session", "extract", str(source), "--output", str(target)]) == 2
    assert capsys.readouterr().err and not target.exists()


def test_exclusive_output_and_query_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = write_log(tmp_path / "root.jsonl", meta("root"), call(), output())
    target = tmp_path / "out.json"
    args = ["session", "extract", str(source), "--output", str(target)]
    assert main(args) == 0
    capsys.readouterr()
    original = target.read_bytes()
    assert main(args) == 2
    capsys.readouterr()
    assert target.read_bytes() == original
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert main(["session", "extract", str(source), "--output", str(link)]) == 2
    capsys.readouterr()
    for options in (
        ["--limit", "0"],
        ["--offset", "-1"],
        ["--max-chars", "0"],
        ["--chat-id", "absent"],
    ):
        assert main(["session", "search", str(target), *options]) == 2
        assert capsys.readouterr().err
    assert main(["session", "show", str(target), "--call-id", "c1", "--before", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 2
    assert main(["session", "stats", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["calls"] == 1
    target.write_text('{"format":"knowledge-refinery.session-analysis","schema_version":1}')
    assert main(["session", "stats", str(target)]) == 2
    assert "re-extract" in capsys.readouterr().err


def test_concurrent_change_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_log(tmp_path / "root.jsonl", meta("root"))
    original = _Extractor.consume

    def modifying_consume(self: _Extractor, raw: str, line: int) -> None:
        original(self, raw, line)
        path.write_text("replaced")

    monkeypatch.setattr(_Extractor, "consume", modifying_consume)
    with pytest.raises(ValueError, match="changed while reading"):
        extract_session(path)


def test_unrelated_and_conflicting_child_sources_rejected(tmp_path: Path) -> None:
    parent = write_log(tmp_path / "parent.jsonl", meta("parent"))
    unrelated = write_log(tmp_path / "unrelated.jsonl", meta("other"))
    with pytest.raises(ValueError, match="not a verified descendant"):
        extract_session(parent, children=[unrelated])
    child = write_log(tmp_path / "child.jsonl", meta("child", "parent"))
    conflict = write_log(tmp_path / "conflict.jsonl", meta("child", "parent"), call())
    with pytest.raises(ValueError, match="Conflicting rollout"):
        extract_session(parent, children=[child, conflict])


def test_explicit_event_ids_and_async_process_references(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        call("spawn", "spawn_agent"),
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "SubAgentActivity",
                "id": "spawn",
                "agent_thread_id": "child",
                "kind": "spawn",
            },
        ),
        output("spawn", '{"task_name":"/root/worker"}'),
        call("run"),
        output("run", '{"session_id":123,"output":"running"}'),
        record(
            "response_item",
            type="function_call",
            name="write_stdin",
            call_id="wait",
            arguments='{"session_id":123}',
        ),
        output("wait", '{"exit_code":0,"output":"done"}'),
    )
    bundle = extract_session(source)
    assert bundle["calls"][0]["execution_records"] == ["root:L3"]
    process = [r for r in bundle["relations"] if r["type"] == "process_reference"]
    assert process == [
        {
            "type": "process_reference",
            "from": "root:L6",
            "to": "root:L7",
            "basis": "explicit_exec_session_id",
            "process_id": "123",
            "chat_id": "root",
        }
    ]
    view = show_records(bundle, filters={"call_id": "spawn"})
    assert view["child_links"][0]["status"] == "not_loaded"
    assert session_stats(bundle)["calls"] == 3  # wait is its own request, not completion of run


def test_unknown_nested_item_fields_preserved_but_hidden(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        record(
            "event_msg",
            type="item_completed",
            item={
                "type": "CommandExecution",
                "id": "x",
                "command": "echo ok",
                "future_field": "FUTURE_DATA",
            },
        ),
    )
    bundle = extract_session(source)
    assert "FUTURE_DATA" in json.dumps(bundle)
    assert "FUTURE_DATA" not in json.dumps(search_records(bundle))
    assert "FUTURE_DATA" in json.dumps(search_records(bundle, filters={"include_unparsed": True}))


def test_cli_child_discovery_and_same_chat_neighbors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    logs = tmp_path / "logs"
    parent = write_log(logs / "parent.jsonl", meta("parent"), call(), output())
    write_log(logs / "child.jsonl", meta("child", "parent"), call(), output())
    # Unrelated bodies are never loaded during discovery.
    write_log(logs / "unrelated.jsonl", meta("other"), "invalid body")
    target = tmp_path / "out.json"
    assert (
        main(
            [
                "session",
                "extract",
                str(parent),
                "--include-children",
                "--sessions-dir",
                str(logs),
                "--output",
                str(target),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["chats"] == 2
    assert (
        main(
            [
                "session",
                "show",
                str(target),
                "--record-id",
                "child:L2",
                "--chat-id",
                "child",
                "--before",
                "10",
                "--after",
                "10",
            ]
        )
        == 0
    )
    view = json.loads(capsys.readouterr().out)
    assert all(r["chat_id"] == "child" for r in view["neighbors"])
    assert main(["session", "stats", str(target), "--include-children"]) == 0
    assert json.loads(capsys.readouterr().out)["calls"] == 2


@pytest.mark.parametrize("with_marker", [False, True])
def test_inherited_parent_history_is_preserved_without_double_counting(
    tmp_path: Path, with_marker: bool
) -> None:
    child_meta = meta("child", "parent")
    entries = [
        child_meta,
        meta("parent"),
        call(),
        output(),
        record("event_msg", type="thread_settings_applied", thread_id="child"),
        call(),
        output(),
    ]
    if with_marker:
        child_meta["payload"]["subagent_history_start_ordinal"] = 4
        for ordinal, entry in enumerate(entries):
            entry["ordinal"] = ordinal
    source = write_log(tmp_path / "child.jsonl", *entries)
    bundle = extract_session(source)
    assert session_stats(bundle)["calls"] == 1
    assert session_stats(bundle)["context_only_records"] == 3
    assert bundle["calls"][0]["request_record"] == "child:L6"
    assert search_records(bundle, filters={"tool": "exec_command"})["total"] == 1
    assert (
        search_records(bundle, filters={"tool": "exec_command", "include_context": True})["total"]
        == 2
    )
    assert bundle["records"][5]["ownership_basis"] == (
        "history_start_ordinal" if with_marker else "explicit_thread_boundary"
    )


def test_copied_history_without_ownership_evidence_is_not_counted(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "child.jsonl", meta("child", "parent"), meta("parent"), call(), output()
    )
    bundle = extract_session(source)
    assert session_stats(bundle)["calls"] == 0
    assert any(w["code"] == "ownership_unresolved" for w in bundle["warnings"])
    assert len(bundle["records"]) == 4


def test_tool_namespaces_are_not_merged(tmp_path: Path) -> None:
    source = write_log(
        tmp_path / "rollout.jsonl",
        meta("root"),
        call("one", "js", namespace="browser"),
        output("one"),
        call("two", "js", namespace="node"),
        output("two"),
    )
    bundle = extract_session(source)
    assert {item["tool"] for item in session_stats(bundle)["tools"]} == {"browser.js", "node.js"}
    assert search_records(bundle, filters={"tool": "browser.js"})["total"] == 1
