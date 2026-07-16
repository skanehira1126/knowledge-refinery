from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

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
from knowledge_refinery.experience_ops import search_documents_at
from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import enable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import inspect_project
from knowledge_refinery.vault_ops import resolve_project_id
from knowledge_refinery.vault_ops import setup_project


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
    vault_init.add_argument("--force", action="store_true", help="refresh managed template files")
    vault_init.set_defaults(handler=run_vault_init)
    vault_configure = vault_subparsers.add_parser(
        "configure", help="Set the active vault used by the local MCP server"
    )
    vault_configure.add_argument("--root", required=True, help="central refinery repository path")
    vault_configure.set_defaults(handler=run_vault_configure)

    project_parser = subparsers.add_parser("project", help="Connect a project to a refinery")
    project_subparsers = project_parser.add_subparsers(dest="project_command", required=True)
    project_setup = project_subparsers.add_parser(
        "setup", help="Create a project area and link it as .refinery"
    )
    project_setup.add_argument("--target", default=".", help="project repository path")
    project_setup.add_argument("--vault", required=True, help="central refinery repository path")
    project_setup.add_argument("--project-id", default=None, help="stable project slug")
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
    project_enable.add_argument("--target", default=".", help="project repository path")
    project_enable.add_argument(
        "--vault", default=None, help="central vault; defaults to the active vault"
    )
    project_enable.add_argument(
        "--link",
        action="store_true",
        help="optionally create a human-facing .refinery symlink",
    )
    add_guide_arguments(project_enable)
    project_enable.set_defaults(handler=run_project_enable)

    project_disable = project_subparsers.add_parser(
        "disable", help="Disable integration without deleting central knowledge"
    )
    project_disable.add_argument("--target", default=".", help="project repository path")
    project_disable.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    project_disable.set_defaults(handler=run_project_disable)

    project_status = project_subparsers.add_parser(
        "status", help="Inspect repository integration and active-vault consistency"
    )
    project_status.add_argument("--target", default=".", help="project repository path")
    project_status.add_argument("--filename", choices=GUIDE_FILENAME_CHOICES, default="AGENTS.md")
    project_status.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    project_status.set_defaults(handler=run_project_status)

    experience_parser = subparsers.add_parser("experience", help="Record and search experiences")
    experience_subparsers = experience_parser.add_subparsers(
        dest="experience_command", required=True
    )
    experience_upsert = experience_subparsers.add_parser(
        "upsert", help="Create or update one integrated experience document"
    )
    experience_upsert.add_argument("--project", default=".", help="configured project path")
    experience_upsert.add_argument("--experience-id", default=None, help="stable experience ID")
    experience_upsert.add_argument("--title", required=True, help="experience title")
    experience_upsert.add_argument("--purpose", required=True, help="purpose of the attempt")
    experience_upsert.add_argument(
        "--status",
        choices=EXPERIENCE_STATUS_CHOICES,
        default="completed",
        help="experience outcome state",
    )
    experience_upsert.add_argument("--tag", action="append", default=[], help="search tag")
    experience_upsert.add_argument(
        "--evidence", action="append", default=[], help="evidence reference; repeatable"
    )
    experience_upsert.add_argument(
        "--related-experience", action="append", default=[], help="related experience ID"
    )
    experience_upsert.add_argument(
        "--supersedes", action="append", default=[], help="superseded experience ID"
    )
    experience_upsert.add_argument("--confidence", choices=CONFIDENCE_CHOICES, default=None)
    experience_upsert.add_argument(
        "--expected-updated-at",
        default=None,
        help="revision returned by a prior read; required when updating existing experience",
    )
    add_body_arguments(experience_upsert)
    experience_upsert.set_defaults(handler=run_experience_upsert)

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
    memory_upsert.add_argument("--project", default=".", help="configured project path")
    memory_upsert.add_argument("--memory-id", default=None, help="stable memory ID")
    memory_upsert.add_argument("--title", required=True, help="memory title")
    memory_upsert.add_argument("--summary", required=True, help="reusable principle")
    memory_upsert.add_argument("--tag", action="append", default=[], help="search tag")
    memory_upsert.add_argument(
        "--source-experience",
        action="append",
        default=[],
        help="experience ID supporting this memory",
    )
    memory_upsert.add_argument("--shared", action="store_true", help="write to shared/memory")
    memory_upsert.add_argument("--confidence", choices=CONFIDENCE_CHOICES, default=None)
    memory_upsert.add_argument(
        "--expected-updated-at",
        default=None,
        help="revision returned by a prior read; required when updating existing memory",
    )
    add_body_arguments(memory_upsert)
    memory_upsert.set_defaults(handler=run_memory_upsert)

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

    agents_parser = subparsers.add_parser(
        "update-agents-md", help="Update the managed refinery guidance block"
    )
    agents_parser.add_argument("--target", default=".")
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
    parser.add_argument("--project", default=".", help="configured project path")
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
    result = init_vault(Path(args.root), force=bool(args.force))
    config = set_active_vault(result.root)
    print(f"Refinery initialized: {result.root}")
    print(f"Active vault configured: {config}")
    print(f"Created or updated files: {len(result.changed)}")
    return 0


