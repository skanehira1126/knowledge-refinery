from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import yaml

from knowledge_refinery import get_version
from knowledge_refinery.agents_ops import GUIDE_FILENAME_CHOICES
from knowledge_refinery.agents_ops import LANG_CHOICES
from knowledge_refinery.agents_ops import apply_agents_md
from knowledge_refinery.agents_ops import has_managed_block
from knowledge_refinery.agents_ops import remove_agents_md
from knowledge_refinery.config_ops import get_active_vault
from knowledge_refinery.config_ops import set_active_vault
from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import CONFIDENCE_CHOICES
from knowledge_refinery.experience_ops import EVIDENCE_TYPE_CHOICES
from knowledge_refinery.experience_ops import EXPERIENCE_STATUS_CHOICES
from knowledge_refinery.experience_ops import MEMORY_SCOPE_CHOICES
from knowledge_refinery.experience_ops import SearchFilters
from knowledge_refinery.experience_ops import parse_datetime_filter
from knowledge_refinery.experience_ops import read_experience_at
from knowledge_refinery.experience_ops import read_memory_at
from knowledge_refinery.experience_ops import search_documents_at
from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.tag_ops import browse_knowledge_tags
from knowledge_refinery.tag_ops import search_knowledge_tags
from knowledge_refinery.tag_ops import update_tag_description
from knowledge_refinery.vault_ops import context_from_vault
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import enable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import inspect_project
from knowledge_refinery.vault_ops import read_project_metadata
from knowledge_refinery.vault_ops import resolve_project_id
from knowledge_refinery.vault_ops import setup_project
from knowledge_refinery.vault_ops import update_project_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge-refinery",
        description="Keep project experiences in a central personal refinery repository.",
    )
    parser.add_argument("--version", action="version", version=get_version())
    subparsers = parser.add_subparsers(dest="command", required=True)

    vault_parser = subparsers.add_parser("vault", help="Manage the central refinery repository")
    vault_subparsers = vault_parser.add_subparsers(dest="vault_command", required=True)
    vault_init = vault_subparsers.add_parser(
        "init", help="Initialize a central refinery repository"
    )
    vault_init.add_argument("--root", required=True, help="central refinery repository path")
    vault_init.add_argument(
        "--force",
        action="store_true",
        help="overwrite managed vault templates; preserves the immutable vault ID",
    )
    vault_init.set_defaults(handler=run_vault_init)
    vault_configure = vault_subparsers.add_parser(
        "configure", help="Set the active vault used by the local MCP server"
    )
    vault_configure.add_argument("--root", required=True, help="central refinery repository path")
    vault_configure.set_defaults(handler=run_vault_configure)

    project_parser = subparsers.add_parser("project", help="Connect a project to a refinery")
    project_subparsers = project_parser.add_subparsers(dest="project_command", required=True)
    project_setup = project_subparsers.add_parser(
        "setup", help="Create a project area, metadata, and optional .refinery link"
    )
    project_setup.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_setup.add_argument("--vault", required=True, help="central refinery repository path")
    project_setup.add_argument("--project-id", default=None, help="stable project slug")
    project_setup.add_argument("--project-name", default=None, help="human-readable project name")
    project_setup.add_argument("--summary", default=None, help="concise project summary")
    project_setup.add_argument(
        "--tag", action="append", default=None, help="project discovery tag"
    )
    project_setup.add_argument(
        "--technology", action="append", default=None, help="technology used by the project"
    )
    project_setup.add_argument(
        "--link",
        action="store_true",
        help="optionally create a human-facing .refinery symlink",
    )
    add_guide_arguments(project_setup)
    project_setup.add_argument(
        "--agents",
        action="store_true",
        help="append the managed repository guidance block",
    )
    project_setup.set_defaults(handler=run_project_setup)

    project_enable = project_subparsers.add_parser(
        "enable", help="Re-enable Knowledge Refinery for a configured project"
    )
    project_enable.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_enable.add_argument(
        "--vault", default=None, help="central vault; defaults to the active vault"
    )
    project_enable.add_argument(
        "--link",
        action="store_true",
        help="optionally create a human-facing .refinery symlink",
    )
    add_guide_arguments(project_enable)
    project_enable.add_argument(
        "--agents",
        action="store_true",
        help="append the managed repository guidance block",
    )
    project_enable.set_defaults(handler=run_project_enable)

    project_disable = project_subparsers.add_parser(
        "disable", help="Disable integration without deleting central knowledge"
    )
    project_disable.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_disable.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    project_disable.set_defaults(handler=run_project_disable)

    project_status = project_subparsers.add_parser(
        "status", help="Inspect repository integration and active-vault consistency"
    )
    project_status.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_status.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    project_status.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    project_status.set_defaults(handler=run_project_status)

    project_metadata = project_subparsers.add_parser(
        "metadata", help="Read or update central project metadata"
    )
    project_metadata_subparsers = project_metadata.add_subparsers(
        dest="project_metadata_command", required=True
    )
    project_metadata_show = project_metadata_subparsers.add_parser(
        "show", help="Read project metadata"
    )
    project_metadata_show.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_metadata_show.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    project_metadata_show.set_defaults(handler=run_project_metadata_show)
    project_metadata_update = project_metadata_subparsers.add_parser(
        "update", help="Partially update project metadata using the current revision"
    )
    project_metadata_update.add_argument(
        "--target", "--project", dest="target", default=".", help="project repository path"
    )
    project_metadata_update.add_argument("--name", default=None, help="human-readable name")
    project_metadata_update.add_argument("--summary", default=None, help="concise summary")
    tag_update = project_metadata_update.add_mutually_exclusive_group()
    tag_update.add_argument(
        "--tag", action="append", default=None, help="replace project discovery tags"
    )
    tag_update.add_argument("--clear-tags", action="store_true", help="remove every project tag")
    technology_update = project_metadata_update.add_mutually_exclusive_group()
    technology_update.add_argument(
        "--technology", action="append", default=None, help="replace project technologies"
    )
    technology_update.add_argument(
        "--clear-technologies", action="store_true", help="remove every project technology"
    )
    project_metadata_update.add_argument(
        "--expected-updated-at",
        required=True,
        help="revision returned by project metadata show",
    )
    project_metadata_update.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    project_metadata_update.set_defaults(handler=run_project_metadata_update)

    experience_parser = subparsers.add_parser("experience", help="Record and search experiences")
    experience_subparsers = experience_parser.add_subparsers(
        dest="experience_command", required=True
    )
    experience_upsert = experience_subparsers.add_parser(
        "upsert", help="Create or update one integrated experience document"
    )
    experience_upsert.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    experience_upsert.add_argument("--experience-id", default=None, help="stable experience ID")
    experience_upsert.add_argument("--title", required=True, help="experience title")
    experience_upsert.add_argument("--purpose", required=True, help="purpose of the attempt")
    experience_upsert.add_argument(
        "--status",
        choices=EXPERIENCE_STATUS_CHOICES,
        default="completed",
        help="experience outcome state",
    )
    experience_tags = experience_upsert.add_mutually_exclusive_group()
    experience_tags.add_argument("--tag", action="append", default=None, help="search tag")
    experience_tags.add_argument(
        "--clear-tags", action="store_true", help="remove every knowledge tag"
    )
    experience_evidence = experience_upsert.add_mutually_exclusive_group()
    experience_evidence.add_argument(
        "--evidence", action="append", default=None, help="evidence reference; repeatable"
    )
    experience_evidence.add_argument(
        "--clear-evidence", action="store_true", help="remove every evidence reference"
    )
    experience_related = experience_upsert.add_mutually_exclusive_group()
    experience_related.add_argument(
        "--related-experience", action="append", default=None, help="related experience ID"
    )
    experience_related.add_argument(
        "--clear-related-experiences",
        action="store_true",
        help="remove every related experience",
    )
    experience_supersedes = experience_upsert.add_mutually_exclusive_group()
    experience_supersedes.add_argument(
        "--supersedes", action="append", default=None, help="superseded experience ID"
    )
    experience_supersedes.add_argument(
        "--clear-supersedes", action="store_true", help="remove every superseded experience"
    )
    experience_confidence = experience_upsert.add_mutually_exclusive_group()
    experience_confidence.add_argument("--confidence", choices=CONFIDENCE_CHOICES, default=None)
    experience_confidence.add_argument(
        "--clear-confidence", action="store_true", help="remove the confidence value"
    )
    experience_upsert.add_argument(
        "--expected-updated-at",
        default=None,
        help="revision returned by a prior read; required when updating existing experience",
    )
    add_body_arguments(experience_upsert)
    experience_upsert.set_defaults(handler=run_experience_upsert)

    experience_get = experience_subparsers.add_parser(
        "get", help="Read one experience document as JSON"
    )
    experience_get.add_argument("source", help="experience ID or project-id/experience-id")
    experience_get.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    experience_get.set_defaults(handler=run_experience_get)

    experience_search = experience_subparsers.add_parser(
        "search", help="Search experiences across projects"
    )
    add_search_arguments(experience_search)
    experience_search.add_argument(
        "--status", action="append", choices=EXPERIENCE_STATUS_CHOICES, default=[]
    )
    experience_search.add_argument(
        "--related-experience", action="append", default=[], help="related experience filter"
    )
    experience_search.add_argument(
        "--evidence-type", action="append", choices=EVIDENCE_TYPE_CHOICES, default=[]
    )
    add_typed_search_arguments(experience_search)
    experience_search.set_defaults(handler=run_experience_search)

    memory_parser = subparsers.add_parser("memory", help="Record and search distilled memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_upsert = memory_subparsers.add_parser(
        "upsert", help="Create or update a reusable memory document"
    )
    memory_upsert.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    memory_upsert.add_argument("--memory-id", default=None, help="stable memory ID")
    memory_upsert.add_argument("--title", required=True, help="memory title")
    memory_upsert.add_argument("--summary", required=True, help="reusable principle")
    memory_tags = memory_upsert.add_mutually_exclusive_group()
    memory_tags.add_argument("--tag", action="append", default=None, help="search tag")
    memory_tags.add_argument(
        "--clear-tags", action="store_true", help="remove every knowledge tag"
    )
    memory_upsert.add_argument(
        "--source-experience",
        action="append",
        default=None,
        help="experience ID supporting this memory",
    )
    memory_upsert.add_argument("--shared", action="store_true", help="write to shared/memory")
    memory_confidence = memory_upsert.add_mutually_exclusive_group()
    memory_confidence.add_argument("--confidence", choices=CONFIDENCE_CHOICES, default=None)
    memory_confidence.add_argument(
        "--clear-confidence", action="store_true", help="remove the confidence value"
    )
    memory_upsert.add_argument(
        "--expected-updated-at",
        default=None,
        help="revision returned by a prior read; required when updating existing memory",
    )
    add_body_arguments(memory_upsert)
    memory_upsert.set_defaults(handler=run_memory_upsert)

    memory_get = memory_subparsers.add_parser("get", help="Read one memory document as JSON")
    memory_get.add_argument("memory_id", help="stable memory ID")
    memory_get.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    memory_get.add_argument("--scope", choices=MEMORY_SCOPE_CHOICES, default="project")
    memory_get.add_argument("--project-id", default=None, help="project scope owner")
    memory_get.set_defaults(handler=run_memory_get)

    memory_search = memory_subparsers.add_parser("search", help="Search project and shared memory")
    add_search_arguments(memory_search)
    memory_search.add_argument(
        "--source-experience", action="append", default=[], help="supporting experience filter"
    )
    memory_search.add_argument(
        "--scope", action="append", choices=MEMORY_SCOPE_CHOICES, default=[]
    )
    add_typed_search_arguments(memory_search)
    memory_search.set_defaults(handler=run_memory_search)

    tag_parser = subparsers.add_parser("tag", help="Browse and describe Knowledge tags")
    tag_subparsers = tag_parser.add_subparsers(dest="tag_command", required=True)
    tag_browse = tag_subparsers.add_parser(
        "browse", help="List the immediate children of one Knowledge tag"
    )
    tag_browse.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    tag_browse.add_argument("--parent", default=None, help="parent tag; omit for root tags")
    tag_browse.add_argument(
        "--all-projects", action="store_true", help="include usage from every project"
    )
    tag_browse.set_defaults(handler=run_tag_browse)

    tag_search = tag_subparsers.add_parser(
        "search", help="Search Knowledge tag paths and descriptions"
    )
    tag_search.add_argument("terms", nargs="+", help="AND-matched search terms")
    tag_search.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    tag_search.add_argument(
        "--all-projects", action="store_true", help="include usage from every project"
    )
    tag_search.set_defaults(handler=run_tag_search)

    tag_describe = tag_subparsers.add_parser(
        "describe", help="Create or update one Knowledge tag description"
    )
    tag_describe.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    tag_describe.add_argument("--tag", required=True, help="Knowledge tag path")
    tag_describe.add_argument("--description", required=True, help="stable tag description")
    tag_describe.add_argument(
        "--expected-updated-at",
        default=None,
        help="taxonomy revision returned by tag browse or search",
    )
    tag_describe.set_defaults(handler=run_tag_describe)

    agents_parser = subparsers.add_parser(
        "update-agents-md", help="Update the managed refinery guidance block"
    )
    agents_parser.add_argument("--target", "--project", dest="target", default=".")
    agents_parser.add_argument("--lang", choices=LANG_CHOICES, default="jp")
    agents_parser.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    agents_parser.set_defaults(handler=run_apply_agents_md)

    mcp_parser = subparsers.add_parser("mcp", help="Run the local MCP server")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_subparsers.add_parser("serve", help="Serve MCP over stdio")
    mcp_serve.set_defaults(handler=run_mcp_serve)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Diagnose runtime, active vault, and project integration"
    )
    doctor_parser.add_argument(
        "--target",
        "--project",
        dest="target",
        default=".",
        help="project repository path (--project is a compatibility alias)",
    )
    doctor_parser.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    doctor_parser.add_argument(
        "--mcp-version",
        default=None,
        help="version returned by refinery_info; enables CLI/Plugin drift detection",
    )
    doctor_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    doctor_parser.set_defaults(handler=run_doctor)
    return parser


