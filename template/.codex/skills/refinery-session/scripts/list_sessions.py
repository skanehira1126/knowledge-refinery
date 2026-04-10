#!/usr/bin/env python3
"""List refinery sessions by reading session meta.yaml files."""

import argparse
from pathlib import Path


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        try:
            from ruamel.yaml import YAML  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "YAML parser is required. Install PyYAML or ruamel.yaml."
            ) from exc

        parser = YAML(typ="safe")
        return parser.load(text)


def parse_meta_yaml(path: Path) -> dict[str, object]:
    data = load_yaml(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"meta.yaml must contain a mapping: {path}")
    return data


def list_sessions(root: Path) -> list[tuple[Path, dict[str, object]]]:
    results: list[tuple[Path, dict[str, object]]] = []
    sessions_root = root / "sessions"
    if not sessions_root.exists():
        return results

    for meta_path in sorted(sessions_root.glob("*/meta.yaml")):
        results.append((meta_path, parse_meta_yaml(meta_path)))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List sessions from meta.yaml")
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
            f"{rel}	session_id={session_id}	status={status}	phase={phase}	flow_status={flow_status}	last_updated_at={updated}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
