"""Expose vault-wide issue operations through the command-line interface."""

import argparse
import json

from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.issue_ops import ISSUE_STATUSES
from knowledge_refinery.issue_ops import create_issue
from knowledge_refinery.issue_ops import get_issue
from knowledge_refinery.issue_ops import list_issue_tags
from knowledge_refinery.issue_ops import list_issues
from knowledge_refinery.issue_ops import maintain_issue_tag
from knowledge_refinery.issue_ops import update_issue


def configure_issue_parser(parser: argparse.ArgumentParser) -> None:
    """Register issue and issue-tag commands on the supplied issue parser."""
    commands = parser.add_subparsers(dest="issue_command", required=True)
    create = commands.add_parser("create", help="Create an independent backlog issue")
    create.add_argument("--title", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--done-when", default="", help="completion criteria")
    create.add_argument("--project", action="append", help="registered project ID; repeatable")
    create.add_argument("--tag", action="append", help="free-form issue tag; repeatable")

    show = commands.add_parser("show", help="Read an issue and its change history")
    show.add_argument("issue_id")
    listing = commands.add_parser("list", help="List issues across the active vault")
    listing.add_argument("--project", help="filter by registered project ID, not a local path")
    listing.add_argument("--status", choices=ISSUE_STATUSES)
    listing.add_argument("--tag")

    update = commands.add_parser("update", help="Update fields, status, project links, and tags")
    update.add_argument("issue_id")
    update.add_argument("--expected-revision", type=int, required=True)
    update.add_argument("--title")
    update.add_argument("--description")
    update.add_argument("--done-when")
    update.add_argument("--status", choices=ISSUE_STATUSES)
    update.add_argument("--reason", default="", help="required for status changes")
    for option in ("add-project", "remove-project", "add-tag", "remove-tag"):
        update.add_argument(f"--{option}", action="append")

    tags = commands.add_parser("tag", help="List, rename/merge, or remove issue tags")
    tag_commands = tags.add_subparsers(dest="issue_tag_command", required=True)
    tag_list = tag_commands.add_parser("list", help="List used tags and issue counts")
    tag_list.add_argument("--project", help="limit counts to one project ID")
    rename = tag_commands.add_parser("rename", help="Rename a tag; merge if destination exists")
    rename.add_argument("tag")
    rename.add_argument("replacement")
    remove = tag_commands.add_parser("remove", help="Remove a tag from all issues")
    remove.add_argument("tag")
    for command in (create, show, listing, update, tag_list, rename, remove):
        command.add_argument("--json", action="store_true", help="emit machine-readable JSON")
        command.set_defaults(handler=run_issue)


def run_issue(args: argparse.Namespace) -> int:
    """Resolve the active vault, perform the operation, and render its result."""
    vault = get_active_vault()
    operation = args.issue_command
    payload: object
    if operation == "create":
        payload = create_issue(
            vault,
            title=args.title,
            description=args.description,
            done_when=args.done_when,
            projects=args.project,
            tags=args.tag,
        )
    elif operation == "show":
        payload = get_issue(vault, args.issue_id)
    elif operation == "list":
        payload = [
            {key: value for key, value in issue.items() if key != "history"}
            for issue in list_issues(vault, project=args.project, status=args.status, tag=args.tag)
        ]
    elif operation == "update":
        payload = update_issue(
            vault,
            args.issue_id,
            expected_revision=args.expected_revision,
            title=args.title,
            description=args.description,
            done_when=args.done_when,
            status=args.status,
            add_projects=args.add_project,
            remove_projects=args.remove_project,
            add_tags=args.add_tag,
            remove_tags=args.remove_tag,
            reason=args.reason,
        )
    elif args.issue_tag_command == "list":
        payload = list_issue_tags(vault, project=args.project)
    else:
        affected = maintain_issue_tag(
            vault,
            args.tag,
            replacement=args.replacement if args.issue_tag_command == "rename" else None,
        )
        payload = {"affected_issues": affected, "count": len(affected)}
    print(json.dumps(payload, ensure_ascii=False, indent=None if args.json else 2))
    return 0