def add_guide_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lang", choices=LANG_CHOICES, default="jp")
    parser.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")


def add_body_arguments(parser: argparse.ArgumentParser) -> None:
    body_group = parser.add_mutually_exclusive_group()
    body_group.add_argument("--body", default=None, help="Markdown body")
    body_group.add_argument("--body-file", default=None, help="UTF-8 Markdown body file")


def add_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("terms", nargs="*", default=[], help="AND-matched search terms")
    parser.add_argument(
        "--project", "--target", dest="project", default=".", help="configured project path"
    )
    parser.add_argument("--project-id", action="append", default=[], help="project filter")
    parser.add_argument("--tag", action="append", default=[], help="required tag")
    parser.add_argument("--all-projects", action="store_true", help="search every project")


def add_typed_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", action="append", default=[], help="exact document ID")
    parser.add_argument("--confidence", action="append", choices=CONFIDENCE_CHOICES, default=[])
    parser.add_argument("--recorded-from", default=None, help="inclusive ISO date or datetime")
    parser.add_argument("--recorded-to", default=None, help="inclusive ISO date or datetime")


def read_body(args: argparse.Namespace) -> str | None:
    if args.body_file is not None:
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body


def run_vault_init(args: argparse.Namespace) -> int:
    previous, _ = _active_vault_or_error()
    result = init_vault(Path(args.root), force=bool(args.force))
    config = set_active_vault(result.root)
    print(f"Refinery initialized: {result.root}")
    if previous is not None and previous != result.root:
        print(f"Previous active vault: {previous}")
    print(f"Active vault: {result.root}")
    print(f"Config file: {config}")
    print(f"Created or updated files: {len(result.changed)}")
    return 0


