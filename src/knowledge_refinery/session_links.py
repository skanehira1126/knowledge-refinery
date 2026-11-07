"""Derive conservative identity links, skill references, and subagent relationships."""

from __future__ import annotations

from collections import defaultdict
import json
import re
from typing import Any

from knowledge_refinery.session_ops import json_value
from knowledge_refinery.session_ops import string


NAMED_SKILL = re.compile(r"\$([a-z][a-z0-9_-]*(?::[a-z][a-z0-9_-]*)?)\b")
SKILL_PATH = re.compile(r"""[/\\]([^/\\\s"']+)[/\\]SKILL\.md""")
SKILL_BODY = re.compile(r"<skill>.*?<name>\s*([^<\s]+)\s*</name>.*?</skill>", re.S)
CATALOG = re.compile(r"^-\s+([a-z][a-z0-9_:-]*):.*\(file:", re.M)


def content_text(value: Any) -> str:
    """Collect textual message blocks without exposing non-text attachments."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(content_text(item) for item in value)
    if isinstance(value, dict):
        return str(value.get("text", value.get("refusal", "")))
    return ""


def record_text(record: dict[str, Any]) -> str:
    """Return known evidence text for search; unparsed records are intentionally excluded."""
    data = record.get("data") or {}
    kind = record["kind"]
    if kind == "call":
        return str(data.get("arguments", data.get("input", "")))
    if kind == "result":
        output = data.get("output")
        return output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    if kind == "message":
        item = data.get("item", data)
        return content_text(item.get("content", item.get("message", "")))
    if kind == "execution":
        item = data["item"]
        return json.dumps(
            {
                k: item[k]
                for k in (
                    "command",
                    "arguments",
                    "aggregated_output",
                    "result",
                    "stdout",
                    "stderr",
                )
                if k in item
            },
            ensure_ascii=False,
        )
    return ""


def _duplicate_key(record: dict[str, Any]) -> tuple[str, ...] | None:
    item_id = record["source_ids"]["item_id"]
    if not item_id or record["kind"] not in {"call", "result", "message", "execution"}:
        return None
    data = record["data"]
    if record["kind"] == "message":
        item = data.get("item", data)
        role = item.get("role") or {"UserMessage": "user", "AgentMessage": "assistant"}.get(
            item.get("type")
        )
        payload = json.dumps([role, item.get("phase"), record_text(record)], ensure_ascii=False)
    else:
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return (
        record["chat_id"],
        item_id,
        record["kind"],
        record["turn_id"] or "",
        record["ownership"],
        payload,
        json.dumps(record["unparsed"], sort_keys=True, ensure_ascii=False),
    )


def _duplicates(records: list[dict[str, Any]], relations: list[dict[str, Any]]) -> None:
    seen: dict[tuple[str, ...], str] = {}
    for record in records:
        record["duplicate_of"] = None
        key = _duplicate_key(record)
        if key is None:
            continue
        if key in seen:
            record["duplicate_of"] = seen[key]
            relations.append(
                {
                    "type": "duplicate",
                    "from": record["record_id"],
                    "to": seen[key],
                    "basis": "same_item_id_and_content",
                }
            )
        else:
            seen[key] = record["record_id"]


def _calls(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": record["record_id"] + ":call",
            "chat_id": record["chat_id"],
            "call_id": record["source_ids"]["call_id"],
            "tool": record["tool"],
            "request_record": record["record_id"],
            "result_records": [],
            "execution_records": [],
            "link_status": "missing_result",
        }
        for record in records
        if record["kind"] == "call"
        and not record["duplicate_of"]
        and record["ownership"] == "local"
    ]


def _link_results(
    records: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    by_call: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_item: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    record_map = {r["record_id"]: r for r in records}
    for call in calls:
        by_call[call["chat_id"], call["call_id"]].append(call)
        request = record_map[call["request_record"]]
        if item_id := request["source_ids"]["item_id"]:
            by_item[call["chat_id"], item_id].append(call)
    for record in records:
        if (
            record["duplicate_of"]
            or record["ownership"] != "local"
            or record["kind"] not in {"result", "execution"}
        ):
            continue
        candidates = _candidates(record, by_call, by_item)
        if len(candidates) == 1:
            call = candidates[0]
            if record["kind"] == "result" and not _compatible(record_map, record, call):
                candidates = []
            else:
                field = "result_records" if record["kind"] == "result" else "execution_records"
                call[field].append(record["record_id"])
                relations.append(
                    {
                        "type": "result" if record["kind"] == "result" else "execution",
                        "from": call["request_record"],
                        "to": record["record_id"],
                        "basis": "explicit_identifier",
                    }
                )
                continue
        warnings.append(
            {
                "code": "ambiguous_link" if candidates else "unmatched_" + record["kind"],
                "chat_id": record["chat_id"],
                "record_id": record["record_id"],
                "candidate_calls": [c["id"] for c in candidates],
            }
        )
    for call in calls:
        ambiguous = len(by_call[call["chat_id"], call["call_id"]]) > 1
        call["link_status"] = (
            "ambiguous"
            if ambiguous
            else ("matched" if call["result_records"] else "missing_result")
        )
        if call["link_status"] != "matched":
            warnings.append(
                {
                    "code": call["link_status"],
                    "chat_id": call["chat_id"],
                    "record_id": call["request_record"],
                }
            )


def _candidates(
    record: dict[str, Any], by_call: dict[Any, Any], by_item: dict[Any, Any]
) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    chat, ids = record["chat_id"], record["source_ids"]
    for call in by_call.get((chat, ids["call_id"]), []):
        found[call["id"]] = call
    if record["kind"] == "execution":
        for call in by_item.get((chat, ids["item_id"]), []) + by_call.get(
            (chat, ids["item_id"]), []
        ):
            found[call["id"]] = call
    return list(found.values())


def _compatible(record_map: dict[str, Any], result: dict[str, Any], call: dict[str, Any]) -> bool:
    request = record_map[call["request_record"]]
    return (
        request["source_subtype"] + "_output" == result["source_subtype"]
        and result["line"] > request["line"]
    )


def _skill_mentions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mentions = []
    for record in records:
        if record["duplicate_of"] or record["kind"] not in {"call", "message", "execution"}:
            continue
        text = record_text(record)
        if record["kind"] == "execution":
            item = record["data"]["item"]
            text = json.dumps({k: item[k] for k in ("command", "arguments") if k in item})
        candidates = {(match.group(1), "named_reference") for match in NAMED_SKILL.finditer(text)}
        candidates.update((m.group(1), "body_provided") for m in SKILL_BODY.finditer(text))
        candidates.update((m.group(1), "catalog_entry") for m in CATALOG.finditer(text))
        catalog = bool(CATALOG.search(text))
        path_kind = (
            "read_candidate"
            if record["kind"] in {"call", "execution"}
            else ("catalog_entry" if catalog else "path_reference")
        )
        candidates.update((m.group(1), path_kind) for m in SKILL_PATH.finditer(text))
        for name, kind in sorted(candidates):
            plugin, _, short = name.rpartition(":")
            mentions.append(
                {
                    "chat_id": record["chat_id"],
                    "record_id": record["record_id"],
                    "skill": short or name,
                    "qualified_name": name,
                    "plugin": plugin or None,
                    "kind": kind,
                }
            )
    return mentions


def _spawn_identifiers(call: dict[str, Any], records: dict[str, Any]) -> set[str]:
    identifiers: set[str] = set()
    for rid in call["result_records"]:
        value = json_value(records[rid]["data"].get("output"))
        if isinstance(value, dict):
            identifiers.update(v for k in ("task_name", "agent_id") if (v := string(value.get(k))))
    return identifiers


def _child_links(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    records = {record["record_id"]: record for record in bundle["records"]}
    links = []
    connected: set[str] = set()
    for call in bundle["calls"]:
        if call["tool"].rsplit(".", 1)[-1] != "spawn_agent":
            continue
        identifiers = _spawn_identifiers(call, records)
        children = [
            chat
            for chat in bundle["chats"]
            if (
                chat["parent_chat_id"] == call["chat_id"]
                and (chat["chat_id"] in identifiers or chat["agent_path"] in identifiers)
            )
        ]
        child = children[0] if len(children) == 1 else None
        if child:
            connected.add(child["chat_id"])
        links.append(
            {
                "parent_chat_id": call["chat_id"],
                "child_chat_id": child["chat_id"] if child else None,
                "spawn_call_id": call["id"],
                "agent_identifiers": sorted(identifiers),
                "status": "matched" if child else ("ambiguous" if children else "not_loaded"),
                "candidate_chat_ids": [c["chat_id"] for c in children]
                if len(children) > 1
                else [],
            }
        )
    for chat in bundle["chats"]:
        if chat["chat_id"] != bundle["root_chat_id"] and chat["chat_id"] not in connected:
            links.append(
                {
                    "parent_chat_id": chat["parent_chat_id"],
                    "child_chat_id": chat["chat_id"],
                    "spawn_call_id": None,
                    "agent_identifiers": [chat["agent_path"]] if chat["agent_path"] else [],
                    "status": "metadata_only",
                    "candidate_chat_ids": [],
                }
            )
    return links


def _process_links(
    records: list[dict[str, Any]], calls: list[dict[str, Any]], relations: list[dict[str, Any]]
) -> None:
    by_record = {r["record_id"]: r for r in records}
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for call in calls:
        name = call["tool"].rsplit(".", 1)[-1]
        if name not in {"exec_command", "write_stdin"}:
            continue
        for rid in [call["request_record"], *call["result_records"]]:
            record = by_record[rid]
            data = record["data"]
            value = json_value(data.get("arguments", data.get("output")))
            if isinstance(value, dict) and isinstance(value.get("session_id"), str | int):
                groups[(call["chat_id"], str(value["session_id"]))].append(rid)
    for (chat_id, process_id), ids in groups.items():
        for rid in ids[1:]:
            relations.append(
                {
                    "type": "process_reference",
                    "from": ids[0],
                    "to": rid,
                    "basis": "explicit_exec_session_id",
                    "process_id": process_id,
                    "chat_id": chat_id,
                }
            )


def build_links(bundle: dict[str, Any]) -> None:
    """Populate deterministic links without guessing relationships from text similarity."""
    records = bundle["records"]
    relations: list[dict[str, Any]] = []
    _duplicates(records, relations)
    calls = _calls(records)
    _link_results(records, calls, relations, bundle["warnings"])
    _process_links(records, calls, relations)
    bundle.update(calls=calls, relations=relations, skill_mentions=_skill_mentions(records))
    bundle["child_links"] = _child_links(bundle)
