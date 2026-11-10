"""Local session extraction, bounded evidence queries, and descriptive counts."""

import argparse
import json
import os
from pathlib import Path

from knowledge_refinery.session_catalog import list_sessions
from knowledge_refinery.session_ops import extract_session
from knowledge_refinery.session_query import KINDS
from knowledge_refinery.session_query import load_analysis
from knowledge_refinery.session_query import search_records
from knowledge_refinery.session_query import session_stats
from knowledge_refinery.session_query import show_records


def configure_session_parser(parser: argparse.ArgumentParser) -> None:
    """Register local session commands independently of vault and MCP configuration."""
    commands = parser.add_subparsers(required=True)
    listing = commands.add_parser("list", help="List root chats by log modification time")
    listing.add_argument(
        "--project",
        type=Path,
        default=Path("."),
        help="registered project working directory (default: current directory)",
    )
    listing.add_argument(
        "--updated-since",
        help="inclusive lower bound: YYYY-MM-DD (UTC) or ISO timestamp with timezone",
    )
    listing.add_argument(
        "--updated-before",
        help="exclusive upper bound: YYYY-MM-DD (UTC) or ISO timestamp with timezone",
    )
    listing.add_argument(
        "--sessions-dir",
        type=Path,
        action="append",
        help="log directory (repeatable; replaces default CODEX_HOME/sessions)",
    )
    listing.add_argument(
        "--limit", type=int, default=20, help="maximum chats to return (default: 20)"
    )
    listing.add_argument("--offset", type=int, default=0, help="chats to skip (default: 0)")
    listing.set_defaults(handler=run_session_list)

    extract = commands.add_parser("extract", help="Save full rollout evidence as analysis JSON")
    extract.add_argument("path", type=Path, help="root chat's local rollout JSONL")
    extract.add_argument(
        "--output", type=Path, required=True, help="new private analysis JSON file"
    )
    extract.add_argument(
        "--exclude-children", action="store_true", help="extract only the root chat"
    )
    extract.add_argument(
        "--sessions-dir",
        type=Path,
        action="append",
        help="discovery root (repeatable; defaults to CODEX_HOME/sessions)",
    )
    extract.set_defaults(handler=run_session_extract)

    search = commands.add_parser("search", help="Find records in saved analysis JSON")
    search.add_argument("path", type=Path, help="saved analysis JSON")
    search.add_argument("--chat-id", help="scope root (defaults to the extracted root chat)")
    search.add_argument(
        "--exclude-children", action="store_true", help="query only the selected chat"
    )
    search_ids = search.add_mutually_exclusive_group(required=False)
    search_ids.add_argument("--record-id")
    search_ids.add_argument("--call-id")
    search_ids.add_argument("--item-id")
    search_ids.add_argument("--turn-id")
    search.add_argument("--tool", help="exact call name or server/tool for an MCP execution event")
    search.add_argument("--skill", help="exact skill name or plugin:skill")
    search.add_argument(
        "--skill-kind",
        choices=[
            "named_reference",
            "body_provided",
            "catalog_entry",
            "read_candidate",
            "path_reference",
        ],
    )
    search.add_argument("--kind", choices=sorted(KINDS))
    search.add_argument("--text", help="literal, case-sensitive search in known evidence text")
    search.add_argument(
        "--include-unparsed", action="store_true", help="explicitly expose/search unparsed text"
    )
    search.add_argument("--include-duplicates", action="store_true")
    search.add_argument(
        "--include-context",
        action="store_true",
        help="include inherited or unowned context records",
    )
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--offset", type=int, default=0)
    search.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="preview limit per record; does not alter saved data",
    )
    search.set_defaults(handler=run_session_query, operation="search")

    show = commands.add_parser(
        "show", help="Show identified records, neighbors, and related evidence"
    )
    show.add_argument("path", type=Path, help="saved analysis JSON")
    show.add_argument("--chat-id", help="scope root (defaults to the extracted root chat)")
    show.add_argument(
        "--exclude-children", action="store_true", help="query only the selected chat"
    )
    show_ids = show.add_mutually_exclusive_group(required=True)
    show_ids.add_argument("--record-id")
    show_ids.add_argument("--call-id")
    show_ids.add_argument("--item-id")
    show_ids.add_argument("--turn-id")
    show.add_argument("--tool", help="exact call name or server/tool for an MCP execution event")
    show.add_argument("--skill", help="exact skill name or plugin:skill")
    show.add_argument(
        "--skill-kind",
        choices=[
            "named_reference",
            "body_provided",
            "catalog_entry",
            "read_candidate",
            "path_reference",
        ],
    )
    show.add_argument("--kind", choices=sorted(KINDS))
    show.add_argument("--text", help="literal, case-sensitive search in known evidence text")
    show.add_argument(
        "--include-unparsed", action="store_true", help="explicitly expose/search unparsed text"
    )
    show.add_argument("--include-duplicates", action="store_true")
    show.add_argument(
        "--include-context",
        action="store_true",
        help="include inherited or unowned context records",
    )
    show.add_argument("--limit", type=int, default=20)
    show.add_argument("--offset", type=int, default=0)
    show.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="preview limit per record; does not alter saved data",
    )
    show.add_argument("--before", type=int, default=0)
    show.add_argument("--after", type=int, default=0)
    show.set_defaults(handler=run_session_query, operation="show")

    stats = commands.add_parser("stats", help="Count calls and evidence in saved analysis JSON")
    stats.add_argument("path", type=Path, help="saved analysis JSON")
    stats.add_argument("--chat-id", help="scope root (defaults to the extracted root chat)")
    stats.add_argument(
        "--exclude-children", action="store_true", help="query only the selected chat"
    )
    stats.set_defaults(handler=run_session_query, operation="stats")


