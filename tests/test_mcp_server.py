from pathlib import Path
from typing import Any
from typing import cast

import pytest

from knowledge_refinery.config_ops import set_active_vault
from knowledge_refinery.mcp_server import refinery_browse_knowledge_tags
from knowledge_refinery.mcp_server import refinery_delete_experience
from knowledge_refinery.mcp_server import refinery_delete_memory
from knowledge_refinery.mcp_server import refinery_get_experience
from knowledge_refinery.mcp_server import refinery_get_memory
from knowledge_refinery.mcp_server import refinery_get_project_metadata
from knowledge_refinery.mcp_server import refinery_info
from knowledge_refinery.mcp_server import refinery_list_projects
from knowledge_refinery.mcp_server import refinery_record_experience
from knowledge_refinery.mcp_server import refinery_record_memory
from knowledge_refinery.mcp_server import refinery_search_experiences
from knowledge_refinery.mcp_server import refinery_search_knowledge_tags
from knowledge_refinery.mcp_server import refinery_search_memory
from knowledge_refinery.mcp_server import refinery_update_project_metadata
from knowledge_refinery.mcp_server import refinery_update_tag_description
from knowledge_refinery.mcp_server import refinery_validate
from knowledge_refinery.tag_ops import TAG_TAXONOMY
from knowledge_refinery.vault_ops import disable_project
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import read_vault_id
from knowledge_refinery.vault_ops import setup_project


def configured_mcp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("REFINERY_CONFIG", str(tmp_path / "config.yaml"))
    vault = tmp_path / "refinery"
    project = tmp_path / "pybr"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="pybr")
    set_active_vault(vault)
    return vault


def test_local_mcp_records_searches_and_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"

    recorded = refinery_record_experience(
        project_path=str(project),
        title="Boruta検証",
        purpose="特徴量を選択する",
        status="completed",
        body="## 試したこと\n\nBoruta\n",
        evidence=[
            {
                "type": "file",
                "path": "notebooks/boruta.ipynb",
                "git_state": "untracked",
                "retention": "reference",
            }
        ],
        tags=["domain/ml"],
        confidence="medium",
        experience_id="boruta-trial",
    )

    metadata = refinery_get_project_metadata(str(project))
    assert metadata["project_id"] == "pybr"
    assert refinery_list_projects() == [metadata]
    updated_metadata = refinery_update_project_metadata(
        project_path=str(project),
        name="Pybr",
        summary="特徴量選択の実験プロジェクト",
        tags=["ml"],
        technologies=["Python"],
        expected_updated_at=str(metadata["updated_at"]),
    )
    assert updated_metadata["summary"] == "特徴量選択の実験プロジェクト"
    tagged_metadata = refinery_update_project_metadata(
        project_path=str(project),
        tags=["ml", "feature-selection"],
        expected_updated_at=str(updated_metadata["updated_at"]),
    )
    assert tagged_metadata["name"] == "Pybr"
    assert tagged_metadata["summary"] == "特徴量選択の実験プロジェクト"
    assert tagged_metadata["tags"] == ["ml", "feature-selection"]
    assert tagged_metadata["technologies"] == ["Python"]
    assert refinery_list_projects() == [tagged_metadata]
    assert refinery_info() == {
        "version": "0.2.0",
        "schema_version": 2,
        "project_metadata_schema_version": 1,
        "tag_taxonomy_schema_version": 1,
        "active_vault_id": read_vault_id(vault),
    }
    assert recorded["experience_id"] == "boruta-trial"
    assert recorded["updated_at"]
    assert (
        refinery_search_experiences(
            project_path=str(project),
            evidence_types=["file"],
            experience_ids=["boruta-trial"],
        )[0]["id"]
        == "boruta-trial"
    )
    header = refinery_get_experience(str(project), "boruta-trial")["header"]
    assert isinstance(header, dict)
    assert header["confidence"] == "medium"

    memory = refinery_record_memory(
        project_path=str(project),
        title="特徴量選択の原則",
        summary="相関グループも確認する",
        source_experiences=["boruta-trial"],
        confidence="medium",
        memory_id="feature-selection",
    )
    assert memory["memory_id"] == "feature-selection"
    assert memory["status"] == "active"
    assert memory["superseded_by"] is None
    assert memory["updated_at"]
    read_memory = refinery_get_memory(str(project), "feature-selection")
    assert read_memory["header"]["summary"] == "相関グループも確認する"
    assert (
        refinery_search_memory(project_path=str(project), source_experiences=["boruta-trial"])[0][
            "id"
        ]
        == "feature-selection"
    )
    assert refinery_validate() == {"valid": True, "checked": 3, "errors": []}


