from collections.abc import Mapping
import json
from pathlib import Path

from knowledge_refinery.knowledge_ops import CopyResult
from knowledge_refinery.knowledge_ops import UpsertKnowledgeResult
from knowledge_refinery.search_ops import KnowledgeSearchEntry
from knowledge_refinery.search_ops import SessionSearchEntry


def render_search_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def render_key_value_line(pairs: list[tuple[str, object]]) -> str:
    return " ".join(f"{key}={render_search_value(value)}" for key, value in pairs)


def render_apply_template_output(
    *,
    template_root: Path,
    target_root: Path,
    skill_destination: str,
    copied_count: int,
) -> list[str]:
    return [
        f"Applied template from: {template_root}",
        f"Target repository: {target_root}",
        f"Skill destination: .{skill_destination}/skills",
        f"Copied files: {copied_count}",
        "",
        "Next steps:",
        "1) Install `knowledge-refinery` with `uv tool install ...` "
        "in the environment that will run the CLI.",
        "2) Update the managed AGENTS.md or CLAUDE.md section with "
        "`knowledge-refinery update-agents-md --target ... --lang jp|en`.",
        f"3) Confirm .{skill_destination}/skills/, .refinery/shared/, and "
        "`.refinery/template-meta.yaml` were copied.",
        "4) Later template updates can be applied with "
        "`knowledge-refinery update-template --target ...`.",
        "5) Use `knowledge-refinery skills ...` for session, search, and review operations.",
        "6) Use sessions/*/meta.yaml as the single session metadata format.",
    ]


def render_update_template_output(
    *,
    template_root: Path,
    target_root: Path,
    skill_destination: str,
    copied_count: int,
) -> list[str]:
    return [
        f"Updated template from: {template_root}",
        f"Target repository: {target_root}",
        f"Skill destination: .{skill_destination}/skills",
        f"Updated files: {copied_count}",
        "",
        "Next steps:",
        "1) Reinstall `knowledge-refinery` in the environment that runs "
        "the CLI if the package source was updated.",
        "2) Refresh the managed AGENTS.md or CLAUDE.md section with "
        "`knowledge-refinery update-agents-md --target ... --lang jp|en`.",
        f"3) Review the updated diffs under .{skill_destination}/skills/ and .refinery/shared/.",
        "4) `.refinery/template-meta.yaml` is refreshed to match the CLI version used "
        "for this update.",
        "5) Existing .refinery/shared/state.md is preserved during template refreshes.",
        "6) Use `knowledge-refinery skills ...` for session, search, and review operations.",
        "7) Keep sessions/*/meta.yaml as the single session metadata format.",
    ]


def render_session_update_output(path: Path, meta: Mapping[str, object]) -> str:
    return render_key_value_line(
        [
            ("path", path.parent.as_posix()),
            ("session_id", str(meta.get("session_id", ""))),
            ("title", str(meta.get("title", ""))),
            ("task", str(meta.get("task", ""))),
            ("status", str(meta.get("status", ""))),
            ("phase", str(meta.get("phase", ""))),
            ("flow_status", str(meta.get("flow_status", ""))),
            ("next_action", str(meta.get("next_action", ""))),
        ]
    )


def render_upsert_knowledge_output(result: UpsertKnowledgeResult) -> str:
    status = "created" if result.created else "updated"
    return render_key_value_line(
        [
            ("status", status),
            ("path", result.path.as_posix()),
            ("knowledge_id", str(result.header.get("knowledge_id", ""))),
            ("knowledge_type", str(result.header.get("knowledge_type", ""))),
            ("title", str(result.header.get("title", ""))),
            ("summary", str(result.header.get("summary", ""))),
        ]
    )


def render_session_search_output(entries: list[SessionSearchEntry]) -> list[str]:
    if not entries:
        return ["No sessions found."]
    return [
        render_key_value_line(
            [
                ("path", entry.path.as_posix()),
                ("session_id", entry.session_id),
                ("title", entry.title),
                ("task", entry.task),
                ("status", entry.status),
                ("phase", entry.phase),
                ("flow_status", entry.flow_status),
                ("next_action", entry.next_action),
            ]
        )
        for entry in entries
    ]


def render_knowledge_search_output(entries: list[KnowledgeSearchEntry]) -> list[str]:
    if not entries:
        return ["No knowledge files found."]
    return [
        render_key_value_line(
            [
                ("path", entry.path.as_posix()),
                ("scope", entry.scope),
                ("knowledge_id", entry.knowledge_id),
                ("knowledge_type", entry.knowledge_type),
                ("title", entry.title),
                ("summary", entry.summary),
                ("tags", entry.tags),
                ("source_sessions", entry.source_sessions),
            ]
        )
        for entry in entries
    ]


def render_review_search_output(entries: list[KnowledgeSearchEntry]) -> list[str]:
    if not entries:
        return ["No review files found."]
    return [
        render_key_value_line(
            [
                ("path", entry.path.as_posix()),
                ("knowledge_id", entry.knowledge_id),
                ("knowledge_type", entry.knowledge_type),
                ("title", entry.title),
                ("summary", entry.summary),
                ("tags", entry.tags),
                ("source_sessions", entry.source_sessions),
            ]
        )
        for entry in entries
    ]


def render_copy_results_output(
    results: list[CopyResult],
    *,
    empty_message: str,
    copied_label: str,
    skipped_label: str,
    summary_prefix: str,
) -> list[str]:
    if not results:
        return [empty_message]

    lines: list[str] = []
    copied = 0
    skipped = 0
    for result in results:
        status = copied_label if result.copied else skipped_label
        lines.append(f"{status}\t{result.target.as_posix()}\tfrom={result.source.as_posix()}")
        if result.copied:
            copied += 1
        else:
            skipped += 1

    lines.append(f"{summary_prefix}: {copied_label}={copied} {skipped_label}={skipped}")
    return lines


def render_refresh_review_output(results: list[CopyResult]) -> list[str]:
    lines = [
        f"refreshed\t{result.target.as_posix()}\tfrom={result.source.as_posix()}"
        for result in results
    ]
    lines.append(f"Refreshed review files: {len(results)}")
    return lines
