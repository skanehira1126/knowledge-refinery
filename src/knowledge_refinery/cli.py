from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from knowledge_refinery.agents_ops import LANG_CHOICES, apply_agents_md
from knowledge_refinery.front_matter import list_headers_filtered
from knowledge_refinery.knowledge_ops import list_review, prepare_review, promote_review, refresh_review, reject_review
from knowledge_refinery.session_metadata import init_session, list_sessions
from knowledge_refinery.template_ops import apply_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="knowledge-refinery", description="Knowledge refinery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply-template", help="Copy the refinery template into a target repository")
    apply_parser.add_argument("--target", default=".", help="target repository path")
    apply_parser.add_argument("--force", action="store_true", help="overwrite existing files")
    apply_parser.set_defaults(handler=run_apply_template)

    agents_parser = subparsers.add_parser(
        "update-agents-md",
        help="Append or update the managed refinery section in a target AGENTS.md",
    )
    agents_parser.add_argument("--target", default=".", help="target repository path or AGENTS.md path")
    agents_parser.add_argument("--lang", choices=LANG_CHOICES, default="jp", help="snippet language")
    agents_parser.set_defaults(handler=run_apply_agents_md)

    init_parser = subparsers.add_parser("init-session", help="Initialize a refinery session")
    init_parser.add_argument("--task", required=True, help="Task summary")
    init_parser.add_argument("--kind", default="task", help="Session kind (default: task)")
    init_parser.add_argument("--title", default=None, help="Session title (default: same as --task)")
    init_parser.add_argument(
        "--created-by",
        default="user",
        choices=["user", "llm"],
        help="Session creator (default: user)",
    )
    init_parser.add_argument("--repository", default=None, help="Repository name")
    init_parser.add_argument("--domain", default=None, help="Session domain")
    init_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    init_parser.set_defaults(handler=run_init_session)

    list_sessions_parser = subparsers.add_parser("list-sessions", help="List refinery sessions from meta.yaml")
    list_sessions_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    list_sessions_parser.set_defaults(handler=run_list_sessions)

    list_headers_parser = subparsers.add_parser("list-headers", help="List markdown YAML front matter headers in refinery")
    list_headers_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    list_headers_parser.add_argument(
        "--scope",
        action="append",
        choices=["raw", "flow", "review", "stock"],
        default=[],
        help="limit listing to a layer; may be specified multiple times",
    )
    list_headers_parser.add_argument(
        "--session-id",
        default=None,
        help="session ID filter for raw/flow scopes",
    )
    list_headers_parser.set_defaults(handler=run_list_headers)

    review_parser = subparsers.add_parser("prepare-review", help="Copy flow knowledge files into shared/review")
    review_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    review_parser.add_argument("--session-id", default=None, help="Session ID to process (default: all sessions)")
    review_parser.add_argument("--force", action="store_true", help="overwrite existing review files")
    review_parser.set_defaults(handler=run_prepare_review)

    promote_parser = subparsers.add_parser("promote-review", help="Copy review knowledge files into shared/stock")
    promote_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    promote_parser.add_argument("--all", action="store_true", help="promote all review files")
    promote_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to promote; may be specified multiple times",
    )
    promote_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to promote; may be specified multiple times",
    )
    promote_parser.add_argument("--force", action="store_true", help="overwrite existing stock files")
    promote_parser.set_defaults(handler=run_promote_review)

    list_review_parser = subparsers.add_parser("list-review", help="List review knowledge files in shared/review")
    list_review_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    list_review_parser.add_argument("--include-rejected", action="store_true", help="include rejected review files")
    list_review_parser.add_argument("--session-id", default=None, help="filter by source session ID")
    list_review_parser.set_defaults(handler=run_list_review)

    refresh_parser = subparsers.add_parser("refresh-review", help="Refresh review files from their flow sources")
    refresh_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    refresh_parser.add_argument("--all", action="store_true", help="refresh all review files")
    refresh_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to refresh; may be specified multiple times",
    )
    refresh_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to refresh; may be specified multiple times",
    )
    refresh_parser.set_defaults(handler=run_refresh_review)

    reject_parser = subparsers.add_parser("reject-review", help="Move review files out of the active review queue")
    reject_parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    reject_parser.add_argument("--all", action="store_true", help="reject all review files")
    reject_parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="knowledge_id to reject; may be specified multiple times",
    )
    reject_parser.add_argument(
        "--review-file",
        action="append",
        default=[],
        help="review file path to reject; may be specified multiple times",
    )
    reject_parser.add_argument("--force", action="store_true", help="overwrite existing rejected files")
    reject_parser.set_defaults(handler=run_reject_review)

    return parser


