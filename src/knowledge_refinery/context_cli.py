"""Inspect project hook context and deliver it to Codex."""

import argparse
import json
from pathlib import Path
import sys

from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.context_ops import context_targets
from knowledge_refinery.context_ops import hook_target
from knowledge_refinery.context_ops import list_contexts
from knowledge_refinery.context_ops import read_context
from knowledge_refinery.vault_ops import PROJECT_CONFIG
from knowledge_refinery.vault_ops import ProjectContext
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import inspect_maintenance_vault
from knowledge_refinery.vault_ops import read_project_config
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import resolve_project_context


def configure_context_parser(parser: argparse.ArgumentParser) -> None:
    """Register local context reads and the stdin/stdout hook adapter."""
    commands = parser.add_subparsers(dest="context_command", required=True)
    listing = commands.add_parser("list", help="List supported targets and their revisions")
    show = commands.add_parser("show", help="Read one target's Markdown")
    for command in (listing, show):
        location = command.add_mutually_exclusive_group()
        location.add_argument("--project", help="project working directory (default: cwd)")
        location.add_argument("--vault", help="opened active vault root, with --project-id")
        command.add_argument("--project-id", help="registered project ID for --vault")
        command.add_argument("--json", action="store_true", help="include revision in JSON")
    show.add_argument("target", choices=context_targets())
    listing.set_defaults(handler=run_context_list)
    show.set_defaults(handler=run_context_show)
    hook = commands.add_parser("hook", help="Deliver context for a Codex hook JSON on stdin")
    hook.set_defaults(handler=run_context_hook)


def _project_root(cwd: Path) -> Path | None:
    cwd = cwd.expanduser().resolve()
    for root in (cwd, *cwd.parents):
        if (root / PROJECT_CONFIG).is_file():
            return root
        if (root / ".git").exists():
            break
    return None


def _selected_project(args: argparse.Namespace) -> ProjectContext:
    if (args.vault is None) != (args.project_id is None):
        raise ValueError("--vault and --project-id must be supplied together")
    active = get_active_vault()
    if args.vault is not None:
        inspect_maintenance_vault(Path(args.vault).expanduser().resolve(), active)
        project = context_from_vault(active, args.project_id)
    else:
        root = _project_root(Path(args.project or "."))
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


def run_context_hook(args: argparse.Namespace) -> int:
    """Emit only saved Markdown as Codex additional context for the incoming event."""
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object in Codex hook input")
    event = payload.get("hook_event_name")
    if not isinstance(event, str):
        raise ValueError("Expected hook_event_name in Codex hook input")
    target = hook_target(event, payload)
    if target is None:
        return 0
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise ValueError("Expected an absolute cwd in Codex hook input")
    root = _project_root(Path(cwd))
    if root is None or not read_project_config(root).enabled:
        return 0
    active = get_active_vault()
    project = resolve_project_context(root, active)
    body = read_context(project.project_store, target)["body"]
    if body and body.strip():
        read_project_metadata(active, project.project_id)
        output = {"hookEventName": event, "additionalContext": body}
        print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))
    return 0
