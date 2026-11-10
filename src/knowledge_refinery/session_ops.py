"""Preserve local rollout evidence and build an analysis bundle without executing it."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


FORMAT = "knowledge-refinery.session-analysis"
SCHEMA_VERSION = 2
CALL_TYPES = {"function_call", "custom_tool_call"}
RESULT_TYPES = {"function_call_output", "custom_tool_call_output"}
LIFECYCLE_TYPES = {
    "task_started",
    "task_complete",
    "task_failed",
    "turn_aborted",
    "turn_started",
    "turn_complete",
    "turn_completed",
    "turn_failed",
}
EXECUTION_TYPES = {
    "CommandExecution",
    "McpToolCall",
    "FileChange",
    "Extension",
    "SubAgentActivity",
}
REASONING_TYPES = {"reasoning", "agent_reasoning", "reasoning_text", "summary_text"}
REASONING_KEYS = {"encrypted_content", "reasoning", "reasoning_content", "reasoning_text"}
COMMON_FIELDS = {"type", "id", "status", "turn_id", "internal_chat_message_metadata_passthrough"}
PAYLOAD_FIELDS = {
    "message": {"role", "content", "phase", "channel"},
    "function_call": {"name", "namespace", "arguments", "call_id"},
    "custom_tool_call": {"name", "namespace", "input", "call_id"},
    "function_call_output": {"output", "call_id"},
    "custom_tool_call_output": {"output", "call_id"},
    "user_message": {"message", "images", "local_images"},
    "agent_message": {"message", "phase"},
    "item_completed": {"item", "started_at_ms", "completed_at_ms", "thread_id"},
}

OUTER_FIELDS = {
    "session_meta": {
        "id",
        "session_id",
        "timestamp",
        "cwd",
        "cli_version",
        "source",
        "thread_source",
        "base_instructions",
        "context_window",
        "creator_account_id",
        "creator_user_id",
        "git",
        "history_mode",
        "model_provider",
        "originator",
        "runtime_workspace_roots",
        "subagent_history_start_ordinal",
        "forked_from_id",
        "parent_thread_id",
        "agent_path",
        "agent_nickname",
        "multi_agent_version",
    },
    "turn_context": {
        "turn_id",
        "root_turn_id",
        "cwd",
        "model",
        "effort",
        "summary",
        "approval_policy",
        "approvals_reviewer",
        "collaboration_mode",
        "comp_hash",
        "cyber_access_program",
        "disabled_plugin_ids",
        "file_system_sandbox_policy",
        "multi_agent_version",
        "permission_profile",
        "realtime_active",
        "sandbox_policy",
    },
    "world_state": {"full", "state"},
    "token_usage_record": {
        "response_id",
        "root_turn_id",
        "session_id",
        "thread_id",
        "thread_token_usage",
        "turn_id",
        "turn_token_usage",
        "usage",
    },
}
LIFECYCLE_FIELDS = {
    "turn_id",
    "root_turn_id",
    "started_at",
    "completed_at",
    "duration_ms",
    "last_agent_message",
    "time_to_first_token_ms",
    "model_context_window",
    "collaboration_mode_kind",
    "turn_attribution",
    "reason",
}
ITEM_FIELDS = {
    "CommandExecution": {
        "command",
        "cwd",
        "aggregated_output",
        "exit_code",
        "process_id",
        "status",
        "duration",
        "parsed_cmd",
        "source",
    },
    "McpToolCall": {"arguments", "result", "server", "tool", "status", "duration", "pluginId"},
    "FileChange": {"changes", "status", "stdout", "stderr"},
    "UserMessage": {"content", "client_id"},
    "AgentMessage": {"content", "phase"},
    "SubAgentActivity": {"agent_path", "agent_thread_id", "kind", "model", "reasoning_effort"},
    "Extension": {"action", "kind", "query", "results"},
}


def _extra_fields(value: dict[str, Any]) -> tuple[list[str], list[str]]:
    payload = value["payload"]
    subtype = string(payload.get("type"))
    known = PAYLOAD_FIELDS.get(subtype or "", OUTER_FIELDS.get(str(value.get("type"))))
    if subtype in LIFECYCLE_TYPES:
        known = LIFECYCLE_FIELDS
    extras = sorted(set(payload) - COMMON_FIELDS - known) if known is not None else []
    item = payload.get("item")
    item_extras = []
    if isinstance(item, dict) and string(item.get("type")) in ITEM_FIELDS:
        item_extras = sorted(set(item) - {"id", "type", "call_id"} - ITEM_FIELDS[item["type"]])
    return extras, item_extras


def sanitize(value: Any) -> Any:
    """Remove identifiable reasoning data recursively, including unknown envelopes."""
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if not isinstance(value, dict):
        return value
    kind = str(value.get("type", "")).lower()
    if kind in REASONING_TYPES or value.get("channel") == "analysis":
        return {"type": value.get("type"), "excluded": "reasoning"}
    return {key: sanitize(item) for key, item in value.items() if key not in REASONING_KEYS}


def string(value: Any) -> str | None:
    """Return a nonempty string without coercing malformed identifiers."""
    return value if isinstance(value, str) and value.strip() else None


def json_value(value: Any) -> Any:
    """Decode a JSON string when possible, otherwise preserve its original value."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            pass
    return value


