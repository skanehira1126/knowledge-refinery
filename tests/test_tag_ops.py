from pathlib import Path

import pytest

from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.experience_ops import upsert_memory_at
from knowledge_refinery.tag_ops import browse_knowledge_tags
from knowledge_refinery.tag_ops import search_knowledge_tags
from knowledge_refinery.tag_ops import update_tag_description
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


def _configured_vault(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "refinery"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    return vault, project


def _record_experience(vault: Path, project_id: str, experience_id: str, tag: str) -> None:
    upsert_experience_at(
        vault,
        project_id,
        title=experience_id,
        purpose="tag集計を検証する",
        status="completed",
        experience_id=experience_id,
        filename=None,
        tags=[tag],
        evidence=[],
        related_experiences=[],
        supersedes=[],
        confidence="high",
        body="検証結果",
    )


def test_browse_tags_traverses_one_level_with_descriptions_and_usage(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)
    _record_experience(vault, "product", "feature-selection", "domain/ml/feature-selection")
    upsert_memory_at(
        vault,
        "product",
        title="ML原則",
        summary="機械学習の原則",
        memory_id="ml-principle",
        filename=None,
        tags=["domain/ml"],
        source_experiences=["feature-selection"],
        shared=False,
        confidence="high",
        body="原則",
    )

    root = browse_knowledge_tags(vault, "product")
    domain = next(item for item in root["tags"] if item["tag"] == "domain")
    assert domain == {
        "tag": "domain",
        "segment": "domain",
        "description": "対象となる業務・知識領域",
        "defined": True,
        "direct_count": 0,
        "document_count": 2,
        "experience_count": 1,
        "project_memory_count": 1,
        "shared_memory_count": 0,
        "has_children": True,
    }

    children = browse_knowledge_tags(vault, "product", parent_tag="domain")
    assert [item["tag"] for item in children["tags"]] == ["domain/ml"]
    assert children["tags"][0]["description"] is None
    assert children["tags"][0]["document_count"] == 2

    leaves = browse_knowledge_tags(vault, "product", parent_tag="domain/ml")
    assert [item["tag"] for item in leaves["tags"]] == ["domain/ml/feature-selection"]
    assert leaves["tags"][0]["direct_count"] == 1


def test_tag_descriptions_are_revisioned_and_searchable(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)
    _record_experience(vault, "product", "feature-selection", "domain/ml/feature-selection")

    created = update_tag_description(
        vault,
        tag="domain/ml",
        description="機械学習モデルと分析手法",
        expected_updated_at=None,
    )
    assert created.updated_at is not None
    matches = search_knowledge_tags(vault, "product", terms=["機械学習", "分析"])
    assert [item["tag"] for item in matches["tags"]] == ["domain/ml"]
    assert matches["tags"][0]["description"] == "機械学習モデルと分析手法"

    updated = update_tag_description(
        vault,
        tag="domain/ml/feature-selection",
        description="特徴量選択の手法と評価",
        expected_updated_at=created.updated_at,
    )
    assert updated.updated_at != created.updated_at
    with pytest.raises(ValueError, match="stale"):
        update_tag_description(
            vault,
            tag="domain/ml",
            description="古いrevisionからの更新",
            expected_updated_at=created.updated_at,
        )


def test_all_projects_controls_tag_usage_scope(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    setup_project(other, vault, project_id="other")
    _record_experience(vault, "other", "search-timeout", "issue/performance/timeout")

    local = browse_knowledge_tags(vault, "product", parent_tag="issue")
    assert local["tags"] == []
    across_vault = browse_knowledge_tags(vault, "product", parent_tag="issue", all_projects=True)
    assert [item["tag"] for item in across_vault["tags"]] == ["issue/performance"]
    assert across_vault["tags"][0]["document_count"] == 1


def test_browse_includes_shared_memory_in_current_project_scope(tmp_path: Path) -> None:
    vault, _ = _configured_vault(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    setup_project(other, vault, project_id="other")
    _record_experience(vault, "product", "product-trial", "domain/testing")
    _record_experience(vault, "other", "other-trial", "domain/testing")
    upsert_memory_at(
        vault,
        "product",
        title="回帰テスト原則",
        summary="変更後は回帰テストを実施する",
        memory_id="regression-principle",
        filename=None,
        tags=["task/testing/regression"],
        source_experiences=["product/product-trial", "other/other-trial"],
        shared=True,
        confidence="high",
        body="共有原則",
    )

    result = browse_knowledge_tags(vault, "product", parent_tag="task/testing")

    assert [item["tag"] for item in result["tags"]] == ["task/testing/regression"]
    assert result["tags"][0]["document_count"] == 1
    assert result["tags"][0]["shared_memory_count"] == 1


@pytest.mark.parametrize("tag", ["Domain/ml", "domain//ml", "a/b/c/d"])
def test_tag_description_rejects_invalid_paths(tmp_path: Path, tag: str) -> None:
    vault, _ = _configured_vault(tmp_path)
    with pytest.raises(ValueError, match="one to three lowercase"):
        update_tag_description(
            vault,
            tag=tag,
            description="不正なtag",
            expected_updated_at=None,
        )