def test_mcp_browses_searches_and_describes_knowledge_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="検索性能",
        purpose="timeoutを調査する",
        status="completed",
        body="調査結果",
        tags=["issue/performance/timeout"],
        experience_id="search-timeout",
    )

    root = refinery_browse_knowledge_tags(str(project))
    issue = next(item for item in root["tags"] if item["tag"] == "issue")
    assert issue["description"] == "発生した問題や障害の分類"
    assert issue["document_count"] == 1
    children = refinery_browse_knowledge_tags(str(project), parent_tag="issue")
    assert [item["tag"] for item in children["tags"]] == ["issue/performance"]

    described = refinery_update_tag_description(
        project_path=str(project),
        tag="issue/performance",
        description="実行速度と資源効率の問題",
        expected_updated_at=root["taxonomy_updated_at"],
    )
    assert described["taxonomy_updated_at"]
    matches = refinery_search_knowledge_tags(str(project), terms=["資源効率"])
    assert [item["tag"] for item in matches["tags"]] == ["issue/performance"]
    assert refinery_validate() == {"valid": True, "checked": 3, "errors": []}


def test_validate_reports_malformed_tag_taxonomy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    (vault / TAG_TAXONOMY).write_text(
        "schema_version: 1\nupdated_at: invalid\ntags: {}\n", encoding="utf-8"
    )

    result = refinery_validate()

    assert result["valid"] is False
    assert result["errors"][0]["path"] == TAG_TAXONOMY
    assert "ISO 8601" in result["errors"][0]["error"]


def test_mcp_reads_qualified_experience_and_shared_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    first = tmp_path / "pybr"
    second = tmp_path / "vision"
    second.mkdir()
    setup_project(second, vault, project_id="vision")
    for project, experience_id in ((first, "first-trial"), (second, "second-trial")):
        refinery_record_experience(
            project_path=str(project),
            title=experience_id,
            purpose="shared evidence",
            status="completed",
            body=f"body for {experience_id}",
            experience_id=experience_id,
        )

    qualified = refinery_get_experience(str(first), "vision/second-trial")
    assert qualified["body"] == "body for second-trial"
    recorded = refinery_record_memory(
        project_path=str(first),
        title="shared rule",
        summary="works in two projects",
        source_experiences=["pybr/first-trial", "vision/second-trial"],
        shared=True,
        memory_id="shared-rule",
    )
    memory = refinery_get_memory(str(first), "shared-rule", scope="shared")

    assert memory["header"]["source_experiences"] == [
        "pybr/first-trial",
        "vision/second-trial",
    ]
    assert memory["header"]["updated_at"] == recorded["updated_at"]
    shared_entry = refinery_search_memory(
        str(first), memory_ids=["shared-rule"], scopes=["shared"]
    )[0]
    assert shared_entry["scope"] == "shared"
    assert shared_entry["project_id"] is None


def test_memory_update_requires_current_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="source",
        purpose="support memory",
        status="completed",
        body="source",
        experience_id="source",
    )
    created = refinery_record_memory(
        project_path=str(project),
        title="rule",
        summary="first",
        source_experiences=["source"],
        memory_id="rule",
    )

    with pytest.raises(ValueError, match="expected_updated_at"):
        refinery_record_memory(
            project_path=str(project),
            title="rule",
            summary="unsafe overwrite",
            source_experiences=["source"],
            memory_id="rule",
        )
    with pytest.raises(ValueError, match="stale"):
        refinery_record_memory(
            project_path=str(project),
            title="rule",
            summary="stale overwrite",
            source_experiences=["source"],
            memory_id="rule",
            expected_updated_at="stale",
        )

    updated = refinery_record_memory(
        project_path=str(project),
        title="rule",
        summary="safe update",
        source_experiences=["source"],
        memory_id="rule",
        expected_updated_at=created["updated_at"],
    )
    assert updated["updated_at"] != created["updated_at"]
    assert refinery_get_memory(str(project), "rule")["header"]["summary"] == "safe update"


