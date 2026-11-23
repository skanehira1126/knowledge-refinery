"""Inspect stored project context and deliver the plugin's fixed operating instructions."""

import argparse
import json
from pathlib import Path
import sys

from knowledge_refinery.agents_ops import load_agents_snippet
from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.context_ops import list_contexts
from knowledge_refinery.context_ops import read_context
from knowledge_refinery.vault_ops import ProjectContext
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import find_project_root
from knowledge_refinery.vault_ops import inspect_maintenance_vault
from knowledge_refinery.vault_ops import read_project_config
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import resolve_project_context


def configure_context_parser(parser: argparse.ArgumentParser) -> None:
    """Register context inspection and the fixed SessionStart command."""
    commands = parser.add_subparsers(dest="context_command", required=True)
    listing = commands.add_parser("list", help="List supported targets and their revisions")
    show = commands.add_parser("show", help="Read one target's Markdown")
    for command in (listing, show):
        location = command.add_mutually_exclusive_group()
        location.add_argument("--project", help="project working directory (default: cwd)")
        location.add_argument("--vault", help="opened active vault root, with --project-id")
        command.add_argument("--project-id", help="registered project ID for --vault")
        command.add_argument("--json", action="store_true", help="include revision in JSON")
    show.add_argument("target", help="target from context list or a saved SessionStart target")
    listing.set_defaults(handler=run_context_list)
    show.set_defaults(handler=run_context_show)
    guidance = commands.add_parser(
        "guidance-hook", help="Deliver plugin guidance at session start"
    )
    guidance.set_defaults(handler=run_guidance_hook)


def _selected_project(args: argparse.Namespace) -> ProjectContext:
    if (args.vault is None) != (args.project_id is None):
        raise ValueError("--vault and --project-id must be supplied together")
    active = get_active_vault()
    if args.vault is not None:
        inspect_maintenance_vault(Path(args.vault).expanduser().resolve(), active)
        project = context_from_vault(active, args.project_id)
    else:
        root = find_project_root(Path(args.project or "."))
        if root is None:
            raise ValueError("No registered project at this working directory")
        project = resolve_project_context(root, active)
    read_project_metadata(active, project.project_id)
    return project


def run_context_list(args: argparse.Namespace) -> int:
    """Show saved and unset targets for one project."""
    entries = list_contexts(_selected_project(args).project_store)
    if args.json:
        print(json.dumps(entries))
    else:
        for entry in entries:
            print(f"{entry['target']}\t{entry['revision'] or '-'}")
    return 0


def run_context_show(args: argparse.Namespace) -> int:
    """Print one body as Markdown or return its text and revision from the same read."""
    entry = read_context(_selected_project(args).project_store, args.target)
    if args.json:
        print(json.dumps(entry, ensure_ascii=False))
    elif entry["body"] is not None:
        sys.stdout.write(entry["body"])
    return 0


def run_guidance_hook(args: argparse.Namespace) -> int:
    """Deliver the packaged instructions to a locally enabled repo on startup or compact."""
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object in hook input")
    event = payload.get("hook_event_name")
    if not isinstance(event, str):
        raise ValueError("Expected hook_event_name in hook input")
    if event != "SessionStart" or payload.get("source") not in ("startup", "compact"):
        return 0
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise ValueError("Expected an absolute cwd in hook input")
    root = find_project_root(Path(cwd))
    if root is not None and read_project_config(root, include_binding=False).enabled:
        output = {"hookEventName": event, "additionalContext": load_agents_snippet("jp")}
        print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))
    return 0
