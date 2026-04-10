#!/usr/bin/env python3
"""List refinery sessions by reading session meta.json files."""

import argparse
import json
from pathlib import Path


def parse_meta_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"meta.json must contain a mapping: {path}")
    return data


def list_sessions(root: Path) -> list[tuple[Path, dict[str, object]]]:
    results: list[tuple[Path, dict[str, object]]] = []
    sessions_root = root / "sessions"
    if not sessions_root.exists():
        return results

    for meta_path in sorted(sessions_root.glob("*/meta.json")):
        results.append((meta_path, parse_meta_json(meta_path)))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List sessions from meta.json")
    parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