def test_experience_update_requires_current_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    created = refinery_record_experience(
        project_path=str(project),
        title="trial",
        purpose="first",
        status="completed",
        body="first",
        experience_id="trial",
    )

    with pytest.raises(ValueError, match="expected_updated_at"):
        refinery_record_experience(
            project_path=str(project),
            title="trial",
            purpose="unsafe",
            status="completed",
            body="unsafe",
            experience_id="trial",
        )
    with pytest.raises(ValueError, match="stale"):
        refinery_record_experience(
            project_path=str(project),
            title="trial",
            purpose="stale",
            status="completed",
            body="stale",
            experience_id="trial",
            expected_updated_at="stale",
        )

    updated = refinery_record_experience(
        project_path=str(project),
        title="trial",
        purpose="safe",
        status="completed",
        body="safe",
        experience_id="trial",
        expected_updated_at=created["updated_at"],
    )
    assert updated["updated_at"] != created["updated_at"]
    assert refinery_get_experience(str(project), "trial")["body"] == "safe"


def test_malformed_memory_does_not_block_healthy_reads_or_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="source",
        purpose="support memory",
        status="completed",
        body="source",
        experience_id="source",
    )
    refinery_record_memory(
        project_path=str(project),
        title="healthy",
        summary="healthy",
        source_experiences=["source"],
        memory_id="healthy",
    )
    (vault / "shared" / "memory" / "broken.md").write_text("not front matter\n", encoding="utf-8")

    assert refinery_get_memory(str(project), "healthy")["body"] == "healthy"
    assert [entry["id"] for entry in refinery_search_memory(str(project))] == ["healthy"]
    assert refinery_validate()["valid"] is False


def test_validate_rejects_path_project_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="mismatch",
        purpose="validate location",
        status="completed",
        body="body",
        experience_id="mismatch",
    )
    path = vault / "projects" / "pybr" / "experiences" / "mismatch.md"
    text = path.read_text(encoding="utf-8").replace("project_id: pybr", "project_id: other")
    path.write_text(text, encoding="utf-8")

    result = refinery_validate()

    assert result["valid"] is False
    assert "must match path project" in str(result["errors"])


def test_validate_rejects_invalid_project_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    path = vault / "projects" / "pybr" / "project.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("name: pybr", "name: ''"),
        encoding="utf-8",
    )

    result = refinery_validate()

    assert result["valid"] is False
    assert result["checked"] == 0
    assert result["errors"] == [
        {
            "path": "projects/pybr/project.yaml",
            "error": "project metadata requires a non-empty name",
        }
    ]


def test_validate_rejects_filename_that_does_not_match_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="filename mismatch",
        purpose="validate location",
        status="completed",
        body="body",
        experience_id="canonical-id",
    )
    original = vault / "projects" / "pybr" / "experiences" / "canonical-id.md"
    original.rename(original.with_name("wrong-name.md"))

    result = refinery_validate()

    assert result["valid"] is False
    assert "filename must match document ID" in str(result["errors"])


def test_project_scoped_mcp_rejects_disabled_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    disable_project(project)

    with pytest.raises(ValueError, match="is disabled"):
        refinery_search_memory(project_path=str(project))
    with pytest.raises(ValueError, match="is disabled"):
        refinery_get_project_metadata(project_path=str(project))
    with pytest.raises(ValueError, match="is disabled"):
        refinery_record_experience(
            project_path=str(project),
            title="拒否される記録",
            purpose="無効化を検証する",
            status="completed",
            body="記録しない",
        )


def test_validate_reports_memory_with_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="一時的な根拠",
        purpose="参照検証",
        status="completed",
        body="根拠",
        experience_id="temporary-source",
    )
    refinery_record_memory(
        project_path=str(project),
        title="根拠を失うmemory",
        summary="検証対象",
        source_experiences=["temporary-source"],
        memory_id="orphaned-memory",
    )
    (vault / "projects" / "pybr" / "experiences" / "temporary-source.md").unlink()

    result = refinery_validate()

    assert result["valid"] is False
    assert result["checked"] == 1
    assert isinstance(result["errors"], list)
    assert "Unknown source experience" in result["errors"][0]["error"]


