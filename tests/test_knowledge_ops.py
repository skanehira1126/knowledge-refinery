from pathlib import Path

import pytest

from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.knowledge_ops import list_review
from knowledge_refinery.knowledge_ops import prepare_review
from knowledge_refinery.knowledge_ops import promote_review
from knowledge_refinery.knowledge_ops import refresh_review
from knowledge_refinery.knowledge_ops import reject_review


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_prepare_review_normalizes_header_and_sets_lineage(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "API Rate Limit.md"
    write_markdown(
        flow_path,
        """---
title: API Rate Limit
description: Observation notes
summary: Summary text
tags:
  - api
  - limits
---

Body
""",
    )

    results = prepare_review(root)

    review_path = root / "shared" / "review" / "session-123--api-rate-limit.md"
    assert [result.target for result in results] == [review_path]
    content = review_path.read_text(encoding="utf-8")
    assert "knowledge_id: api-rate-limit" in content
    assert "source_sessions:\n- session-123" in content
    assert "derived_from:\n- .refinery/sessions/session-123/flow/API Rate Limit.md" in content
    assert "tags:\n- api\n- limits" in content


def test_prepare_review_collects_nested_flow_files(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "topic" / "example.md"
    write_markdown(
        flow_path,
        """---
title: Example
description: Observation notes
summary: Summary text
---

Body
""",
    )

    results = prepare_review(root)

    review_path = root / "shared" / "review" / "session-123--example.md"
    assert [result.target for result in results] == [review_path]
    assert (
        "derived_from:\n- .refinery/sessions/session-123/flow/topic/example.md"
        in review_path.read_text(encoding="utf-8")
    )


def test_promote_review_merges_existing_stock_lineage_and_sessions(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    review_path = root / "shared" / "review" / "session-123--api-rate-limit.md"
    stock_path = root / "shared" / "stock" / "api-rate-limit.md"
    write_markdown(
        review_path,
        """---
title: API Rate Limit
description: Observation notes
summary: Summary text
knowledge_id: api-rate-limit
source_sessions:
  - session-123
derived_from:
  - .refinery/sessions/session-123/flow/api-rate-limit.md
---

New body
""",
    )
    write_markdown(
        stock_path,
        """---
title: API Rate Limit
description: Observation notes
summary: Summary text
knowledge_id: api-rate-limit
source_sessions:
  - session-000
derived_from:
  - .refinery/shared/review/session-000--api-rate-limit.md
---

Old body
""",
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
    assert "derived_from:\n- .refinery/shared/review/session-000--api-rate-limit.md" in content
    assert "- .refinery/sessions/session-123/flow/api-rate-limit.md" in content
    assert "- .refinery/shared/review/session-123--api-rate-limit.md" in content
    assert content.endswith("New body\n")


def test_refresh_review_rebuilds_review_from_flow_source(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    flow_path = root / "sessions" / "session-123" / "flow" / "api-rate-limit.md"
    review_path = root / "shared" / "review" / "session-123--api-rate-limit.md"
    write_markdown(
        flow_path,
        """---
title: API Rate Limit
description: Updated observation notes
summary: Updated summary
knowledge_id: api-rate-limit
---

Fresh body
""",
    )
    write_markdown(
        review_path,
        """---
title: API Rate Limit
description: Old description
summary: Old summary
knowledge_id: api-rate-limit
source_sessions:
  - session-123
derived_from:
  - .refinery/sessions/session-123/flow/api-rate-limit.md
---

Old body
""",
    )

    results = refresh_review(
        root, knowledge_ids=[], review_files=[str(review_path)], all_files=False
    )

    assert results[0].target == review_path
    content = review_path.read_text(encoding="utf-8")
    assert "description: Updated observation notes" in content
    assert "summary: Updated summary" in content
    assert "source_sessions:\n- session-123" in content
    assert "Old body" not in content
    assert content.endswith("Fresh body\n")


def test_reject_review_moves_file_out_of_active_review_queue(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    review_path = root / "shared" / "review" / "session-123--api-rate-limit.md"
    write_markdown(
        review_path,
        """---
title: API Rate Limit
description: Observation notes
summary: Summary text
knowledge_id: api-rate-limit
source_sessions:
  - session-123
---

Body
""",
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


def test_prepare_review_raises_conflict_for_duplicate_knowledge_id_in_same_session(
    tmp_path: Path,
) -> None:
    root = tmp_path / ".refinery"
    first_flow_path = root / "sessions" / "session-123" / "flow" / "API Rate Limit.md"
    second_flow_path = root / "sessions" / "session-123" / "flow" / "api_rate_limit.md"
    write_markdown(
        first_flow_path,
        """---
title: API Rate Limit
description: Observation notes
summary: Summary text
---

One
""",
    )
    write_markdown(
        second_flow_path,
        """---
title: API Rate Limit Duplicate
description: Observation notes
summary: Summary text
---

Two
""",
    )

    with pytest.raises(RefineryConflictError):
        prepare_review(root)
