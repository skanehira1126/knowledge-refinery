"""Bounded read-only views and counts over saved session-analysis JSON."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from knowledge_refinery.session_links import record_text
from knowledge_refinery.session_ops import FORMAT
from knowledge_refinery.session_ops import SCHEMA_VERSION


KINDS = {
    "metadata",
    "context",
    "message",
    "call",
    "result",
    "execution",
    "lifecycle",
    "usage",
    "unparsed",
    "excluded",
}


def load_analysis(path: Path) -> dict[str, Any]:
    """Load the supported bundle version and reject structurally invalid query inputs."""
    value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != FORMAT:
        raise ValueError("Expected a Knowledge Refinery session-analysis JSON")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported analysis schema; re-extract with schema {SCHEMA_VERSION}")
    for key in (
        "chats",
        "records",
        "calls",
        "relations",
        "skill_mentions",
        "warnings",
        "child_links",
    ):
        if not isinstance(value.get(key), list) or not all(
            isinstance(v, dict) for v in value[key]
        ):
            raise ValueError(f"Invalid analysis collection: {key}")
    try:
        _validate(value)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Invalid analysis structure; re-extract the source") from error
    return value


def _validate(bundle: dict[str, Any]) -> None:
    chats = {c["chat_id"] for c in bundle["chats"]}
    if bundle["root_chat_id"] not in chats or len(chats) != len(bundle["chats"]):
        raise ValueError("Missing root or duplicate chats")
    records = {r["record_id"]: r for r in bundle["records"]}
    if len(records) != len(bundle["records"]):
        raise ValueError("Duplicate record IDs")
    _validate_records(records, chats)
    for call in bundle["calls"]:
        if call["chat_id"] not in chats or call["request_record"] not in records:
            raise ValueError("Dangling call reference")
        if not all(rid in records for rid in call["result_records"] + call["execution_records"]):
            raise ValueError("Dangling result reference")
    for link in bundle["relations"]:
        if link["from"] not in records or link["to"] not in records:
            raise ValueError("Dangling relationship")
    for mention in bundle["skill_mentions"]:
        if mention["record_id"] not in records:
            raise ValueError("Dangling skill reference")


def _validate_records(records: dict[str, Any], chats: set[str]) -> None:
    for record in records.values():
        if record["chat_id"] not in chats or record["kind"] not in KINDS:
            raise ValueError("Invalid record chat or kind")
        if not isinstance(record["line"], int) or not isinstance(record["source_ids"], dict):
            raise ValueError("Invalid record position or identifiers")
        if record["data"] is not None and not isinstance(record["data"], dict):
            raise ValueError("Invalid record data")
        if record["duplicate_of"] is not None and record["duplicate_of"] not in records:
            raise ValueError("Dangling duplicate reference")


def selected_chats(
    bundle: dict[str, Any], chat_id: str | None = None, include_children: bool = True
) -> set[str]:
    """Select one chat or its loaded descendants using explicit parent metadata."""
    selected = {chat_id or bundle["root_chat_id"]}
    known = {chat["chat_id"] for chat in bundle["chats"]}
    if not selected <= known:
        raise ValueError("Chat ID is not present in this analysis")
    if include_children:
        previous: set[str] = set()
        while previous != selected:
            previous = selected.copy()
            selected.update(
                c["chat_id"] for c in bundle["chats"] if c["parent_chat_id"] in selected
            )
    return selected


def _preview(
    record: dict[str, Any], max_chars: int, include_unparsed: bool, warnings: list[dict[str, Any]]
) -> dict[str, Any]:
    result = {
        k: record[k]
        for k in (
            "record_id",
            "chat_id",
            "line",
            "timestamp",
            "kind",
            "ownership",
            "ownership_basis",
            "ordinal",
            "source_type",
            "source_subtype",
            "turn_id",
            "turn_id_basis",
            "source_ids",
            "tool",
            "duplicate_of",
        )
    }
    content = record.get("data")
    if record.get("source_metadata") is not None:
        content = {"payload": content, "metadata": record["source_metadata"]}
    result["warnings"] = [w for w in warnings if w.get("record_id") == record["record_id"]]
    if include_unparsed and record.get("unparsed"):
        content = {"data": content, "unparsed": record["unparsed"]}
    text = json.dumps(content, ensure_ascii=False) if content is not None else ""
    result.update(
        preview=text[:max_chars],
        preview_chars=len(text),
        truncated=len(text) > max_chars,
        has_unparsed=record.get("unparsed") is not None,
    )
    return result


def _matches(record: dict[str, Any], filters: dict[str, Any], skill_ids: set[str]) -> bool:
    mapping = {
        "record_id": record["record_id"],
        "call_id": record["source_ids"].get("call_id"),
        "item_id": record["source_ids"].get("item_id"),
        "turn_id": record["turn_id"],
        "tool": record["tool"],
        "kind": record["kind"],
    }
    if any(filters.get(k) is not None and filters[k] != value for k, value in mapping.items()):
        return False
    if filters.get("skill") and record["record_id"] not in skill_ids:
        return False
    if filters.get("text"):
        text = record_text(record)
        if filters.get("include_unparsed") and record.get("unparsed"):
            text += "\n" + (record["unparsed"].get("raw_text") or "")
        if filters["text"] not in text:
            return False
    return True


def search_records(
    bundle: dict[str, Any],
    *,
    chat_id: str | None = None,
    include_children: bool = True,
    filters: dict[str, Any] | None = None,
    limit: int = 20,
    offset: int = 0,
    max_chars: int = 2000,
) -> dict[str, Any]:
    """Find evidence by exact identities and bounded previews; never search reasoning."""
    if limit <= 0 or offset < 0 or max_chars <= 0:
        raise ValueError("limit/max-chars must be positive and offset nonnegative")
    filters = filters or {}
    chats = selected_chats(bundle, chat_id, include_children)
    skill_ids = {
        m["record_id"]
        for m in bundle["skill_mentions"]
        if (
            filters.get("skill") in {m["skill"], m["qualified_name"]}
            and (not filters.get("skill_kind") or filters["skill_kind"] == m["kind"])
        )
    }
    matches = [
        r
        for r in bundle["records"]
        if (
            r["chat_id"] in chats
            and (filters.get("include_context") or r["ownership"] == "local")
            and (filters.get("include_duplicates") or not r["duplicate_of"])
            and _matches(r, filters, skill_ids)
        )
    ]
    page = matches[offset : offset + limit]
    result = {
        "chat_ids": sorted(chats),
        "total": len(matches),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(matches) else None,
        "records": [
            _preview(r, max_chars, bool(filters.get("include_unparsed")), bundle["warnings"])
            for r in page
        ],
    }
    if filters.get("skill"):
        page_ids = {r["record_id"] for r in page}
        result["skill_matches"] = [
            m
            for m in bundle["skill_mentions"]
            if (
                m["record_id"] in page_ids
                and filters["skill"] in {m["skill"], m["qualified_name"]}
                and (not filters.get("skill_kind") or filters["skill_kind"] == m["kind"])
            )
        ]
    return result


def show_records(
    bundle: dict[str, Any], *, before: int = 0, after: int = 0, **options: Any
) -> dict[str, Any]:
    """Show selected evidence, same-chat neighbors, and separately linked records."""
    if before < 0 or after < 0 or before > 100 or after > 100:
        raise ValueError("before/after must be between 0 and 100")
    result = search_records(bundle, **options)
    ids = {r["record_id"] for r in result["records"]}
    related: set[str] = set()
    for relation in bundle["relations"]:
        if relation["from"] in ids:
            related.add(relation["to"])
        if relation["to"] in ids:
            related.add(relation["from"])
    neighbors: set[str] = set()
    for chat_id in result["chat_ids"]:
        records = [r for r in bundle["records"] if r["chat_id"] == chat_id]
        for index, record in enumerate(records):
            if record["record_id"] in ids:
                neighbors.update(
                    r["record_id"] for r in records[max(0, index - before) : index + after + 1]
                )
    max_chars = options.get("max_chars", 2000)
    unparsed = bool((options.get("filters") or {}).get("include_unparsed"))
    result["neighbors"] = [
        _preview(r, max_chars, unparsed, bundle["warnings"])
        for r in bundle["records"]
        if r["record_id"] in neighbors - ids
    ]
    linked = [r for r in bundle["records"] if r["record_id"] in related - ids]
    limit = options.get("limit", 20)
    result["related_total"] = len(linked)
    result["related"] = [
        _preview(r, max_chars, unparsed, bundle["warnings"]) for r in linked[:limit]
    ]
    result["related_truncated"] = len(linked) > limit
    call_ids = {
        c["id"]
        for c in bundle["calls"]
        if (c["request_record"] in ids or ids.intersection(c["result_records"]))
    }
    result["child_links"] = [
        link for link in bundle["child_links"] if link["spawn_call_id"] in call_ids
    ]
    return result


def session_stats(
    bundle: dict[str, Any], *, chat_id: str | None = None, include_children: bool = True
) -> dict[str, Any]:
    """Count canonical requests, keeping execution evidence and skill references separate."""
    chats = selected_chats(bundle, chat_id, include_children)
    calls = [c for c in bundle["calls"] if c["chat_id"] in chats]
    records = [r for r in bundle["records"] if r["chat_id"] in chats]
    tools = []
    for name in sorted({call["tool"] for call in calls}):
        group = [call for call in calls if call["tool"] == name]
        tools.append(
            {
                "tool": name,
                "calls": len(group),
                "with_result": sum(bool(c["result_records"]) for c in group),
                "missing_result": sum(not c["result_records"] for c in group),
                "ambiguous": sum(c["link_status"] == "ambiguous" for c in group),
            }
        )
    linked = {rid for call in calls for rid in call["execution_records"]}
    events = [
        r
        for r in records
        if r["kind"] == "execution" and not r["duplicate_of"] and r["ownership"] == "local"
    ]
    local_ids = {r["record_id"] for r in records if r["ownership"] == "local"}
    mentions = Counter(
        (m["qualified_name"], m["kind"])
        for m in bundle["skill_mentions"]
        if m["chat_id"] in chats and m["record_id"] in local_ids
    )
    return {
        "chat_ids": sorted(chats),
        "calls": len(calls),
        "tools": tools,
        "by_chat": [
            {"chat_id": chat, "calls": sum(c["chat_id"] == chat for c in calls)}
            for chat in sorted(chats)
        ],
        "records": len(records),
        "duplicate_records": sum(bool(r["duplicate_of"]) for r in records),
        "execution_events": len(events),
        "context_only_records": sum(r["ownership"] == "context_only" for r in records),
        "unlinked_execution_events": sum(r["record_id"] not in linked for r in events),
        "unparsed_records": sum(r["unparsed"] is not None for r in records),
        "skill_references": [
            {"skill": name, "kind": kind, "records": count}
            for (name, kind), count in sorted(mentions.items())
        ],
        "child_links": [link for link in bundle["child_links"] if link["parent_chat_id"] in chats],
        "warning_count": sum(w.get("chat_id") in chats for w in bundle["warnings"]),
        "warnings_by_code": dict(
            Counter(w["code"] for w in bundle["warnings"] if w.get("chat_id") in chats)
        ),
        "counting_unit": "canonical request records; execution events and retries are not merged",
    }
