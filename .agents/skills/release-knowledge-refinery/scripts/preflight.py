from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[4]
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _package_version() -> str | None:
    source = _read("src/knowledge_refinery/__init__.py")
    match = re.search(r'^__version__ = "([^"]+)"$', source, re.M)
    return match.group(1) if match else None


def _operational_files() -> list[Path]:
    candidates = [ROOT / ".mcp.json"]
    candidates.extend((ROOT / ".github" / "workflows").glob("*.yml"))
    candidates.extend((ROOT / ".github" / "workflows").glob("*.yaml"))
    candidates.extend((ROOT / "scripts").glob("*.py"))
    candidates.extend((ROOT / "scripts").glob("*.sh"))
    return sorted(path for path in candidates if path.is_file())


def validate(version: str) -> list[str]:
    errors: list[str] = []
    if not VERSION_RE.fullmatch(version):
        return [f"version must use X.Y.Z: {version}"]

    python_version = _package_version()
    plugin_version = json.loads(_read(".codex-plugin/plugin.json")).get("version")
    if python_version != version:
        errors.append(f"Python package version is {python_version!r}, expected {version!r}")
    if plugin_version != version:
        errors.append(f"Plugin version is {plugin_version!r}, expected {version!r}")

    required_text = {
        "docs/schema.md": f"cli_version: {version}",
        "tests/test_mcp_server.py": f'"version": "{version}"',
        "tests/test_cli_v2.py": f'"detail": "cli={version},',
    }
    for relative_path, expected in required_text.items():
        if expected not in _read(relative_path):
            errors.append(f"{relative_path} does not contain {expected!r}")

    if _git("ls-files", "uv.lock"):
        errors.append("uv.lock must not be tracked")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "uv.lock"],
        cwd=ROOT,
        check=False,
    )
    if ignored.returncode != 0:
        errors.append("uv.lock must be ignored")

    frozen_flag = "--" + "frozen"
    for path in _operational_files():
        if frozen_flag in path.read_text(encoding="utf-8"):
            errors.append(f"frozen lockfile resolution remains in {path.relative_to(ROOT)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Knowledge Refinery release invariants")
    parser.add_argument("--version", required=True, help="release version without the v prefix")
    args = parser.parse_args()

    errors = validate(args.version)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Release preflight passed for {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
