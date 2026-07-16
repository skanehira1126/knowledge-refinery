from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import time

import pytest

from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.storage_ops import atomic_write_text
from knowledge_refinery.storage_ops import interprocess_lock
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


def test_atomic_write_replaces_content_without_temporary_files(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("old\n", encoding="utf-8")

    atomic_write_text(path, "new\n")

    assert path.read_text(encoding="utf-8") == "new\n"
    assert list(tmp_path.glob(".config.yaml.*.tmp")) == []


def test_interprocess_lock_times_out_and_recovers_stale_lock(tmp_path: Path) -> None:
    target = tmp_path / "experience.md"
    with interprocess_lock(target, timeout=0.1):
        with pytest.raises(TimeoutError, match="document lock"):
            with interprocess_lock(target, timeout=0.02):
                pass

    lock_path = tmp_path / ".experience.md.lock"
    lock_path.write_text("abandoned", encoding="ascii")
    stale_time = time.time() - 120
    os.utime(lock_path, (stale_time, stale_time))

    with interprocess_lock(target, timeout=0.1, stale_after=60):
        assert lock_path.is_file()
    assert not lock_path.exists()


def _configured_vault(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    project = tmp_path / "project"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="project")
    return vault, project


def test_concurrent_experience_updates_remain_coherent(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)

    def write(index: int) -> None:
        upsert_experience_at(
            vault,
            "project",
            title=f"title-{index}",
            purpose=f"purpose-{index}",
            status="completed",
            experience_id="concurrent",
            filename=None,
            tags=[],
            evidence=[],
            related_experiences=[],
            supersedes=[],
            confidence="medium",
            body=f"body-{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(24)))

    path = vault / "projects" / "project" / "experiences" / "concurrent.md"
    header, body = split_front_matter(path.read_text(encoding="utf-8"))
    final_index = str(header["title"]).removeprefix("title-")
    assert header["purpose"] == f"purpose-{final_index}"
    assert body.strip() == f"body-{final_index}"
    assert not path.with_name(f".{path.name}.lock").exists()
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_concurrent_memory_updates_remain_coherent(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)
    upsert_experience_at(
        vault,
        "project",
        title="source",
        purpose="support memory",
        status="completed",
        experience_id="source",
        filename=None,
        tags=[],
        evidence=[],
        related_experiences=[],
        supersedes=[],
        confidence="high",
        body="source",
    )

    initial_path = upsert_memory_at(
        vault,
        "project",
        title="initial-memory",
        summary="initial-summary",
        memory_id="concurrent-memory",
        filename=None,
        tags=[],
        source_experiences=["source"],
        shared=False,
        confidence="high",
        body="initial-body",
    )
    initial_header, _ = split_front_matter(initial_path.read_text(encoding="utf-8"))
    revision = str(initial_header["updated_at"])

    def write(index: int) -> bool:
        try:
            upsert_memory_at(
                vault,
                "project",
                title=f"memory-{index}",
                summary=f"summary-{index}",
                memory_id="concurrent-memory",
                filename=None,
                tags=[],
                source_experiences=["source"],
                shared=False,
                confidence="high",
                body=f"memory-body-{index}",
                expected_updated_at=revision,
            )
        except ValueError as error:
            assert "stale" in str(error)
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(write, range(24)))

    assert sum(results) == 1
    path = vault / "projects" / "project" / "memory" / "concurrent-memory.md"
    header, body = split_front_matter(path.read_text(encoding="utf-8"))
    final_index = str(header["title"]).removeprefix("memory-")
    assert header["summary"] == f"summary-{final_index}"
    assert body.strip() == f"memory-body-{final_index}"
    assert not path.with_name(f".{path.name}.lock").exists()
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