def run_session_list(args: argparse.Namespace) -> int:
    """Print a bounded metadata-only inventory of root chat logs."""
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    result = list_sessions(
        args.sessions_dir or [home / "sessions"],
        project=args.project,
        updated_since=args.updated_since,
        updated_before=args.updated_before,
        limit=args.limit,
        offset=args.offset,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run_session_extract(args: argparse.Namespace) -> int:
    """Save full evidence exclusively and print a compact receipt, not the raw transcript."""
    if args.sessions_dir and args.exclude_children:
        raise ValueError("--sessions-dir cannot be combined with --exclude-children")
    roots = None
    if not args.exclude_children:
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        roots = args.sessions_dir or [home / "sessions"]
    result = extract_session(args.path, discovery_roots=roots)
    output_path = args.output.expanduser()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(text)
    print(
        json.dumps(
            {
                "output": str(output_path.resolve()),
                "schema_version": result["schema_version"],
                "root_chat_id": result["root_chat_id"],
                "chats": len(result["chats"]),
                "records": len(result["records"]),
                "calls": len(result["calls"]),
                "warnings": len(result["warnings"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


def run_session_query(args: argparse.Namespace) -> int:
    """Dispatch read-only query views over a validated analysis bundle."""
    bundle = load_analysis(args.path)
    scope = {"chat_id": args.chat_id, "include_children": not args.exclude_children}
    if args.operation == "stats":
        result = session_stats(bundle, **scope)
    else:
        if args.skill_kind and not args.skill:
            raise ValueError("--skill-kind requires --skill")
        filters = {
            key: getattr(args, key)
            for key in (
                "record_id",
                "call_id",
                "item_id",
                "turn_id",
                "tool",
                "skill",
                "skill_kind",
                "kind",
                "text",
                "include_unparsed",
                "include_duplicates",
                "include_context",
            )
        }
        options = dict(
            **scope,
            filters=filters,
            limit=args.limit,
            offset=args.offset,
            max_chars=args.max_chars,
        )
        if args.operation == "show":
            result = show_records(bundle, before=args.before, after=args.after, **options)
        else:
            result = search_records(bundle, **options)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
