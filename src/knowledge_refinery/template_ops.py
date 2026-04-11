from __future__ import annotations

import shutil
from pathlib import Path

TEMPLATE_COPY_PATHS = (
    ("codex", ".codex"),
    ("refinery", ".refinery"),
)


def locate_template_root() -> Path:
    template_root = Path(__file__).resolve().parent / "template"
    if not template_root.is_dir():
        raise FileNotFoundError("Embedded template directory not found in the installed package.")
    return template_root


def copy_tree(src: Path, dst: Path, force: bool = False) -> list[Path]:
    copied: list[Path] = []
    for source_root_name, target_root_name in TEMPLATE_COPY_PATHS:
        root_path = src / source_root_name
        if not root_path.exists():
            continue

        for path in root_path.rglob("*"):
            if "__pycache__" in path.parts or any(part.endswith((".egg-info", ".dist-info")) for part in path.parts):
                continue

            rel = path.relative_to(root_path)
            target = dst / target_root_name / rel

            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and not force:
                continue
            shutil.copy2(path, target)
            copied.append(target)
    return copied


def apply_template(target_root: Path, force: bool = False) -> tuple[Path, list[Path]]:
    template_root = locate_template_root()
    copied = copy_tree(template_root, target_root, force=force)
    return template_root, copied
