from collections.abc import Callable
from pathlib import Path

import pytest

from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.errors import RefineryPathError
from knowledge_refinery.knowledge_ops import list_review
from knowledge_refinery.knowledge_ops import prepare_review
from knowledge_refinery.knowledge_ops import promote_review
from knowledge_refinery.knowledge_ops import refresh_review
from knowledge_refinery.knowledge_ops import reject_review
from tests._support import write_markdown_document


def test_prepare_review_normalizes_header_and_sets_lineage(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "API Rate Limit.md"
    write_markdown_document(
        flow_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
            "knowledge_type": "reference",
            "tags": ["api", "limits"],
        },
        "Body",
    )

    results = prepare_review(root)

    review_path = root / "shared" / "review" / "session-123--reference--api-rate-limit.md"
    assert [result.target for result in results] == [review_path]
    content = review_path.read_text(encoding="utf-8")
    assert "knowledge_id: api-rate-limit" in content
    assert "knowledge_type: reference" in content
    assert "source_sessions:\n- session-123" in content
    assert "derived_from:\n- .refinery/sessions/session-123/flow/API Rate Limit.md" in content
    assert "tags:\n- api\n- limits" in content


def test_prepare_review_collects_nested_flow_files(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "topic" / "example.md"
    write_markdown_document(
        flow_path,
        {
            "title": "Example",
            "description": "Observation notes",
            "summary": "Summary text",
        },
        "Body",
    )

    results = prepare_review(root)

    review_path = root / "shared" / "review" / "session-123--example.md"
    assert [result.target for result in results] == [review_path]
    assert (
        "derived_from:\n- .refinery/sessions/session-123/flow/topic/example.md"
        in review_path.read_text(encoding="utf-8")
    )


def test_prepare_review_allows_same_knowledge_id_when_knowledge_type_differs(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".refinery"
    write_markdown_document(
        root / "sessions" / "session-123" / "flow" / "api-rate-limit-reference.md",
        {
            "title": "API Rate Limit Facts",
            "description": "Observation notes",
            "summary": "Stable limits",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
        },
        "Facts",
    )
    write_markdown_document(
        root / "sessions" / "session-123" / "flow" / "api-rate-limit-how.md",
        {
            "title": "API Rate Limit Strategy",
            "description": "Observation notes",
            "summary": "How to react",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "constructive",
        },
        "Heuristics",
    )

    results = prepare_review(root)

    assert [result.target.name for result in results] == [
        "session-123--constructive--api-rate-limit.md",
        "session-123--reference--api-rate-limit.md",
    ]


def test_promote_review_merges_existing_stock_lineage_and_sessions(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    review_path = root / "shared" / "review" / "session-123--reference--api-rate-limit.md"
    stock_path = root / "shared" / "stock" / "reference--api-rate-limit.md"
    write_markdown_document(
        review_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-123"],
            "derived_from": [".refinery/sessions/session-123/flow/api-rate-limit.md"],
        },
        "New body",
    )
    write_markdown_document(
        stock_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-000"],
            "derived_from": [".refinery/shared/review/session-000--api-rate-limit.md"],
        },
        "Old body",
    )

    results = promote_review(
        root,
        knowledge_ids=[],
        review_files=[str(review_path)],
        all_files=False,
        force=True,
    )

    assert results[0].target == stock_path
    content = stock_path.read_text(encoding="utf-8")
    assert "source_sessions:\n- session-000\n- session-123" in content
    assert "knowledge_type: reference" in content
    assert "derived_from:\n- .refinery/shared/review/session-000--api-rate-limit.md" in content
    assert "- .refinery/sessions/session-123/flow/api-rate-limit.md" in content
    assert "- .refinery/shared/review/session-123--reference--api-rate-limit.md" in content
    assert content.endswith("New body\n")


def test_refresh_review_rebuilds_review_from_flow_source(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "api-rate-limit.md"
    review_path = root / "shared" / "review" / "session-123--reference--api-rate-limit.md"
    write_markdown_document(
        flow_path,
        {
            "title": "API Rate Limit",
            "description": "Updated observation notes",
            "summary": "Updated summary",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
        },
        "Fresh body",
    )
    write_markdown_document(
        review_path,
        {
            "title": "API Rate Limit",
            "description": "Old description",
            "summary": "Old summary",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-123"],
            "derived_from": [".refinery/sessions/session-123/flow/api-rate-limit.md"],
        },
        "Old body",
    )

    results = refresh_review(
        root, knowledge_ids=[], review_files=[str(review_path)], all_files=False
    )

    assert results[0].target == review_path
    content = review_path.read_text(encoding="utf-8")
    assert "description: Updated observation notes" in content
    assert "summary: Updated summary" in content
    assert "knowledge_type: reference" in content
    assert "source_sessions:\n- session-123" in content
    assert "Old body" not in content
    assert content.endswith("Fresh body\n")


def test_reject_review_moves_file_out_of_active_review_queue(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    review_path = root / "shared" / "review" / "session-123--reference--api-rate-limit.md"
    write_markdown_document(
        review_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-123"],
        },
        "Body",
    )

    results = reject_review(
        root, knowledge_ids=[], review_files=[str(review_path)], all_files=False
    )

    rejected_path = root / "shared" / "review" / "rejected" / review_path.name
    assert results[0].target == rejected_path
    assert not review_path.exists()
    assert rejected_path.exists()
    entries = list_review(root, include_rejected=False)
    assert entries == []


def test_promote_review_filters_knowledge_id_by_knowledge_type(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    reference_path = root / "shared" / "review" / "session-123--reference--api-rate-limit.md"
    constructive_path = root / "shared" / "review" / "session-123--constructive--api-rate-limit.md"
    for review_path, knowledge_type in [
        (reference_path, "reference"),
        (constructive_path, "constructive"),
    ]:
        write_markdown_document(
            review_path,
            {
                "title": f"API Rate Limit {knowledge_type}",
                "description": "Observation notes",
                "summary": "Summary text",
                "knowledge_id": "api-rate-limit",
                "knowledge_type": knowledge_type,
                "source_sessions": ["session-123"],
                "derived_from": [".refinery/sessions/session-123/flow/api-rate-limit.md"],
            },
            f"{knowledge_type} body",
        )

    results = promote_review(
        root,
        knowledge_ids=["api-rate-limit"],
        knowledge_types=["constructive"],
        review_files=[],
        all_files=False,
    )

    assert [result.source for result in results] == [constructive_path]
    assert results[0].target == root / "shared" / "stock" / "constructive--api-rate-limit.md"
    assert not (root / "shared" / "stock" / "reference--api-rate-limit.md").exists()


def test_promote_review_requires_type_or_file_for_duplicate_knowledge_id(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".refinery"
    for knowledge_type in ["reference", "constructive"]:
        write_markdown_document(
            root / "shared" / "review" / f"session-123--{knowledge_type}--api-rate-limit.md",
            {
                "title": f"API Rate Limit {knowledge_type}",
                "description": "Observation notes",
                "summary": "Summary text",
                "knowledge_id": "api-rate-limit",
                "knowledge_type": knowledge_type,
                "source_sessions": ["session-123"],
                "derived_from": [".refinery/sessions/session-123/flow/api-rate-limit.md"],
            },
            "Body",
        )

    with pytest.raises(RefineryConflictError):
        promote_review(
            root,
            knowledge_ids=["api-rate-limit"],
            review_files=[],
            all_files=False,
        )


def test_prepare_review_raises_conflict_for_duplicate_knowledge_id_in_same_session(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".refinery"
    first_flow_path = root / "sessions" / "session-123" / "flow" / "API Rate Limit.md"
    second_flow_path = root / "sessions" / "session-123" / "flow" / "api_rate_limit.md"
    write_markdown_document(
        first_flow_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
        },
        "One",
    )
    write_markdown_document(
        second_flow_path,
        {
            "title": "API Rate Limit Duplicate",
            "description": "Observation notes",
            "summary": "Summary text",
        },
        "Two",
    )

    with pytest.raises(RefineryConflictError):
        prepare_review(root)


def test_prepare_review_force_still_raises_conflict_for_duplicate_knowledge_id_in_same_session(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".refinery"
    first_flow_path = root / "sessions" / "session-123" / "flow" / "API Rate Limit.md"
    second_flow_path = root / "sessions" / "session-123" / "flow" / "api_rate_limit.md"
    write_markdown_document(
        first_flow_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
        },
        "One",
    )
    write_markdown_document(
        second_flow_path,
        {
            "title": "API Rate Limit Duplicate",
            "description": "Observation notes",
            "summary": "Summary text",
        },
        "Two",
    )

    with pytest.raises(RefineryConflictError):
        prepare_review(root, force=True)


@pytest.mark.parametrize(
    ("operation", "kwargs"),
    [
        (promote_review, {"force": False}),
        (refresh_review, {}),
        (reject_review, {"force": False}),
    ],
)
def test_review_operations_reject_non_review_files(
    tmp_path: Path,
    operation: Callable[..., object],
    kwargs: dict[str, object],
) -> None:
    root = tmp_path / ".refinery"
    stock_path = root / "shared" / "stock" / "api-rate-limit.md"
    write_markdown_document(
        stock_path,
        {
            "title": "API Rate Limit",
            "description": "Observation notes",
            "summary": "Summary text",
            "knowledge_id": "api-rate-limit",
            "source_sessions": ["session-123"],
        },
        "Body",
    )

    with pytest.raises(RefineryPathError):
        operation(
            root,
            knowledge_ids=[],
            review_files=[str(stock_path)],
            all_files=False,
            **kwargs,
        )
