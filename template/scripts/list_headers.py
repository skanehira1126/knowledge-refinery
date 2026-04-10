#!/usr/bin/env python3
"""List markdown front matter headers under a refinery directory."""


import argparse
from pathlib import Path


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}

    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def list_headers(root: Path) -> list[tuple[Path, dict[str, str]]]:
    results: list[tuple[Path, dict[str, str]]] = []
    for path in sorted(root.rglob("*.md")):
        header = parse_front_matter(path.read_text(encoding="utf-8"))
        if header:
            results.append((path, header))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List markdown headers in refinery")
    parser.add_argument("--root", default=".refinery", help="Refinery root directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    entries = list_headers(root)

    if not entries:
        print("No front matter headers found.")
        return 0

    for path, header in entries:
        rel = path.as_posix()
        title = header.get("title", "")
        desc = header.get("description", "")
        print(f"{rel}\ttitle={title}\tdescription={desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
