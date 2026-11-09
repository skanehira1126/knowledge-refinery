"""Local session extraction, bounded evidence queries, and descriptive counts."""

import argparse
import json
import os
from pathlib import Path

from knowledge_refinery.session_ops import extract_session
from knowledge_refinery.session_query import KINDS
from knowledge_refinery.session_query import load_analysis
from knowledge_refinery.session_query import search_records
from knowledge_refinery.session_query import session_stats
from knowledge_refinery.session_query import show_records


def configure_session_parser(parser: argparse.ArgumentParser) -> None:
    """Register local session commands independently of vault and MCP configuration."""
    commands = parser.add_subparsers(required=True)
    extract = commands.add_parser("extract", help="Save full rollout evidence as analysis JSON")
    extract.add_argument("path", type=Path, help="root chat's local rollout JSONL")
    extract.add_argument(
        "--output", type=Path, required=True, help="new private analysis JSON file"
    )
    extract.add_argument(
        "--child", type=Path, action="append", default=[], help="explicit descendant rollout"
    )
    extract.add_argument(
        "--include-children", action="store_true", help="discover descendant metadata"
    )
    extract.add_argument(
        "--sessions-dir",
        type=Path,
        action="append",
        help="discovery root (repeatable; defaults to CODEX_HOME/sessions)",
    )
    extract.set_defaults(handler=run_session_extract)
    for name in ("search", "show", "stats"):
        command = commands.add_parser(name, help=f"{name.title()} saved analysis evidence")
        command.add_argument("path", type=Path, help="saved analysis JSON")
        command.add_argument("--chat-id", help="chat to query (defaults to root chat)")
        command.add_argument(
            "--include-children", action="store_true", help="include loaded descendants"
        )
        command.set_defaults(handler=run_session_query, operation=name)
        if name != "stats":
            _query_options(command, show=name == "show")


def _query_options(parser: argparse.ArgumentParser, *, show: bool) -> None:
    ids = parser.add_mutually_exclusive_group(required=show)
    for name in ("record-id", "call-id", "item-id", "turn-id"):
        ids.add_argument("--" + name)
    parser.add_argument("--tool", help="exact call name or server/tool for an MCP execution event")
    parser.add_argument("--skill", help="exact skill name or plugin:skill")
    parser.add_argument(
        "--skill-kind",
        choices=[
            "named_reference",
            "body_provided",
            "catalog_entry",
            "read_candidate",
            "path_reference",
        ],
    )
    parser.add_argument("--kind", choices=sorted(KINDS))
    parser.add_argument("--text", help="literal, case-sensitive search in known evidence text")
    parser.add_argument(
        "--include-unparsed", action="store_true", help="explicitly expose/search unparsed text"
    )
    parser.add_argument("--include-duplicates", action="store_true")
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="include inherited or unowned context records",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="preview limit per record; does not alter saved data",
    )
    if show:
        parser.add_argument("--before", type=int, default=0)
        parser.add_argument("--after", type=int, default=0)


def run_session_extract(args: argparse.Namespace) -> int:
    """Save full evidence exclusively and print a compact receipt, not the raw transcript."""
    if args.sessions_dir and not args.include_children:
        raise ValueError("--sessions-dir requires --include-children")
    roots = None
    if args.include_children:
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        roots = args.sessions_dir or [home / "sessions"]
    result = extract_session(args.path, children=args.child, discovery_roots=roots)
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
    scope = {"chat_id": args.chat_id, "include_children": args.include_children}
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
