from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from knowledge_refinery import handoff_ops
from knowledge_refinery.deep_search_ops import build_search_snapshot
from knowledge_refinery.experience_ops import search_documents_at
from knowledge_refinery.handoff_ops import Handoff
from knowledge_refinery.handoff_ops import archive_handoff_at
from knowledge_refinery.handoff_ops import create_handoff_at
from knowledge_refinery.handoff_ops import delete_handoff_at
from knowledge_refinery.handoff_ops import list_handoffs_at
from knowledge_refinery.handoff_ops import read_handoff_at
from knowledge_refinery.handoff_ops import validate_handoffs_at
from knowledge_refinery.tag_ops import browse_knowledge_tags
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project
from tests._support import write_markdown_document


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    init_vault(root)
    for name in ("first", "second"):
        project = tmp_path / name
        project.mkdir()
        setup_project(project, root, project_id=name)
    return root


def create(vault: Path, handoff_id: str = "snapshot-one", **options: str) -> Handoff:
    return create_handoff_at(
        vault,
        "first",
        handoff_id=handoff_id,
        title="検索の修正",
        goal="検索を直す",
        done_when="回帰テストが通る",
        body="## 現在の状態\n\nsrc/search.pyを修正中。仮説は未検証。",
        **options,
    )


def test_snapshot_lifecycle_preserves_content_and_other_tasks(vault: Path) -> None:
    first = create(vault, task_id="search-fix")
    unrelated = create(vault, "another-task")
    before = first.path.read_bytes()
    assert read_handoff_at(vault, "first", "snapshot-one").header["status"] == "active"
    assert first.path.read_bytes() == before
    assert first.as_dict(vault)["path"] == "projects/first/handoffs/snapshot-one.md"

    second = create(
        vault,
        "snapshot-two",
        supersedes="snapshot-one",
        expected_updated_at=str(first.header["updated_at"]),
    )
    old = read_handoff_at(vault, "first", "snapshot-one")
    assert old.body == first.body
    assert old.header["status"] == "archived"
    assert old.header["superseded_by"] == "snapshot-two"
    assert second.header["supersedes"] == "snapshot-one"
    assert second.header["task_id"] == "search-fix"
    assert [item.header["handoff_id"] for item in list_handoffs_at(vault, "first")] == [
        "snapshot-two",
        "another-task",
    ]
    assert len(list_handoffs_at(vault, "first", include_archived=True)) == 3
    assert list_handoffs_at(vault, "second") == []
    assert list_handoffs_at(vault, "first", task_id="search-fix") == [second]

    # Historical ID links remain after explicitly deleting a predecessor.
    assert (
        delete_handoff_at(
            vault,
            "first",
            "snapshot-one",
            expected_updated_at=str(old.header["updated_at"]),
        )["deleted"]
        is True
    )
    assert not old.path.exists()
    assert read_handoff_at(vault, "first", "snapshot-two").header["supersedes"] == "snapshot-one"
    assert read_handoff_at(vault, "first", "another-task") == unrelated


def test_conflicts_and_active_deletion_do_not_mutate_snapshots(vault: Path) -> None:
    first = create(vault, task_id="search-fix")
    before = first.path.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        create(vault)
    with pytest.raises(ValueError, match="active handoff"):
        create(vault, "new-id", task_id="search-fix")
    with pytest.raises(ValueError, match="stale"):
        create(vault, "new-id", supersedes="snapshot-one", expected_updated_at="stale")
    with pytest.raises(ValueError, match="task_id"):
        create(
            vault,
            "new-id",
            supersedes="snapshot-one",
            task_id="wrong-task",
            expected_updated_at=str(first.header["updated_at"]),
        )
    with pytest.raises(ValueError, match="Archive"):
        delete_handoff_at(
            vault, "first", "snapshot-one", expected_updated_at=str(first.header["updated_at"])
        )
    with pytest.raises(ValueError, match="stale"):
        archive_handoff_at(vault, "first", "snapshot-one", expected_updated_at="stale")
    assert first.path.read_bytes() == before
    assert len(list_handoffs_at(vault, "first", include_archived=True)) == 1

    archived = archive_handoff_at(
        vault, "first", "snapshot-one", expected_updated_at=str(first.header["updated_at"])
    )
    with pytest.raises(ValueError, match="stale"):
        delete_handoff_at(
            vault, "first", "snapshot-one", expected_updated_at=str(first.header["updated_at"])
        )
    assert read_handoff_at(vault, "first", "snapshot-one") == archived
    assert (
        archive_handoff_at(
            vault, "first", "snapshot-one", expected_updated_at=str(archived.header["updated_at"])
        )
        == archived
    )