def run_vault_configure(args: argparse.Namespace) -> int:
    previous, _ = _active_vault_or_error()
    root = Path(args.root).expanduser().resolve()
    config = set_active_vault(root)
    if previous is not None and previous != root:
        print(f"Previous active vault: {previous}")
    print(f"Active vault: {root}")
    print(f"Config file: {config}")
    return 0


def run_project_setup(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    previous, _ = _active_vault_or_error()
    result = setup_project(
        Path(args.target),
        vault,
        project_id=args.project_id,
        project_name=args.project_name,
        summary=args.summary,
        tags=list(args.tag) if args.tag is not None else None,
        technologies=list(args.technology) if args.technology is not None else None,
        create_link=bool(args.link),
    )
    config = set_active_vault(vault)
    active = get_active_vault()
    print(f"Project configured: {result.project_id}")
    print(f"Project config: {result.config_path}")
    print(f"Local vault binding: {result.local_config_path}")
    print(f"Refinery store: {result.project_store}")
    print(f"Project metadata: {result.metadata_path}")
    if previous is not None and previous != active:
        print(f"Previous active vault: {previous}")
    print(f"Active vault: {active}")
    print(f"Config file: {config}")
    if result.link_path is not None:
        print(f"Optional refinery link: {result.link_path}")
    if args.agents:
        agents_path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
        print(f"Managed repository guidance: {agents_path}")
    return 0


def run_project_enable(args: argparse.Namespace) -> int:
    previous, _ = _active_vault_or_error()
    vault = Path(args.vault) if args.vault is not None else get_active_vault()
    result = enable_project(Path(args.target), vault, create_link=bool(args.link))
    if args.vault is not None:
        config = set_active_vault(vault)
        active = get_active_vault()
    print(f"Project enabled: {result.project_id}")
    print(f"Project config: {result.config_path}")
    print(f"Local vault binding: {result.local_config_path}")
    print(f"Refinery store: {result.project_store}")
    print(f"Project metadata: {result.metadata_path}")
    if args.vault is not None:
        if previous is not None and previous != active:
            print(f"Previous active vault: {previous}")
        print(f"Active vault: {active}")
        print(f"Config file: {config}")
    if result.link_path is not None:
        print(f"Optional refinery link: {result.link_path}")
    if args.agents:
        agents_path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
        print(f"Managed repository guidance: {agents_path}")
    return 0


def run_project_disable(args: argparse.Namespace) -> int:
    project = Path(args.target)
    config = disable_project(project)
    removed = remove_agents_md(project, filename=args.filename)
    print(f"Project disabled: {config.project_id}")
    print("Central refinery data was preserved.")
    if removed is not None:
        print(f"Managed repository guidance removed: {removed}")
    return 0


def _active_vault_or_error() -> tuple[Path | None, str | None]:
    try:
        return get_active_vault(), None
    except (OSError, ValueError) as error:
        return None, str(error)


def _project_status_payload(project: Path, filename: str) -> dict[str, object]:
    vault, vault_error = _active_vault_or_error()
    status = inspect_project(project, vault)
    metadata: dict[str, object] | None = None
    metadata_error = status.metadata_error
    if vault is not None and status.metadata_valid and status.project_id is not None:
        try:
            metadata = read_project_metadata(vault, status.project_id).as_dict()
        except (OSError, ValueError) as error:
            metadata_error = str(error)
    ready_for_tools = status.ready and metadata is not None
    return {
        "state": status.state,
        "ready": ready_for_tools,
        "ready_for_tools": ready_for_tools,
        "project_root": str(status.project_root),
        "config_path": str(status.config_path),
        "config_exists": status.config_exists,
        "config_valid": status.config_valid,
        "config_error": status.config_error,
        "project_id": status.project_id,
        "enabled": status.enabled,
        "configured_vault_id": status.configured_vault_id,
        "active_vault_id": status.active_vault_id,
        "vault_match": status.vault_match,
        "active_vault": str(status.vault_root) if status.vault_root is not None else None,
        "active_vault_error": vault_error,
        "vault_registered": status.vault_registered,
        "project_store": (str(status.project_store) if status.project_store is not None else None),
        "project_metadata_path": (
            str(status.metadata_path) if status.metadata_path is not None else None
        ),
        "project_metadata": metadata,
        "project_metadata_valid": status.metadata_valid,
        "project_metadata_error": metadata_error,
        "link_state": status.link_state,
        "managed_guidance": has_managed_block(project, filename=filename),
        "guidance_filename": filename,
    }


def _print_mapping(payload: dict[str, object]) -> None:
    for key, value in payload.items():
        if isinstance(value, bool):
            rendered = "yes" if value else "no"
        elif value is None:
            rendered = "-"
        else:
            rendered = str(value)
        print(f"{key}: {rendered}")


def run_project_status(args: argparse.Namespace) -> int:
    payload = _project_status_payload(Path(args.target), args.filename)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        _print_mapping(payload)
    return 0 if payload["state"] == "disabled" or payload["ready"] else 1


def run_project_metadata_show(args: argparse.Namespace) -> int:
    vault = get_active_vault()
    metadata = read_project_metadata(vault, resolve_project_id(Path(args.target), vault)).as_dict()
    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    else:
        _print_mapping(metadata)
    return 0


def run_project_metadata_update(args: argparse.Namespace) -> int:
    vault = get_active_vault()
    project_id = resolve_project_id(Path(args.target), vault)
    tags = [] if args.clear_tags else (list(args.tag) if args.tag is not None else None)
    technologies = (
        []
        if args.clear_technologies
        else (list(args.technology) if args.technology is not None else None)
    )
    metadata = update_project_metadata(
        vault,
        project_id,
        expected_updated_at=args.expected_updated_at,
        name=args.name,
        summary=args.summary,
        tags=tags,
        technologies=technologies,
    ).as_dict()
    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    else:
        _print_mapping(metadata)
    return 0


def _vault_write_check(vault: Path | None) -> tuple[bool, str]:
    if vault is None:
        return False, "active vault unavailable"
    descriptor = -1
    temporary_name = ""
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".doctor-", dir=vault)
        os.close(descriptor)
        descriptor = -1
        Path(temporary_name).unlink()
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass
        return False, str(error)
    return True, "temporary write succeeded"