def run_apply_template(args: argparse.Namespace) -> int:
    target_root = Path(args.target).resolve()
    template_root, copied = apply_template(target_root, force=args.force)

    print(f"Applied template from: {template_root}")
    print(f"Target repository: {target_root}")
    print(f"Copied files: {len(copied)}")
    print("\nNext steps:")
    print("1) Install `knowledge-refinery` with `uv tool install ...` in the environment that will run the CLI.")
    print("2) Update the managed AGENTS.md section with `knowledge-refinery update-agents-md --target ... --lang jp|en`.")
    print("3) Confirm .codex/skills/ and .refinery/shared/ were copied.")
    print("4) Use sessions/*/meta.yaml as the single session metadata format.")
    return 0


def run_apply_agents_md(args: argparse.Namespace) -> int:
    agents_path = apply_agents_md(Path(args.target), lang=args.lang)
    print(agents_path.as_posix())
    return 0


def run_init_session(args: argparse.Namespace) -> int:
    session_root = init_session(
        Path(args.root),
        task=args.task,
        kind=args.kind,
        title=args.title or args.task,
        created_by=args.created_by,
        repository=args.repository,
        domain=args.domain,
    )
    print(session_root.as_posix())
    return 0


def run_list_sessions(args: argparse.Namespace) -> int:
    entries = list_sessions(Path(args.root))
    if not entries:
        print("No sessions found.")
        return 0

    for path, meta in entries:
        rel = path.parent.as_posix()
        session_id = str(meta.get("session_id", ""))
        status = str(meta.get("status", ""))
        phase = str(meta.get("phase", ""))
        flow_status = str(meta.get("flow_status", ""))
        updated = str(meta.get("last_updated_at", ""))
        print(
            f"{rel}\tsession_id={session_id}\tstatus={status}\tphase={phase}\tflow_status={flow_status}\tlast_updated_at={updated}"
        )
    return 0


def run_list_headers(args: argparse.Namespace) -> int:
    entries = list_headers_filtered(
        Path(args.root),
        scopes=list(args.scope),
        session_id=args.session_id,
    )
    if not entries:
        print("No front matter headers found.")
        return 0

    for path, header in entries:
        rel = path.as_posix()
        title = header.get("title", "")
        desc = header.get("description", "")
        print(f"{rel}\ttitle={title}\tdescription={desc}")
    return 0


def run_prepare_review(args: argparse.Namespace) -> int:
    results = prepare_review(Path(args.root), session_id=args.session_id, force=args.force)
    if not results:
        print("No flow knowledge files found.")
        return 0

    copied = 0
    skipped = 0
    for result in results:
        status = "copied" if result.copied else "skipped"
        rel_source = result.source.as_posix()
        rel_target = result.target.as_posix()
        print(f"{status}\t{rel_target}\tfrom={rel_source}")
        if result.copied:
            copied += 1
        else:
            skipped += 1

    print(f"Prepared review files: copied={copied} skipped={skipped}")
    return 0


def run_promote_review(args: argparse.Namespace) -> int:
    results = promote_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
        force=args.force,
    )

    copied = 0
    skipped = 0
    for result in results:
        status = "copied" if result.copied else "skipped"
        rel_source = result.source.as_posix()
        rel_target = result.target.as_posix()
        print(f"{status}\t{rel_target}\tfrom={rel_source}")
        if result.copied:
            copied += 1
        else:
            skipped += 1

    print(f"Promoted review files: copied={copied} skipped={skipped}")
    return 0


def run_list_review(args: argparse.Namespace) -> int:
    entries = list_review(
        Path(args.root),
        include_rejected=bool(args.include_rejected),
        session_id=args.session_id,
    )
    if not entries:
        print("No review files found.")
        return 0

    for entry in entries:
        sessions = ",".join(entry.source_sessions)
        print(
            f"{entry.path.as_posix()}\tknowledge_id={entry.knowledge_id}\ttitle={entry.title}\tsource_sessions={sessions}"
        )
    return 0


def run_refresh_review(args: argparse.Namespace) -> int:
    results = refresh_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
    )
    refreshed = 0
    for result in results:
        print(f"refreshed\t{result.target.as_posix()}\tfrom={result.source.as_posix()}")
        refreshed += 1
    print(f"Refreshed review files: {refreshed}")
    return 0


def run_reject_review(args: argparse.Namespace) -> int:
    results = reject_review(
        Path(args.root),
        knowledge_ids=list(args.knowledge_id),
        review_files=list(args.review_file),
        all_files=bool(args.all),
        force=args.force,
    )
    moved = 0
    skipped = 0
    for result in results:
        status = "moved" if result.copied else "skipped"
        print(f"{status}\t{result.target.as_posix()}\tfrom={result.source.as_posix()}")
        if result.copied:
            moved += 1
        else:
            skipped += 1
    print(f"Rejected review files: moved={moved} skipped={skipped}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
