from pathlib import Path

import pytest

import knowledge_refinery.cli as cli
from tests._support import make_session_meta
from tests._support import write_markdown_document
from tests._support import write_yaml_data


def test_search_knowledge_lists_default_flow_and_stock_only(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "raw" / "raw-note.md",
        {
            "title": "Raw Note",
            "description": "Raw observation",
        },
        "Body",
    )
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "flow" / "api-rate-limit.md",
        {
            "title": "API Rate Limit",
            "description": "Flow notes",
            "summary": "Summary text",
            "knowledge_type": "reference",
            "tags": ["domain/api"],
        },
        "Observed retries",
    )
    write_markdown_document(
        refinery_root / "shared" / "stock" / "api-rate-limit.md",
        {
            "title": "API Rate Limit Stock",
            "description": "Stock notes",
            "summary": "Stable summary",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-123"],
            "derived_from": [".refinery/shared/review/session-123--api-rate-limit.md"],
            "tags": ["domain/api"],
        },
        "Stable body",
    )

    exit_code = cli.main(["knowledge", "search", "--root", str(refinery_root)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'scope="flow"' in captured.out
    assert 'scope="stock"' in captured.out
    assert 'scope="raw"' not in captured.out
    assert 'knowledge_type="reference"' in captured.out
    assert captured.err == ""


def test_search_knowledge_supports_and_terms_and_exact_filters(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "flow" / "api-rate-limit.md",
        {
            "title": "API Rate Limit",
            "description": "Flow notes",
            "summary": "Burst rate limits",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "tags": ["domain/api", "issue/rate-limit"],
            "source_sessions": ["session-123"],
        },
        "Rate limit behavior for API retries",
    )
    write_markdown_document(
        refinery_root / "sessions" / "session-999" / "flow" / "auth.md",
        {
            "title": "Auth",
            "description": "Different topic",
            "summary": "Login notes",
            "knowledge_id": "auth-notes",
            "knowledge_type": "constructive",
            "tags": ["domain/auth"],
        },
        "No rate content",
    )

    exit_code = cli.main(
        [
            "knowledge",
            "search",
            "API",
            "rate",
            "--root",
            str(refinery_root),
            "--scope",
            "flow",
            "--tag",
            "domain/api",
            "--knowledge-id",
            "api-rate-limit",
            "--knowledge-type",
            "reference",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"knowledge_id"="api-rate-limit"' not in captured.out
    assert 'knowledge_id="api-rate-limit"' in captured.out
    assert 'knowledge_type="reference"' in captured.out
    assert 'title="API Rate Limit"' in captured.out
    assert 'title="Auth"' not in captured.out


def test_search_knowledge_raw_scope_respects_session_filter(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "raw" / "first.md",
        {
            "title": "API Error",
            "description": "Raw note",
        },
        "Observed command failure",
    )
    write_markdown_document(
        refinery_root / "sessions" / "session-999" / "raw" / "second.md",
        {
            "title": "API Error",
            "description": "Other session",
        },
        "Observed elsewhere",
    )

    exit_code = cli.main(
        [
            "knowledge",
            "search",
            "--root",
            str(refinery_root),
            "--scope",
            "raw",
            "--session-id",
            "session-123",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "session-123/raw/first.md" in captured.out
    assert "session-999/raw/second.md" not in captured.out


def test_search_knowledge_can_filter_by_knowledge_type_only(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "flow" / "api-rate-limit.md",
        {
            "title": "API Rate Limit",
            "description": "Flow notes",
            "summary": "Stable API behavior",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
        },
        "429 conditions",
    )
    write_markdown_document(
        refinery_root / "sessions" / "session-123" / "flow" / "retry-strategy.md",
        {
            "title": "Retry Strategy",
            "description": "Flow notes",
            "summary": "Tuning heuristics",
            "knowledge_id": "retry-strategy",
            "knowledge_type": "constructive",
        },
        "Adjust backoff based on failure mode",
    )

    exit_code = cli.main(
        [
            "knowledge",
            "search",
            "--root",
            str(refinery_root),
            "--scope",
            "flow",
            "--knowledge-type",
            "constructive",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'title="Retry Strategy"' in captured.out
    assert 'title="API Rate Limit"' not in captured.out


def test_search_review_can_include_rejected_files(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_markdown_document(
        refinery_root / "shared" / "review" / "session-123--api-rate-limit.md",
        {
            "title": "API Rate Limit",
            "description": "Review note",
            "summary": "Active review",
            "knowledge_id": "api-rate-limit",
            "knowledge_type": "reference",
            "source_sessions": ["session-123"],
            "tags": ["domain/api"],
        },
        "Active body",
    )
    write_markdown_document(
        refinery_root / "shared" / "review" / "rejected" / "session-999--auth.md",
        {
            "title": "Auth Review",
            "description": "Rejected review note",
            "summary": "Rejected review",
            "knowledge_id": "auth-review",
            "knowledge_type": "constructive",
            "source_sessions": ["session-999"],
            "tags": ["domain/auth"],
        },
        "Rejected body",
    )

    exit_code = cli.main(
        [
            "review",
            "search",
            "--root",
            str(refinery_root),
            "--include-rejected",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'knowledge_id="api-rate-limit"' in captured.out
    assert 'knowledge_id="auth-review"' in captured.out
    assert 'knowledge_type="reference"' in captured.out
    assert 'knowledge_type="constructive"' in captured.out


def test_search_sessions_reads_meta_and_state_and_filters(
    refinery_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_root = refinery_root / "sessions" / "session-123"
    write_yaml_data(
        session_root / "meta.yaml",
        make_session_meta(
            title="Investigate API rate limit",
            task="Investigate retry strategy",
            repository=None,
            domain="backend",
        ),
    )
    write_markdown_document(
        session_root / "state.md",
        {
            "title": "Session State",
            "description": "Current state",
        },
        "- 目的: investigate API retry\n- 進捗: captured evidence",
    )
    write_yaml_data(
        refinery_root / "sessions" / "session-999" / "meta.yaml",
        make_session_meta(
            session_id="session-999",
            title="Other work",
            task="Different task",
            repository=None,
            domain="frontend",
            status="closed",
            phase="done",
            current_step="none",
            next_action="none",
            flow_status="done",
            synthesis_status="done",
            coverage_status="complete",
            confidence="medium",
        ),
    )
    write_markdown_document(
        refinery_root / "sessions" / "session-999" / "state.md",
        {
            "title": "Session State",
            "description": "Current state",
        },
        "- 目的: other",
    )

    exit_code = cli.main(
        [
            "session",
            "search",
            "captured",
            "--root",
            str(refinery_root),
            "--status",
            "active",
            "--phase",
            "capture",
            "--domain",
            "backend",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'session_id="session-123"' in captured.out
    assert 'title="Investigate API rate limit"' in captured.out
    assert 'session_id="session-999"' not in captured.out
