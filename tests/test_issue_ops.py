from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.issue_ops import create_issue
from knowledge_refinery.issue_ops import get_issue
from knowledge_refinery.issue_ops import list_issue_tags
from knowledge_refinery.issue_ops import list_issues
from knowledge_refinery.issue_ops import maintain_issue_tag
from knowledge_refinery.issue_ops import update_issue
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    init_vault(root)
    for project_id in ("alpha", "beta"):
        project = tmp_path / project_id
        project.mkdir()
        setup_project(project, root, project_id=project_id)
    return root


def test_independent_issue_lifecycle_and_combined_filters(vault: Path) -> None:
    issue = create_issue(vault, title="検索改善", done_when="比較試験に成功する")
    unrelated = create_issue(vault, title="Other", projects=["beta"], tags=["検索"])
    assert issue["projects"] == []
    assert issue["status"] == "backlog"
    linked = update_issue(
        vault,
        issue["id"],
        expected_revision=1,
        add_projects=["beta", "alpha", "alpha"],
        add_tags=["検索", " bug ", "bug"],
        status="in_progress",
        reason="調査に着手",
    )
    assert linked["projects"] == ["alpha", "beta"]
    assert linked["tags"] == ["bug", "検索"]
    assert [
        item["id"] for item in list_issues(vault, project="beta", status="in_progress", tag="検索")
    ] == [issue["id"]]
    assert len(list_issues(vault)) == 2
    for revision, status in enumerate(("blocked", "ready", "done", "in_progress", "cancelled"), 2):
        linked = update_issue(
            vault,
            issue["id"],
            expected_revision=revision,
            status=status,
            reason="確認済み",
        )
    final = update_issue(
        vault,
        issue["id"],
        expected_revision=7,
        title="改善の見送り",
        description="別案を採用",
        remove_projects=["alpha", "beta"],
        remove_tags=["bug"],
    )
    assert final["projects"] == []
    assert final["tags"] == ["検索"]
    assert final["description"] == "別案を採用"
    assert final["history"][1]["changes"]["status"] == "in_progress"
    assert final["history"][-1]["revision"] == 8
    assert get_issue(vault, issue["id"]) == final
    assert get_issue(vault, unrelated["id"])["revision"] == 1


def test_updates_require_current_revision_and_meaningful_completion(vault: Path) -> None:
    issue = create_issue(vault, title="Task")
    path = vault / "issues.json"
    original = path.read_bytes()
    with pytest.raises(ValueError, match="reason"):
        update_issue(vault, issue["id"], expected_revision=1, status="in_progress")
    with pytest.raises(ValueError, match="completion criteria"):
        update_issue(vault, issue["id"], expected_revision=1, status="done", reason="tested")
    assert path.read_bytes() == original
    completed = update_issue(
        vault,
        issue["id"],
        expected_revision=1,
        done_when="Tests pass",
        status="done",
        reason="All tests passed",
    )
    assert completed["revision"] == 2
    with pytest.raises(RefineryCliError, match="Issue changed"):
        update_issue(vault, issue["id"], expected_revision=1, title="Stale write")
    with pytest.raises(ValueError, match="completion criteria"):
        update_issue(vault, issue["id"], expected_revision=2, done_when="")
    assert get_issue(vault, issue["id"]) == completed
    update_issue(vault, issue["id"], expected_revision=2, title=completed["title"])
    assert get_issue(vault, issue["id"])["revision"] == 2


def test_tag_maintenance_merges_and_removes_across_projects(vault: Path) -> None:
    first = create_issue(vault, title="A", projects=["alpha"], tags=["old", "new"])
    second = create_issue(vault, title="B", projects=["beta"], tags=["old"])
    assert list_issue_tags(vault) == [{"tag": "new", "count": 1}, {"tag": "old", "count": 2}]
    assert list_issue_tags(vault, project="beta") == [{"tag": "old", "count": 1}]
    assert set(maintain_issue_tag(vault, "old", replacement="new")) == {first["id"], second["id"]}
    assert list_issue_tags(vault) == [{"tag": "new", "count": 2}]
    assert get_issue(vault, first["id"])["revision"] == 2
    assert get_issue(vault, first["id"])["history"][0]["changes"]["tags"] == ["new", "old"]
    with pytest.raises(RefineryCliError):
        update_issue(vault, second["id"], expected_revision=1, title="Stale after rename")
    maintain_issue_tag(vault, "new")
    assert list_issue_tags(vault) == []
    assert all(issue["revision"] == 3 for issue in list_issues(vault))
    with pytest.raises(ValueError, match="does not exist"):
        maintain_issue_tag(vault, "missing")


def test_invalid_input_never_changes_store(vault: Path) -> None:
    issue = create_issue(vault, title="Task")
    original = (vault / "issues.json").read_bytes()
    with pytest.raises(ValueError):
        create_issue(vault, title=" ")
    with pytest.raises(ValueError):
        create_issue(vault, title="Unknown project", projects=["unknown"])
    with pytest.raises(ValueError):
        update_issue(vault, issue["id"], expected_revision=1, add_projects=["../escape"])
    with pytest.raises(ValueError, match="same project or tag"):
        update_issue(vault, issue["id"], expected_revision=1, add_tags=["x"], remove_tags=["x"])
    with pytest.raises(ValueError, match="status"):
        update_issue(vault, issue["id"], expected_revision=1, status="unknown", reason="test")
    with pytest.raises(ValueError):
        create_issue(vault, title="Empty tag", tags=[" "])
    with pytest.raises(ValueError, match="does not exist"):
        get_issue(vault, "../escape")
    assert (vault / "issues.json").read_bytes() == original


def test_existing_vault_needs_no_migration_and_rejects_redirected_store(vault: Path) -> None:
    assert list_issues(vault) == []
    assert list_issue_tags(vault) == []
    assert not (vault / "issues.json").exists()
    outside = vault.parent / "outside.json"
    outside.write_text("do not change")
    (vault / "issues.json").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        create_issue(vault, title="Task")
    with pytest.raises(ValueError, match="symlink"):
        list_issues(vault)
    assert outside.read_text() == "do not change"


@pytest.mark.parametrize("damage", ["json", "schema", "history", "duplicate"])
def test_corrupted_store_is_not_overwritten(vault: Path, damage: str) -> None:
    create_issue(vault, title="Original")
    path = vault / "issues.json"
    data = json.loads(path.read_text())
    if damage == "schema":
        data["schema_version"] = 99
    elif damage == "history":
        data["issues"][0]["history"] = []
    elif damage == "duplicate":
        data["issues"].append(data["issues"][0])
    path.write_text("{" if damage == "json" else json.dumps(data))
    original = path.read_bytes()
    with pytest.raises(ValueError):
        create_issue(vault, title="New")
    assert path.read_bytes() == original


def test_concurrent_writers_preserve_creates_and_reject_stale_updates(vault: Path) -> None:
    def create(index: int) -> str:
        return create_issue(vault, title=f"Task {index}")["id"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        identifiers = list(pool.map(create, range(8)))
    assert len(set(identifiers)) == len(list_issues(vault)) == 8

    def update(title: str) -> str:
        try:
            update_issue(vault, identifiers[0], expected_revision=1, title=title)
        except RefineryCliError:
            return "conflict"
        return "updated"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, ["First", "Second"]))
    assert sorted(outcomes) == ["conflict", "updated"]
    assert get_issue(vault, identifiers[0])["revision"] == 2