def _signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _kind(record: dict[str, Any], payload: dict[str, Any]) -> str:
    outer, inner = string(record.get("type")), string(payload.get("type"))
    if payload.get("excluded") == "reasoning":
        return "excluded"
    if outer == "response_item":
        return _response_kind(payload)
    if outer == "event_msg":
        if inner in LIFECYCLE_TYPES:
            return "lifecycle"
        if inner in {"user_message", "agent_message"}:
            return "message"
        if inner == "item_completed":
            return _completed_kind(payload.get("item"))
        if inner == "token_count":
            return "usage"
        return "unparsed"
    return {
        "session_meta": "metadata",
        "turn_context": "context",
        "world_state": "context",
        "token_usage_record": "usage",
    }.get(str(outer), "unparsed")


def _response_kind(payload: dict[str, Any]) -> str:
    kind = string(payload.get("type"))
    if kind in CALL_TYPES and all(string(payload.get(k)) for k in ("call_id", "name")):
        key = "arguments" if kind == "function_call" else "input"
        return "call" if isinstance(payload.get(key), str) else "unparsed"
    if kind in RESULT_TYPES and string(payload.get("call_id")) and "output" in payload:
        return "result"
    if kind == "message" and string(payload.get("role")) and "content" in payload:
        return "message"
    return "unparsed"


def _completed_kind(item: Any) -> str:
    if not isinstance(item, dict):
        return "unparsed"
    if item.get("excluded") == "reasoning":
        return "excluded"
    if string(item.get("type")) in EXECUTION_TYPES:
        return "execution"
    if string(item.get("type")) in {"UserMessage", "AgentMessage"}:
        return "message"
    return "unparsed"


def _tool(payload: dict[str, Any], kind: str) -> str | None:
    if kind == "call":
        name, namespace = string(payload.get("name")), string(payload.get("namespace"))
        if name and namespace and not name.startswith(namespace + "."):
            return namespace + "." + name
        return name
    if kind != "execution":
        return None
    item = payload["item"]
    if item.get("type") == "McpToolCall":
        server, tool = string(item.get("server")), string(item.get("tool"))
        return f"{server}/{tool}" if server and tool else tool
    # These are event categories, not invented names of tool calls.
    return None


