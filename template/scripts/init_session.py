#!/usr/bin/env python3
"""Initialize a refinery session directory.

session_id format: YYYYMMDDTHHMMSSZ-<random>
"""


import argparse
import datetime as dt
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


def init_session(root: Path, task: str, kind: str) -> Path:
    session_id = generate_session_id()
    session_root = root / "sessions" / session_id

    for rel in ("raw", "flow"):
        (session_root / rel).mkdir(parents=True, exist_ok=True)

    created_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_yaml = (
        f"session_id: {session_id}\n"
        f"kind: {kind}\n"
        f"task: {task}\n"
        f"created_at: {created_at}\n"
        "status: active\n"
        "base_shared_state_version: 1\n"
    )
    write_text(session_root / "meta.yaml", meta_yaml)

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
    parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session_root = init_session(Path(args.root), task=args.task, kind=args.kind)
    print(session_root.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
