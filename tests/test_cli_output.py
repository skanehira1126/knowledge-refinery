from pathlib import Path

from knowledge_refinery.cli_output import render_apply_template_output
from knowledge_refinery.cli_output import render_copy_results_output
from knowledge_refinery.cli_output import render_session_update_output
from knowledge_refinery.knowledge_ops import CopyResult


def test_render_apply_template_output_contains_next_steps() -> None:
    lines = render_apply_template_output(
        template_root=Path("/template"),
        target_root=Path("/repo"),
        skill_destination="codex",
        copied_count=5,
    )

    assert lines[:4] == [
        "Applied template from: /template",
        "Target repository: /repo",
        "Skill destination: .codex/skills",
        "Copied files: 5",
    ]
    assert "Next steps:" in lines
    assert any("update-template" in line for line in lines)


def test_render_session_update_output_uses_key_value_format() -> None:
    rendered = render_session_update_output(
        Path("/repo/.refinery/sessions/session-123/meta.yaml"),
        {
            "session_id": "session-123",
            "title": "Investigate API",
            "task": "Review retries",
            "status": "paused",
            "phase": "analysis",
            "flow_status": "in_progress",
            "next_action": "wait",
        },
    )

    assert 'path="/repo/.refinery/sessions/session-123"' in rendered
    assert 'session_id="session-123"' in rendered
    assert 'flow_status="in_progress"' in rendered


def test_render_copy_results_output_renders_detail_and_summary() -> None:
    lines = render_copy_results_output(
        [
            CopyResult(
                source=Path("/repo/.refinery/shared/review/a.md"),
                target=Path("/repo/.refinery/shared/stock/a.md"),
                copied=True,
            ),
            CopyResult(
                source=Path("/repo/.refinery/shared/review/b.md"),
                target=Path("/repo/.refinery/shared/stock/b.md"),
                copied=False,
            ),
        ],
        empty_message="No files found.",
        copied_label="copied",
        skipped_label="skipped",
        summary_prefix="Promoted review files",
    )

    assert lines[0] == (
        "copied\t/repo/.refinery/shared/stock/a.md\tfrom=/repo/.refinery/shared/review/a.md"
    )
    assert lines[1] == (
        "skipped\t/repo/.refinery/shared/stock/b.md\tfrom=/repo/.refinery/shared/review/b.md"
    )
    assert lines[-1] == "Promoted review files: copied=1 skipped=1"


def test_render_copy_results_output_handles_empty_results() -> None:
    assert render_copy_results_output(
        [],
        empty_message="No files found.",
        copied_label="copied",
        skipped_label="skipped",
        summary_prefix="Promoted review files",
    ) == ["No files found."]