def test_mcp_updates_preserve_omitted_fields_and_support_explicit_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    created = refinery_record_experience(
        project_path=str(project),
        title="保持対象",
        purpose="patch semanticsを検証する",
        status="completed",
        body="original",
        evidence=[{"type": "file", "path": "result.txt", "retention": "reference"}],
        tags=["task/testing"],
        confidence="high",
        experience_id="preserved",
    )

    updated = refinery_record_experience(
        project_path=str(project),
        title="保持対象",
        purpose="本文だけ更新する",
        status="completed",
        body="updated",
        experience_id="preserved",
        expected_updated_at=str(created["updated_at"]),
    )
    header = refinery_get_experience(str(project), "preserved")["header"]
    assert header["tags"] == ["task/testing"]
    assert header["evidence"] == [{"type": "file", "path": "result.txt", "retention": "reference"}]
    assert header["confidence"] == "high"

    cleared = refinery_record_experience(
        project_path=str(project),
        title="保持対象",
        purpose="metadataを明示clearする",
        status="completed",
        body="cleared",
        tags=[],
        evidence=[],
        clear_confidence=True,
        experience_id="preserved",
        expected_updated_at=str(updated["updated_at"]),
    )
    cleared_header = refinery_get_experience(str(project), "preserved")["header"]
    assert cleared["updated_at"] == cleared_header["updated_at"]
    assert cleared_header["tags"] == []
    assert cleared_header["evidence"] == []
    assert cleared_header["confidence"] is None

    memory = refinery_record_memory(
        project_path=str(project),
        title="保持するmemory",
        summary="最初の要約",
        source_experiences=["preserved"],
        tags=["task/testing"],
        confidence="medium",
        memory_id="preserved-memory",
    )
    revised_memory = refinery_record_memory(
        project_path=str(project),
        title="保持するmemory",
        summary="更新した要約",
        memory_id="preserved-memory",
        expected_updated_at=str(memory["updated_at"]),
    )
    memory_header = refinery_get_memory(str(project), "preserved-memory")["header"]
    assert memory_header["source_experiences"] == ["preserved"]
    assert memory_header["tags"] == ["task/testing"]
    assert memory_header["confidence"] == "medium"
    assert revised_memory["scope"] == "project"
    assert revised_memory["project_id"] == "pybr"


def test_memory_lifecycle_hides_inactive_entries_and_links_active_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="根拠",
        purpose="memory lifecycleを検証する",
        status="completed",
        body="根拠",
        experience_id="lifecycle-source",
    )
    old = refinery_record_memory(
        project_path=str(project),
        title="旧原則",
        summary="古い原則",
        source_experiences=["lifecycle-source"],
        memory_id="old-rule",
    )
    successor = refinery_record_memory(
        project_path=str(project),
        title="新原則",
        summary="新しい原則",
        source_experiences=["lifecycle-source"],
        memory_id="new-rule",
    )
    refinery_record_memory(
        project_path=str(project),
        title="旧原則",
        summary="新原則に置換済み",
        status="superseded",
        superseded_by="new-rule",
        memory_id="old-rule",
        expected_updated_at=str(old["updated_at"]),
    )

    assert [entry["id"] for entry in refinery_search_memory(str(project))] == ["new-rule"]
    retired = refinery_search_memory(str(project), statuses=["superseded"])
    assert [entry["id"] for entry in retired] == ["old-rule"]
    assert retired[0]["status"] == "superseded"
    old_header = refinery_get_memory(str(project), "old-rule")["header"]
    assert old_header["superseded_by"] == "new-rule"
    blocked_successor = refinery_delete_memory(
        str(project), "new-rule", str(successor["updated_at"])
    )
    assert blocked_successor["can_delete"] is False
    assert blocked_successor["references"][0]["field"] == "superseded_by"