def _mcp_runtime_and_vault_check() -> tuple[dict[str, object], dict[str, object]]:
    try:
        from knowledge_refinery.mcp_server import refinery_info
        from knowledge_refinery.mcp_server import refinery_validate

        info = refinery_info()
    except (ImportError, OSError, ValueError, RefineryCliError) as error:
        runtime = {"name": "mcp_runtime", "ok": False, "detail": str(error)}
        documents = {
            "name": "vault_documents",
            "ok": False,
            "detail": "MCP runtime unavailable",
            "errors": [],
        }
        return runtime, documents
    runtime = {
        "name": "mcp_runtime",
        "ok": info.get("version") == get_version(),
        "detail": f"server={info.get('version')}, schema={info.get('schema_version')}",
    }
    try:
        validation = refinery_validate()
    except (OSError, ValueError, RefineryCliError) as error:
        documents = {
            "name": "vault_documents",
            "ok": False,
            "detail": str(error),
            "errors": [],
        }
        return runtime, documents
    errors = validation.get("errors", [])
    documents = {
        "name": "vault_documents",
        "ok": bool(validation.get("valid")),
        "detail": f"checked={validation.get('checked', 0)}, errors={len(errors)}",
        "errors": errors if isinstance(errors, list) else [],
    }
    return runtime, documents