def run_vault_configure(args: argparse.Namespace) -> int:
    path = set_active_vault(Path(args.root))
    print(f"Active vault configured: {path}")
    return 0


def run_project_setup(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    result = setup_project(
        Path(args.target),
        vault,
        project_id=args.project_id,
        create_link=bool(args.link),
    )
    set_active_vault(vault)
    print(f"Project configured: {result.project_id}")
    print(f"Project config: {result.config_path}")
    print(f"Refinery store: {result.project_store}")
    if result.link_path is not None:
        print(f"Optional refinery link: {result.link_path}")
    if args.agents:
        agents_path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
        print(f"Managed repository guidance: {agents_path}")
    return 0


def run_project_enable(args: argparse.Namespace) -> int:
    vault = Path(args.vault) if args.vault is not None else get_active_vault()
    result = enable_project(Path(args.target), vault, create_link=bool(args.link))
    if args.vault is not None:
        set_active_vault(vault)
    agents_path = apply_agents_md(Path(args.target), lang=args.lang, filename=args.filename)
    print(f"Project enabled: {result.project_id}")
    print(f"Project config: {result.config_path}")
    print(f"Refinery store: {result.project_store}")
    if result.link_path is not None:
        print(f"Optional refinery link: {result.link_path}")
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
    return {
        "state": status.state,
        "ready": status.ready,
        "project_root": str(status.project_root),
        "config_path": str(status.config_path),
        "config_exists": status.config_exists,
        "config_valid": status.config_valid,
        "config_error": status.config_error,
        "project_id": status.project_id,
        "enabled": status.enabled,
        "active_vault": str(status.vault_root) if status.vault_root is not None else None,
        "active_vault_error": vault_error,
        "vault_registered": status.vault_registered,
        "project_store": (str(status.project_store) if status.project_store is not None else None),
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
        documents = {"name": "vault_documents", "ok": False, "detail": str(error)}
        return runtime, documents
    errors = validation.get("errors", [])
    documents = {
        "name": "vault_documents",
        "ok": bool(validation.get("valid")),
        "detail": f"checked={validation.get('checked', 0)}, errors={len(errors)}",
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
            "ok": project["ready"],
            "detail": project["state"],
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
    path = upsert_experience_at(
        get_active_vault(),
        resolve_project_id(project),
        title=args.title,
        purpose=args.purpose,
        status=args.status,
        experience_id=args.experience_id,
        filename=None,
        tags=list(args.tag),
        evidence=list(args.evidence),
        related_experiences=list(args.related_experience),
        supersedes=list(args.supersedes),
        confidence=args.confidence,
        body=read_body(args),
        expected_updated_at=args.expected_updated_at,
    )
    print(path)
    return 0


def run_memory_upsert(args: argparse.Namespace) -> int:
    project = Path(args.project)
    path = upsert_memory_at(
        get_active_vault(),
        resolve_project_id(project),
        title=args.title,
        summary=args.summary,
        memory_id=args.memory_id,
        filename=None,
        tags=list(args.tag),
        source_experiences=list(args.source_experience),
        shared=bool(args.shared),
        confidence=args.confidence,
        body=read_body(args),
        expected_updated_at=args.expected_updated_at,
    )
    print(path)
    return 0


def run_experience_search(args: argparse.Namespace) -> int:
    return run_document_search(args, kind="experiences", statuses=list(args.status))


def run_memory_search(args: argparse.Namespace) -> int:
    return run_document_search(args, kind="memory", statuses=[])


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
    entries = search_documents_at(
        get_active_vault(),
        resolve_project_id(project),
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
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