@dataclass
class _Extractor:
    records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    current_turn: str | None = None
    context_ids: set[str] = field(default_factory=set)
    inherited_context: bool = False

    def consume(self, raw: str, line: int) -> None:
        try:
            value = json.loads(raw)
        except ValueError:
            self.invalid(raw, line)
            return
        cleaned = sanitize(value)
        if not isinstance(cleaned, dict) or not isinstance(cleaned.get("payload"), dict):
            self.unknown(cleaned, raw, line, value != cleaned)
            return
        payload = cleaned["payload"]
        if cleaned.get("type") == "session_meta":
            self.set_metadata(payload, line)
        record = self.make_record(cleaned, payload, line)
        self.preserve_unparsed(record, cleaned, raw, value != cleaned)
        self.records.append(record)

    def set_metadata(self, payload: dict[str, Any], line: int) -> None:
        chat_id = string(payload.get("id"))
        if chat_id is None:
            raise ValueError(f"Missing chat ID in session metadata at line {line}")
        if self.metadata and chat_id != self.metadata["id"]:
            if chat_id not in self.context_ids:
                raise ValueError(f"Mixed chat metadata at line {line}")
            self.inherited_context = True
        if not self.metadata:
            self.metadata = payload
        identity = _child_identity(payload)
        if identity is not None:
            self.context_ids.add(identity[1])

    def make_record(
        self, value: dict[str, Any], payload: dict[str, Any], line: int
    ) -> dict[str, Any]:
        explicit_turn = string(payload.get("turn_id"))
        if explicit_turn and value.get("type") in {"turn_context", "event_msg"}:
            self.current_turn = explicit_turn
        item = payload.get("item")
        item = item if isinstance(item, dict) else {}
        kind = _kind(value, payload)
        record = {
            "line": line,
            "timestamp": value.get("timestamp"),
            "ordinal": value.get("ordinal"),
            "source_metadata": value.get("metadata"),
            "kind": kind,
            "source_type": value.get("type"),
            "source_subtype": payload.get("type"),
            "turn_id": explicit_turn or self.current_turn,
            "turn_id_basis": "explicit"
            if explicit_turn
            else ("preceding_context" if self.current_turn else None),
            "source_ids": {
                "item_id": string(item.get("id")) or string(payload.get("id")),
                "call_id": string(payload.get("call_id")) or string(item.get("call_id")),
                "thread_id": string(payload.get("thread_id")),
            },
            "tool": _tool(payload, kind),
            "data": payload,
            "unparsed": None,
        }
        if string(payload.get("type")) in LIFECYCLE_TYPES - {"task_started", "turn_started"}:
            self.current_turn = None
        return record

    def preserve_unparsed(
        self, record: dict[str, Any], value: dict[str, Any], raw: str, redacted: bool
    ) -> None:
        payload = value["payload"]
        extra, item_extra = _extra_fields(value)
        extra_top = sorted(set(value) - {"timestamp", "type", "payload", "ordinal", "metadata"})
        if record["kind"] != "unparsed" and not extra and not extra_top and not item_extra:
            return
        record["unparsed"] = {
            "reason": "unknown_or_invalid_record"
            if record["kind"] == "unparsed"
            else "additional_fields",
            "payload_fields": extra,
            "item_fields": item_extra,
            "record_fields": extra_top,
            "raw_text": json.dumps(value, ensure_ascii=False) if redacted else raw.rstrip("\n"),
            "raw_exact": not redacted,
        }
        if record["kind"] == "unparsed":
            record["data"] = None
        else:
            record["data"] = {k: v for k, v in payload.items() if k not in extra}
            if item_extra:
                record["data"]["item"] = {
                    k: v for k, v in payload["item"].items() if k not in item_extra
                }
        self.warnings.append({"code": record["unparsed"]["reason"], "line": record["line"]})

    def unknown(self, value: Any, raw: str, line: int, redacted: bool) -> None:
        record = self.make_record({}, {}, line)
        record.update(
            kind="unparsed",
            data=None,
            unparsed={
                "reason": "invalid_record_structure",
                "raw_exact": not redacted,
                "raw_text": json.dumps(value, ensure_ascii=False)
                if redacted
                else raw.rstrip("\n"),
            },
        )
        self.records.append(record)
        self.warnings.append({"code": "invalid_record_structure", "line": line})

    def invalid(self, raw: str, line: int) -> None:
        record = self.make_record({}, {}, line)
        # An invalid envelope cannot be safely field-redacted. Suppress identifiable reasoning.
        excluded = bool(re.search(r'reasoning|encrypted_content|"channel"\s*:\s*"analysis"', raw))
        record.update(
            kind="excluded" if excluded else "unparsed",
            data=None,
            unparsed={
                "reason": "invalid_json",
                "raw_text": None if excluded else raw.rstrip("\n"),
                "raw_exact": not excluded,
            },
        )
        self.records.append(record)
        self.warnings.append({"code": "invalid_json", "line": line})


def read_rollout(path: Path) -> dict[str, Any]:
    """Read a stable file, preserving full non-reasoning evidence and source positions."""
    path = path.expanduser().resolve()
    extractor = _Extractor()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        before = _signature(os.fstat(source.fileno()))
        for line, raw in enumerate(source, 1):
            digest.update(raw)
            extractor.consume(raw.decode("utf-8"), line)
        after = _signature(os.fstat(source.fileno()))
    if before != after or after != _signature(path.stat()):
        raise ValueError("Session file changed while reading; retry a stable snapshot")
    if not extractor.metadata:
        raise ValueError("Missing session metadata; expected a Codex rollout JSONL")
    chat_id = extractor.metadata["id"]
    _mark_ownership(extractor, chat_id)
    for record in extractor.records:
        record.update(record_id=f"{chat_id}:L{record['line']}", chat_id=chat_id)
    for warning in extractor.warnings:
        warning.update(chat_id=chat_id, record_id=f"{chat_id}:L{warning['line']}")
    metadata = extractor.metadata
    source_info = metadata.get("source")
    spawn = source_info.get("subagent", {}) if isinstance(source_info, dict) else {}
    spawn = spawn.get("thread_spawn", {}) if isinstance(spawn, dict) else {}
    spawn = spawn if isinstance(spawn, dict) else {}
    return {
        "chat": {
            "chat_id": chat_id,
            "session_id": string(metadata.get("session_id")),
            "parent_chat_id": string(spawn.get("parent_thread_id"))
            or string(metadata.get("parent_thread_id")),
            "agent_path": string(spawn.get("agent_path")) or string(metadata.get("agent_path")),
            "cli_version": metadata.get("cli_version"),
            "source": {
                "path": str(path),
                "sha256": digest.hexdigest(),
                "bytes": after[2],
                "lines": len(extractor.records),
            },
        },
        "records": extractor.records,
        "warnings": extractor.warnings,
    }