def run_doctor(args: argparse.Namespace) -> int:
    project = _project_status_payload(Path(args.target), args.filename)
    active_vault = Path(str(project["active_vault"])) if project["active_vault"] else None
    write_ok, write_detail = _vault_write_check(active_vault)
    mcp_runtime, vault_documents = _mcp_runtime_and_vault_check()
    runtime_checks: list[dict[str, object]] = [
        {
            "name": "python",
            "ok": sys.version_info >= (3, 11),
            "detail": sys.version.split()[0],
        },
        mcp_runtime,
        {
            "name": "uv",
            "ok": shutil.which("uv") is not None,
            "detail": shutil.which("uv") or "executable not found",
        },
        {
            "name": "active_vault",
            "ok": project["active_vault_error"] is None,
            "detail": project["active_vault"] or project["active_vault_error"],
        },
        {"name": "vault_writable", "ok": write_ok, "detail": write_detail},
        vault_documents,
        {
            "name": "project",
            "ok": project["state"] == "disabled" or project["ready_for_tools"],
            "detail": (
                "disabled (healthy opt-out; tools unavailable)"
                if project["state"] == "disabled"
                else project["state"]
            ),
        },
    ]
    if args.mcp_version is not None:
        runtime_checks.append(
            {
                "name": "version_match",
                "ok": args.mcp_version == get_version(),
                "detail": f"cli={get_version()}, mcp={args.mcp_version}",
            }
        )
    payload: dict[str, object] = {
        "ok": all(bool(check["ok"]) for check in runtime_checks),
        "runtime": runtime_checks,
        "project": project,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"ok: {'yes' if payload['ok'] else 'no'}")
        for check in runtime_checks:
            state = "ok" if check["ok"] else "error"
            print(f"{check['name']}: {state} ({check['detail']})")
        print(f"project_id: {project['project_id'] or '-'}")
        print(f"link_state: {project['link_state']}")
        print(f"managed_guidance: {'yes' if project['managed_guidance'] else 'no'}")
    return 0 if payload["ok"] else 1


