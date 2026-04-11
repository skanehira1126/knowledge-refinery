from __future__ import annotations

from pathlib import Path
import shutil


SKILL_DESTINATION_CHOICES = ("codex", "agent")
SKILL_TEMPLATE_ROOT = "codex"
SKILL_DESTINATION_ROOTS = {
    "codex": ".codex",
    "agent": ".agent",
}
STATIC_TEMPLATE_COPY_PATHS = (("refinery", ".refinery"),)
PRESERVE_ON_FORCE_COPY = {
    ("refinery", "shared/state.md"),
}


def locate_template_root() -> Path:
    template_root = Path(__file__).resolve().parent / "template"
    if not template_root.is_dir():
        raise FileNotFoundError("Embedded template directory not found in the installed package.")
    return template_root


def copy_tree(
    src: Path, dst: Path, force: bool = False, skill_destination: str = "codex"
) -> list[Path]:
    if skill_destination not in SKILL_DESTINATION_CHOICES:
        raise ValueError(f"Unsupported skill destination: {skill_destination}")

    copied: list[Path] = []
    copy_paths = (
        (SKILL_TEMPLATE_ROOT, SKILL_DESTINATION_ROOTS[skill_destination]),
        *STATIC_TEMPLATE_COPY_PATHS,
    )
    for source_root_name, target_root_name in copy_paths:
        root_path = src / source_root_name
        if not root_path.exists():
            continue

        for path in root_path.rglob("*"):
            if "__pycache__" in path.parts or any(
                part.endswith((".egg-info", ".dist-info")) for part in path.parts
            ):
                continue

            rel = path.relative_to(root_path)
            target = dst / target_root_name / rel

            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if (
                force
                and target.exists()
                and (source_root_name, rel.as_posix()) in PRESERVE_ON_FORCE_COPY
            ):
                continue
            if target.exists() and not force:
                continue
            shutil.copy2(path, target)
            copied.append(target)
    return copied


def apply_template(
    target_root: Path, force: bool = False, skill_destination: str = "codex"
) -> tuple[Path, list[Path]]:
    template_root = locate_template_root()
    copied = copy_tree(
        template_root, target_root, force=force, skill_destination=skill_destination
    )
    return template_root, copied