def _mark_ownership(extractor: _Extractor, chat_id: str) -> None:
    marker = extractor.metadata.get("subagent_history_start_ordinal")
    marker = marker if type(marker) is int and marker >= 0 else None
    boundary = next(
        (r["line"] for r in extractor.records if r["source_ids"].get("thread_id") == chat_id), None
    )
    has_context = (
        extractor.inherited_context
        or marker is not None
        or bool(string(extractor.metadata.get("forked_from_id")))
    )
    for record in extractor.records:
        owned = True
        basis = "single_chat"
        if has_context and record["line"] != 1:
            owned, basis = _owns_record(record, marker, boundary)
        record["ownership"] = "local" if owned else "context_only"
        record["ownership_basis"] = basis
        if owned and record["kind"] == "metadata" and record["data"].get("id") != chat_id:
            raise ValueError("Foreign metadata after local execution boundary")
    if has_context:
        local_records = [
            r for r in extractor.records if r["line"] != 1 and r["ownership"] == "local"
        ]
        extractor.warnings.append(
            {
                "code": "inherited_context" if local_records else "ownership_unresolved",
                "line": local_records[0]["line"] if local_records else 1,
            }
        )


def _owns_record(
    record: dict[str, Any], marker: int | None, boundary: int | None
) -> tuple[bool, str]:
    if marker is not None and type(record["ordinal"]) is int:
        return record["ordinal"] >= marker, "history_start_ordinal"
    if boundary is not None:
        return record["line"] >= boundary, "explicit_thread_boundary"
    return False, "unknown"


def _metadata(path: Path) -> dict[str, Any] | None:
    # Discovery reads only the first record; it never searches unrelated conversation bodies.
    try:
        with path.open(encoding="utf-8") as source:
            value = json.loads(source.readline())
        if isinstance(value, dict) and value.get("type") == "session_meta":
            payload = value.get("payload")
            return payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        pass
    return None


def _child_identity(meta: dict[str, Any]) -> tuple[str, str] | None:
    source = meta.get("source")
    spawn: Any = source.get("subagent") if isinstance(source, dict) else None
    spawn = spawn.get("thread_spawn") if isinstance(spawn, dict) else None
    parent = string(spawn.get("parent_thread_id")) if isinstance(spawn, dict) else None
    parent = parent or string(meta.get("parent_thread_id"))
    chat = string(meta.get("id"))
    return (chat, parent) if chat and parent else None


def discover_children(roots: list[Path], parent_id: str) -> list[Path]:
    """Find descendant files by explicit parent metadata, without reading their bodies."""
    candidates: list[tuple[Path, str, str]] = []
    for root in roots:
        if not root.expanduser().is_dir():
            continue
        for path in sorted(root.expanduser().rglob("*.jsonl")):
            meta = _metadata(path)
            if meta is None:
                continue
            identity = _child_identity(meta)
            if identity is not None:
                candidates.append((path, *identity))
    selected: set[Path] = set()
    known = {parent_id}
    changed = True
    while changed:
        changed = False
        for path, chat, parent in candidates:
            if parent in known and chat != parent_id and path not in selected:
                selected.add(path)
                known.add(chat)
                changed = True
    return sorted(selected)


def extract_session(path: Path, *, discovery_roots: list[Path] | None = None) -> dict[str, Any]:
    """Build an analysis bundle from a root chat and descendants found in discovery roots."""
    from knowledge_refinery.session_links import build_links

    root = read_rollout(path)
    root_id = root["chat"]["chat_id"]
    paths = discover_children(discovery_roots, root_id) if discovery_roots is not None else []
    loaded = {root_id: root}
    warnings = []
    for child_path in dict.fromkeys(p.expanduser().resolve() for p in paths):
        child = read_rollout(child_path)
        child_id = child["chat"]["chat_id"]
        if child_id in loaded:
            if child["chat"]["source"]["sha256"] != loaded[child_id]["chat"]["source"]["sha256"]:
                raise ValueError(f"Conflicting rollout files for chat {child_id}")
            warnings.append({"code": "duplicate_source", "chat_id": child_id})
        else:
            loaded[child_id] = child
    _validate_descendants(loaded, root_id)
    bundle = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "root_chat_id": root_id,
        "chats": [item["chat"] for item in loaded.values()],
        "records": [record for item in loaded.values() for record in item["records"]],
        "warnings": warnings + [w for item in loaded.values() for w in item["warnings"]],
    }
    build_links(bundle)
    return bundle


def _validate_descendants(loaded: dict[str, Any], root_id: str) -> None:
    for chat_id in loaded:
        current, visited = chat_id, set()
        while current != root_id:
            if current in visited or current not in loaded:
                raise ValueError(f"Chat {chat_id} is not a verified descendant of the root")
            visited.add(current)
            current = loaded[current]["chat"]["parent_chat_id"]