def run_experience_upsert(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    tags = [] if args.clear_tags else args.tag
    evidence = [] if args.clear_evidence else args.evidence
    related_experiences = [] if args.clear_related_experiences else args.related_experience
    supersedes = [] if args.clear_supersedes else args.supersedes
    path = upsert_experience_at(
        vault,
        resolve_project_id(project, vault),
        title=args.title,
        purpose=args.purpose,
        status=args.status,
        experience_id=args.experience_id,
        filename=None,
        tags=list(tags) if tags is not None else None,
        evidence=list(evidence) if evidence is not None else None,
        related_experiences=(
            list(related_experiences) if related_experiences is not None else None
        ),
        supersedes=list(supersedes) if supersedes is not None else None,
        confidence=args.confidence,
        body=read_body(args),
        expected_updated_at=args.expected_updated_at,
        clear_confidence=bool(args.clear_confidence),
    )
    print(path)
    return 0


def run_experience_get(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    current_project_id = resolve_project_id(project, vault)
    source_project_id, separator, experience_id = args.source.partition("/")
    if not separator:
        source_project_id = current_project_id
        experience_id = args.source
    elif not source_project_id or not experience_id or "/" in experience_id:
        raise ValueError("source must use experience-id or project-id/experience-id")
    path, header, body = read_experience_at(vault, source_project_id, experience_id)
    print(
        json.dumps(
            {"header": header, "body": body, "path": str(path.relative_to(vault))},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def run_memory_upsert(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    tags = [] if args.clear_tags else args.tag
    path = upsert_memory_at(
        vault,
        resolve_project_id(project, vault),
        title=args.title,
        summary=args.summary,
        memory_id=args.memory_id,
        filename=None,
        tags=list(tags) if tags is not None else None,
        source_experiences=(
            list(args.source_experience) if args.source_experience is not None else None
        ),
        shared=bool(args.shared),
        confidence=args.confidence,
        body=read_body(args),
        expected_updated_at=args.expected_updated_at,
        clear_confidence=bool(args.clear_confidence),
    )
    print(path)
    return 0


def run_memory_get(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    current_project_id = resolve_project_id(project, vault)
    path, header, body = read_memory_at(
        vault,
        current_project_id,
        args.memory_id,
        scope=args.scope,
        project_id=args.project_id,
    )
    print(
        json.dumps(
            {"header": header, "body": body, "path": str(path.relative_to(vault))},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def run_experience_search(args: argparse.Namespace) -> int:
    return run_document_search(args, kind="experiences", statuses=list(args.status))


def run_memory_search(args: argparse.Namespace) -> int:
    return run_document_search(args, kind="memory", statuses=[])


def run_tag_browse(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    payload = browse_knowledge_tags(
        vault,
        resolve_project_id(project, vault),
        parent_tag=args.parent,
        all_projects=bool(args.all_projects),
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def run_tag_search(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    payload = search_knowledge_tags(
        vault,
        resolve_project_id(project, vault),
        terms=list(args.terms),
        all_projects=bool(args.all_projects),
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def run_tag_describe(args: argparse.Namespace) -> int:
    project = Path(args.project)
    vault = get_active_vault()
    project_id = resolve_project_id(project, vault)
    context_from_vault(vault, project_id)
    taxonomy = update_tag_description(
        vault,
        tag=args.tag,
        description=args.description,
        expected_updated_at=args.expected_updated_at,
    )
    payload = {
        "tag": args.tag,
        "description": taxonomy.descriptions[args.tag],
        "taxonomy_updated_at": taxonomy.updated_at,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def run_document_search(args: argparse.Namespace, *, kind: str, statuses: list[str]) -> int:
    filters = SearchFilters(
        document_ids=tuple(args.id),
        source_experiences=tuple(getattr(args, "source_experience", [])),
        related_experiences=tuple(getattr(args, "related_experience", [])),
        evidence_types=tuple(getattr(args, "evidence_type", [])),
        scopes=tuple(getattr(args, "scope", [])),
        confidences=tuple(args.confidence),
        recorded_from=(
            parse_datetime_filter(args.recorded_from, end_of_day=False)
            if args.recorded_from
            else None
        ),
        recorded_to=(
            parse_datetime_filter(args.recorded_to, end_of_day=True) if args.recorded_to else None
        ),
    )
    project = Path(args.project)
    vault = get_active_vault()
    entries = search_documents_at(
        vault,
        resolve_project_id(project, vault),
        kind=kind,
        terms=list(args.terms),
        project_ids=list(args.project_id),
        tags=list(args.tag),
        statuses=statuses,
        all_projects=bool(args.all_projects),
        filters=filters,
    )
    for entry in entries:
        print(
            f'project="{entry.project_id}" id="{entry.document_id}" '
            f'title="{entry.title}" path="{entry.path}"'
        )
    return 0


def run_apply_agents_md(args: argparse.Namespace) -> int:
    path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
    print(path)
    return 0


def run_mcp_serve(args: argparse.Namespace) -> int:
    del args
    from knowledge_refinery.mcp_server import serve

    serve()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.handler(args))
    except RefineryCliError as error:
        print(error.render(), file=sys.stderr)
        return error.exit_code
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
