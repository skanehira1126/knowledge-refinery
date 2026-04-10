#!/usr/bin/env python3
"""Initialize a refinery session directory.

session_id format: YYYYMMDDTHHMMSSZ-<random>
"""

import argparse
import datetime as dt
import json
import secrets
import string
from pathlib import Path


ALPHABET = string.ascii_lowercase + string.digits


def generate_session_id(now: dt.datetime | None = None, suffix_len: int = 6) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(suffix_len))
    return f"{timestamp}-{suffix}"



def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_session(
    root: Path,
    task: str,
    kind: str,
    title: str,
    created_by: str,
    repository: str | None,
    domain: str | None,
) -> Path:
    session_id = generate_session_id()
    session_root = root / "sessions" / session_id

    for rel in ("raw", "flow"):
        (session_root / rel).mkdir(parents=True, exist_ok=True)

    created_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "session_id": session_id,
        "kind": kind,
        "title": title,
        "task": task,
        "created_at": created_at,
        "created_by": created_by,
        "repository": repository,
        "domain": domain,
        "status": "active",
        "phase": "capture",
        "current_step": "session initialized",
        "next_action": "raw に初期証拠を追加する",
        "last_updated_at": created_at,
        "closed_at": None,
        "blocked_reason": None,
        "resume_condition": None,
        "parent_session_id": None,
        "child_session_ids": [],
        "related_sessions": [],
        "depends_on": [],
        "supersedes": [],
        "superseded_by": None,
        "evidence_status": "collecting",
        "flow_status": "not_started",
        "synthesis_status": "not_started",
        "coverage_status": "unknown",
        "confidence": "low",
        "raw_item_count": 0,
        "flow_item_count": 0,
        "last_flow_update_at": None,
    }
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    write_text(session_root / "meta.json", meta_json)

    state_md = (
        "---\n"
        f"title: Session State ({session_id})\n"
        "description: このセッションの現在地\n"
        "---\n\n"
        "- 目的:\n"
        "- 進捗:\n"
        "- 次アクション:\n"
    )
    write_text(session_root / "state.md", state_md)

    return session_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a refinery session")
    parser.add_argument("--task", required=True, help="Task summary")
    parser.add_argument("--kind", default="task", help="Session kind (default: task)")
    parser.add_argument("--title", default=None, help="Session title (default: same as --task)")
    parser.add_argument(
        "--created-by",
        default="user",
        choices=["user", "llm"],
        help="Session creator (default: user)",
    )
    parser.add_argument("--repository", default=None, help="Repository name")
    parser.add_argument("--domain", default=None, help="Session domain")
    parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