def test_archive_cutoff_is_exclusive_and_never_deletes(vault: Path) -> None:
    first = create(vault)
    old = archive_handoff_at(
        vault, "first", "snapshot-one", expected_updated_at=str(first.header["updated_at"])
    )
    create(vault, "other")
    with pytest.raises(ValueError, match="include_archived"):
        list_handoffs_at(vault, "first", archived_before="2100-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="timezone"):
        list_handoffs_at(vault, "first", include_archived=True, archived_before="2100-01-01")
    assert (
        list_handoffs_at(
            vault, "first", include_archived=True, archived_before=str(old.header["archived_at"])
        )
        == []
    )
    assert list_handoffs_at(
        vault, "first", include_archived=True, archived_before="2100-01-01T00:00:00Z"
    ) == [old]
    assert old.path.exists()


def test_handoff_does_not_enter_knowledge_search_tags_or_deep_snapshot(
    vault: Path, tmp_path: Path
) -> None:
    create(vault)
    for kind in ("experiences", "memory"):
        assert (
            search_documents_at(
                vault,
                "first",
                kind=kind,
                terms=[],
                tags=[],
                statuses=[],
                project_ids=[],
                all_projects=True,
            )
            == []
        )
    manifest = build_search_snapshot(vault, "first", tmp_path / "snapshot")
    assert manifest["documents"] == []
    assert not list((tmp_path / "snapshot").rglob("handoffs"))
    assert all(tag["document_count"] == 0 for tag in browse_knowledge_tags(vault, "first")["tags"])


@pytest.mark.parametrize("handoff_id", ["", "../second", "Uppercase", "/tmp/escape"])
def test_invalid_id_cannot_escape_storage(vault: Path, handoff_id: str) -> None:
    with pytest.raises(ValueError, match="slug"):
        create(vault, handoff_id)


@pytest.mark.parametrize("location", ["file", "directory"])
def test_handoff_operations_refuse_redirected_storage(
    vault: Path, tmp_path: Path, location: str
) -> None:
    record = create(vault)
    if location == "file":
        target = record.path
        target.unlink()
        outside = tmp_path / "outside.md"
        outside.write_text("untouched", encoding="utf-8")
        target.symlink_to(outside)
    else:
        target = record.path.parent
        target.rename(target.with_name("original-handoffs"))
        outside = tmp_path / "outside"
        outside.mkdir()
        target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        read_handoff_at(vault, "first", "snapshot-one")
    with pytest.raises(ValueError, match="symlink"):
        list_handoffs_at(vault, "first")
    with pytest.raises(ValueError, match="symlink"):
        list_handoffs_at(vault)


def test_cross_project_listing_filters_and_fails_on_invalid_metadata(vault: Path) -> None:
    first = create(vault, task_id="shared-task")
    second = create_handoff_at(
        vault,
        "second",
        title="Other",
        goal="Goal",
        done_when="Done",
        body="Other state",
        handoff_id="snapshot-one",
        task_id="shared-task",
    )
    unrelated = create(vault, "unrelated")
    archived = archive_handoff_at(
        vault, "second", "snapshot-one", expected_updated_at=str(second.header["updated_at"])
    )
    assert list_handoffs_at(vault) == [unrelated, first]
    assert list_handoffs_at(vault, include_archived=True, task_id="shared-task") == [
        archived,
        first,
    ]
    assert list_handoffs_at(
        vault, include_archived=True, archived_before="2100-01-01T00:00:00Z"
    ) == [archived]
    with pytest.raises(ValueError, match="requires include_archived"):
        list_handoffs_at(vault, archived_before="2100-01-01T00:00:00Z")
    (vault / "projects" / "second" / "project.yaml").write_text("invalid: true\n")
    with pytest.raises(ValueError):
        list_handoffs_at(vault)
    with pytest.raises(ValueError):
        read_handoff_at(vault, "second", "snapshot-one")
    assert list_handoffs_at(vault, "first") == [unrelated, first]


def test_failed_predecessor_archive_preserves_original(
    vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = create(vault)
    before = first.path.read_bytes()
    real_write = handoff_ops.atomic_write_text

    def fail_archive(path: Path, content: str) -> None:
        if path == first.path:
            raise OSError("simulated disk error")
        real_write(path, content)

    monkeypatch.setattr(handoff_ops, "atomic_write_text", fail_archive)
    with pytest.raises(OSError, match="disk error"):
        create(
            vault,
            "new-id",
            supersedes="snapshot-one",
            expected_updated_at=str(first.header["updated_at"]),
        )
    assert first.path.read_bytes() == before
    assert len(list_handoffs_at(vault, "first", include_archived=True)) == 1


def test_concurrent_replacements_have_one_winner(vault: Path) -> None:
    first = create(vault)

    def replace(handoff_id: str) -> str:
        try:
            create(
                vault,
                handoff_id,
                supersedes="snapshot-one",
                expected_updated_at=str(first.header["updated_at"]),
            )
            return "created"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(replace, ["new-a", "new-b"]))
    assert sorted(results) == ["conflict", "created"]
    active = list_handoffs_at(vault, "first")
    assert len(active) == 1
    assert (
        read_handoff_at(vault, "first", "snapshot-one").header["superseded_by"]
        == active[0].header["handoff_id"]
    )


def test_existing_project_lazily_creates_handoff_area(vault: Path) -> None:
    root = vault / "projects" / "first" / "handoffs"
    root.rmdir()
    assert list_handoffs_at(vault, "first") == []
    assert not root.exists()
    record = create(vault)
    assert record.path.parent == root
    assert read_handoff_at(vault, "first", "snapshot-one") == record


@pytest.mark.parametrize(
    "changes",
    [
        {"project_id": "second"},
        {"status": "archived", "archived_at": None},
        {"created_at": "2100-01-01T00:00:00Z"},
        {"superseded_by": "other"},
    ],
)
def test_invalid_snapshots_fail_exact_get_and_audit(
    vault: Path, changes: dict[str, object]
) -> None:
    record = create(vault)
    write_markdown_document(record.path, {**record.header, **changes}, record.body)
    with pytest.raises(ValueError):
        read_handoff_at(vault, "first", "snapshot-one")
    checked, errors = validate_handoffs_at(vault, "first")
    assert checked == 0
    assert errors[0]["path"] == "projects/first/handoffs/snapshot-one.md"


def test_audit_detects_incomplete_replacement(vault: Path) -> None:
    first = create(vault)
    path = first.path.with_name("other.md")
    write_markdown_document(
        path,
        {
            **first.header,
            "handoff_id": "other",
            "supersedes": "snapshot-one",
        },
        first.body,
    )
    _, errors = validate_handoffs_at(vault, "first")
    assert any("Duplicate active" in error["error"] for error in errors)


def test_empty_content_cannot_be_saved(vault: Path) -> None:
    with pytest.raises(ValueError, match="body"):
        create_handoff_at(vault, "first", title="Task", goal="Goal", done_when="Done", body=" ")
    assert list_handoffs_at(vault, "first", include_archived=True) == []
