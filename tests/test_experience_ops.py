from pathlib import Path

import pytest

from knowledge_refinery.experience_ops import SearchFilters
from knowledge_refinery.experience_ops import parse_datetime_filter
from knowledge_refinery.experience_ops import search_documents
from knowledge_refinery.experience_ops import upsert_experience
from knowledge_refinery.experience_ops import upsert_memory
from knowledge_refinery.experience_ops import validate_document_header
from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


def configured_project(tmp_path: Path, project_id: str = "pybr") -> tuple[Path, Path]:
    vault = tmp_path / "refinery"
    project = tmp_path / project_id
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id=project_id, create_link=True)
    return project, vault


def test_upsert_experience_keeps_attempt_and_evaluation_together(tmp_path: Path) -> None:
    project, vault = configured_project(tmp_path)
    body = """## 試したこと

- Boruta

## 分かったこと

- 精度は良いが遅かった

## 次の可能性

- 特徴量をグループ化する
"""

    path = upsert_experience(
        project,
        title="Borutaを試した",
        purpose="特徴量を減らす",
        status="completed",
        experience_id="boruta-trial",
        filename=None,
        tags=["domain/ml"],
        evidence=["untracked:notebooks/boruta.ipynb"],
        related_experiences=["feature-selection-baseline"],
        supersedes=[],
        confidence="medium",
        body=body,
    )

    assert path == vault / "projects" / "pybr" / "experiences" / "boruta-trial.md"
    header, rendered_body = split_front_matter(path.read_text(encoding="utf-8"))
    assert header["experience_id"] == "boruta-trial"
    assert header["project_id"] == "pybr"
    assert header["schema_version"] == 2
    assert header["evidence"] == [
        {
            "type": "file",
            "path": "notebooks/boruta.ipynb",
            "git_state": "untracked",
            "retention": "reference",
        }
    ]
    assert header["related_experiences"] == ["feature-selection-baseline"]
    assert header["confidence"] == "medium"
    assert "精度は良いが遅かった" in rendered_body
    assert "特徴量をグループ化する" in rendered_body


def test_search_experiences_across_projects(tmp_path: Path) -> None:
    vault = tmp_path / "refinery"
    init_vault(vault)
    first = tmp_path / "pybr"
    second = tmp_path / "vision"
    first.mkdir()
    second.mkdir()
    setup_project(first, vault, project_id="pybr", create_link=True)
    setup_project(second, vault, project_id="vision", create_link=True)
    for project, experience_id in ((first, "boruta-one"), (second, "boruta-two")):
        upsert_experience(
            project,
            title="Boruta検証",
            purpose="比較",
            status="completed",
            experience_id=experience_id,
            filename=None,
            tags=["domain/ml"],
            evidence=["mlflow:runs:/abc123"],
            related_experiences=[],
            supersedes=[],
            confidence="high",
            body="## 試したこと\n\nBoruta\n",
        )

    local = search_documents(
        first,
        kind="experiences",
        terms=["Boruta"],
        project_ids=[],
        tags=[],
        statuses=[],
        all_projects=False,
        filters=None,
    )
    all_entries = search_documents(
        first,
        kind="experiences",
        terms=["Boruta"],
        project_ids=[],
        tags=["domain/ml"],
        statuses=["completed"],
        all_projects=True,
        filters=SearchFilters(
            evidence_types=("mlflow",),
            confidences=("high",),
        ),
    )

    assert [entry.project_id for entry in local] == ["pybr"]
    assert {entry.project_id for entry in all_entries} == {"pybr", "vision"}


def test_memory_requires_evidence_and_can_be_shared(tmp_path: Path) -> None:
    project, vault = configured_project(tmp_path)
    second = tmp_path / "vision"
    second.mkdir()
    setup_project(second, vault, project_id="vision", create_link=True)
    for source_project, experience_id in (
        (project, "boruta-trial"),
        (second, "vision-trial"),
    ):
        upsert_experience(
            source_project,
            title="共有原則の根拠",
            purpose="複数projectで確認する",
            status="completed",
            experience_id=experience_id,
            filename=None,
            tags=[],
            evidence=[],
            related_experiences=[],
            supersedes=[],
            confidence="high",
            body="## 分かったこと\n\n共通の結果\n",
        )

    path = upsert_memory(
        project,
        title="相関特徴量はグループで評価する",
        summary="個別重要度だけで判断しない",
        memory_id="correlated-features",
        filename=None,
        tags=["domain/ml"],
        source_experiences=["pybr/boruta-trial", "vision/vision-trial"],
        shared=True,
        confidence="high",
        body=None,
    )

    assert path == vault / "shared" / "memory" / "correlated-features.md"
    header, _ = split_front_matter(path.read_text(encoding="utf-8"))
    assert header["source_experiences"] == [
        "pybr/boruta-trial",
        "vision/vision-trial",
    ]
    assert header["scope"] == "shared"
    assert header["confidence"] == "high"


def test_memory_rejects_missing_or_insufficient_source_experiences(tmp_path: Path) -> None:
    project, _ = configured_project(tmp_path)

    with pytest.raises(ValueError, match="Unknown source experience"):
        upsert_memory(
            project,
            title="根拠なし",
            summary="保存できない",
            memory_id="missing-source",
            filename=None,
            tags=[],
            source_experiences=["does-not-exist"],
            shared=False,
            confidence=None,
            body=None,
        )

    with pytest.raises(ValueError, match="project-id/experience-id"):
        upsert_memory(
            project,
            title="曖昧な共有知識",
            summary="保存できない",
            memory_id="ambiguous-shared",
            filename=None,
            tags=[],
            source_experiences=["does-not-exist"],
            shared=True,
            confidence=None,
            body=None,
        )


def test_search_supports_id_relationship_and_recorded_range(tmp_path: Path) -> None:
    project, _ = configured_project(tmp_path)
    upsert_experience(
        project,
        title="後続検証",
        purpose="関連案を試す",
        status="completed",
        experience_id="follow-up",
        filename=None,
        tags=[],
        evidence=["git:abc123:src/model.py"],
        related_experiences=["boruta-trial"],
        supersedes=["old-trial"],
        confidence="medium",
        body=None,
    )

    entries = search_documents(
        project,
        kind="experiences",
        terms=[],
        project_ids=[],
        tags=[],
        statuses=[],
        all_projects=False,
        filters=SearchFilters(
            document_ids=("follow-up",),
            related_experiences=("boruta-trial",),
            evidence_types=("git",),
            recorded_from=parse_datetime_filter("2020-01-01", end_of_day=False),
            recorded_to=parse_datetime_filter("2030-01-01", end_of_day=True),
        ),
    )

    assert [entry.document_id for entry in entries] == ["follow-up"]


def test_schema_validation_rejects_unstructured_evidence() -> None:
    header: dict[str, object] = {
        "schema_version": 2,
        "experience_id": "trial",
        "project_id": "pybr",
        "title": "Trial",
        "purpose": "Test",
        "status": "completed",
        "recorded_at": "2026-07-11T00:00:00+00:00",
        "tags": [],
        "related_experiences": [],
        "supersedes": [],
        "evidence": ["untracked:file.csv"],
        "confidence": "medium",
    }

    try:
        validate_document_header(header, kind="experiences")
    except ValueError as error:
        assert "mapping" in str(error)
    else:
        raise AssertionError("unstructured evidence must be rejected")