def test_safe_delete_requires_revision_confirmation_and_zero_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    source = refinery_record_experience(
        project_path=str(project),
        title="参照される根拠",
        purpose="安全削除を検証する",
        status="completed",
        body="根拠",
        experience_id="referenced-source",
    )
    memory = refinery_record_memory(
        project_path=str(project),
        title="参照memory",
        summary="削除を防ぐ",
        source_experiences=["referenced-source"],
        memory_id="reference-rule",
    )

    blocked = refinery_delete_experience(
        str(project), "referenced-source", str(source["updated_at"])
    )
    assert blocked["can_delete"] is False
    assert blocked["deleted"] is False
    assert blocked["references"][0]["field"] == "source_experiences"
    still_blocked = refinery_delete_experience(
        str(project), "referenced-source", str(source["updated_at"]), confirm=True
    )
    assert still_blocked["deleted"] is False
    assert (vault / "projects" / "pybr" / "experiences" / "referenced-source.md").exists()

    preview = refinery_delete_memory(str(project), "reference-rule", str(memory["updated_at"]))
    assert preview["can_delete"] is True
    assert preview["confirmation_required"] is True
    assert preview["deleted"] is False
    deleted = refinery_delete_memory(
        str(project), "reference-rule", str(memory["updated_at"]), confirm=True
    )
    assert deleted["deleted"] is True
    assert not (vault / "projects" / "pybr" / "memory" / "reference-rule.md").exists()

    removed_source = refinery_delete_experience(
        str(project), "referenced-source", str(source["updated_at"]), confirm=True
    )
    assert removed_source["deleted"] is True
    assert refinery_validate()["valid"] is True


def test_safe_delete_blocks_when_vault_references_cannot_be_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    source = refinery_record_experience(
        project_path=str(project),
        title="削除候補",
        purpose="validation blockerを検証する",
        status="completed",
        body="根拠",
        experience_id="delete-candidate",
    )
    broken = vault / "projects" / "pybr" / "memory" / "broken.md"
    broken.write_text("not front matter", encoding="utf-8")

    impact = refinery_delete_experience(
        str(project), "delete-candidate", str(source["updated_at"]), confirm=True
    )

    assert impact["can_delete"] is False
    assert impact["deleted"] is False
    assert impact["validation_errors"][0]["path"].endswith("memory/broken.md")


def test_search_results_expose_fields_needed_for_deterministic_exact_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    refinery_record_experience(
        project_path=str(project),
        title="検索候補",
        purpose="候補選択に必要な情報を返す",
        status="inconclusive",
        body="body",
        tags=["task/search"],
        confidence="low",
        experience_id="search-entry",
    )
    refinery_record_memory(
        project_path=str(project),
        title="検索memory",
        summary="exact getへ進める",
        source_experiences=["search-entry"],
        tags=["task/search"],
        confidence="low",
        memory_id="search-memory",
    )

    experience = refinery_search_experiences(str(project), experience_ids=["search-entry"])[0]
    memory = refinery_search_memory(str(project), memory_ids=["search-memory"])[0]

    assert experience == {
        "project_id": "pybr",
        "id": "search-entry",
        "title": "検索候補",
        "kind": "experience",
        "summary": "候補選択に必要な情報を返す",
        "status": "inconclusive",
        "scope": None,
        "confidence": "low",
        "tags": ["task/search"],
        "recorded_at": experience["recorded_at"],
        "updated_at": experience["updated_at"],
        "path": "projects/pybr/experiences/search-entry.md",
    }
    assert memory["scope"] == "project"
    assert memory["project_id"] == "pybr"
    assert memory["summary"] == "exact getへ進める"
    assert memory["updated_at"]


def test_mcp_search_rejects_ambiguous_scope_and_invalid_filters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"

    with pytest.raises(ValueError, match="cannot be used together"):
        refinery_search_experiences(str(project), project_ids=["pybr"], all_projects=True)
    with pytest.raises(ValueError, match="Unsupported experience statuses"):
        refinery_search_experiences(str(project), statuses=cast(Any, ["complete"]))
    with pytest.raises(ValueError, match="Unsupported memory statuses"):
        refinery_search_memory(str(project), statuses=cast(Any, ["archived"]))


def test_repo_scoped_mcp_rejects_invalid_project_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = configured_mcp(tmp_path, monkeypatch)
    project = tmp_path / "pybr"
    metadata = vault / "projects" / "pybr" / "project.yaml"
    metadata.write_text(
        metadata.read_text(encoding="utf-8").replace("name: pybr", "name: ''"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty name"):
        refinery_record_experience(
            project_path=str(project),
            title="拒否対象",
            purpose="invalid metadata gate",
            status="completed",
            body="write must not happen",
            experience_id="must-not-exist",
        )
    assert not (vault / "projects" / "pybr" / "experiences" / "must-not-exist.md").exists()
