#!/usr/bin/env python3
"""Copy refinery template files into a target repository."""

import argparse
import shutil
from pathlib import Path


def copy_tree(src: Path, dst: Path, force: bool = False) -> list[Path]:
    copied: list[Path] = []
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dst / rel

        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            continue
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply refinery template to a repository")
    parser.add_argument("--target", default=".", help="target repository path")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    tool_root = Path(__file__).resolve().parents[1]
    template_root = tool_root / "template"
    target_root = Path(args.target).resolve()

    copied = copy_tree(template_root, target_root, force=args.force)

    print(f"Applied template from: {template_root}")
    print(f"Target repository: {target_root}")
    print(f"Copied files: {len(copied)}")
    print("\nNext steps:")
    print("1) Append template/AGENTS.append.md content into your repo AGENTS.md")
    print("2) Confirm skills:")
    print("   - .codex/skills/refinery-session/SKILL.md")
    print("   - .codex/skills/refinery-shared/SKILL.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
