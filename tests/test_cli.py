from argparse import Namespace
from contextlib import redirect_stderr
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile

import pytest
import yaml

from knowledge_refinery import __version__
from knowledge_refinery import get_version
import knowledge_refinery.cli as cli
from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.template_ops import TEMPLATE_METADATA_RELATIVE_PATH
from knowledge_refinery.template_ops import apply_template
from knowledge_refinery.template_ops import copy_tree


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_meta(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parser_accepts_update_template() -> None:
    args = cli.build_parser().parse_args(
        ["update-template", "--target", "/tmp/example", "--skill-destination", "agent"]
    )

    assert args.handler is cli.run_update_template
    assert args.target == "/tmp/example"
    assert args.skill_destination == "agent"


def test_parser_accepts_skills_search_knowledge() -> None:
    args = cli.build_parser().parse_args(
        [
            "skills",
            "search",
            "knowledge",
            "api",
            "rate",
            "--scope",
            "flow",
            "--tag",
            "domain/api",
        ]
    )

    assert args.handler is cli.run_search_knowledge
    assert args.command == "skills"
    assert args.skills_command == "search"
    assert args.terms == ["api", "rate"]
    assert args.scope == ["flow"]
    assert args.tag == ["domain/api"]


def test_parser_accepts_skills_update_session() -> None:
    args = cli.build_parser().parse_args(
        [
            "skills",
            "update-session",
            "--session-id",
            "session-123",
            "--status",
            "paused",
            "--clear-domain",
        ]
    )

    assert args.handler is cli.run_update_session
    assert args.command == "skills"
    assert args.skills_command == "update-session"
    assert args.session_id == "session-123"
    assert args.status == "paused"
    assert args.clear_domain is True


def test_parser_rejects_legacy_top_level_update_session_alias() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            [
                "update-session",
                "--session-id",
                "session-123",
                "--status",
                "paused",
                "--clear-domain",
            ]
        )


def test_get_version_returns_package_version() -> None:
    assert get_version() == __version__


def test_run_apply_template_mentions_update_template(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_apply_template(
        target_root: Path, *, force: bool, skill_destination: str
    ) -> tuple[Path, list[Path]]:
        called["target_root"] = target_root
        called["force"] = force
        called["skill_destination"] = skill_destination
        return Path("/template"), [Path("/repo/.codex/skills/refinery-session/SKILL.md")]

    monkeypatch.setattr(cli, "apply_template", fake_apply_template)
    args = Namespace(target="/repo", force=False, skill_destination="codex")

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = cli.run_apply_template(args)

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": False,
        "skill_destination": "codex",
    }
    assert "update-template" in stdout.getvalue()


def test_run_update_template_forces_template_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_apply_template(
        target_root: Path, *, force: bool, skill_destination: str
    ) -> tuple[Path, list[Path]]:
        called["target_root"] = target_root
        called["force"] = force
        called["skill_destination"] = skill_destination
        return Path("/template"), [Path("/repo/.agent/skills/refinery-session/SKILL.md")]

    monkeypatch.setattr(cli, "apply_template", fake_apply_template)
    args = Namespace(target="/repo", skill_destination="agent")

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = cli.run_update_template(args)

    assert exit_code == 0
    assert called == {
        "target_root": Path("/repo").resolve(),
        "force": True,
        "skill_destination": "agent",
    }
    output = stdout.getvalue()
    assert "Updated files: 1" in output
    assert "Skill destination: .agent/skills" in output
    assert "update-agents-md" in output
    assert "state.md is preserved" in output


def test_copy_tree_preserves_existing_shared_state_on_force() -> None:
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = Path(src_dir)
        dst = Path(dst_dir)

        (src / "refinery" / "shared").mkdir(parents=True)
        (src / "refinery" / "shared" / "state.md").write_text("template state\n", encoding="utf-8")
        (dst / ".refinery" / "shared").mkdir(parents=True)
        target_state = dst / ".refinery" / "shared" / "state.md"
        target_state.write_text("live state\n", encoding="utf-8")

        copied = copy_tree(src, dst, force=True)

        assert copied == []
        assert target_state.read_text(encoding="utf-8") == "live state\n"


def test_copy_tree_creates_shared_state_when_missing() -> None:
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src = Path(src_dir)
        dst = Path(dst_dir)

        (src / "refinery" / "shared").mkdir(parents=True)
        (src / "refinery" / "shared" / "state.md").write_text("template state\n", encoding="utf-8")

        copied = copy_tree(src, dst, force=True)

        assert copied == [dst / ".refinery" / "shared" / "state.md"]
        assert (dst / ".refinery" / "shared" / "state.md").read_text(
            encoding="utf-8"
        ) == "template state\n"


def test_apply_template_writes_template_metadata() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        target_root = Path(target_dir)

        _, copied = apply_template(target_root, force=False, skill_destination="codex")

        metadata_path = target_root / TEMPLATE_METADATA_RELATIVE_PATH
        assert metadata_path in copied
        assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
            "cli_version": __version__,
        }


def test_apply_template_distributes_core_skills() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        target_root = Path(target_dir)

        _, copied = apply_template(target_root, force=False, skill_destination="codex")

        expected = [
            target_root / ".codex" / "skills" / "refinery-session" / "SKILL.md",
            target_root / ".codex" / "skills" / "refinery-capture" / "SKILL.md",
            target_root / ".codex" / "skills" / "refinery-curation" / "SKILL.md",
            target_root / ".codex" / "skills" / "refinery-shared" / "SKILL.md",
            target_root / ".codex" / "skills" / "refinery-repair" / "SKILL.md",
        ]

        for path in expected:
            assert path.exists()
            assert path in copied


def test_apply_template_preserves_existing_metadata_without_force() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        target_root = Path(target_dir)
        metadata_path = target_root / TEMPLATE_METADATA_RELATIVE_PATH
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            "cli_version: 0.0.1\n",
            encoding="utf-8",
        )

        _, copied = apply_template(target_root, force=False, skill_destination="codex")

        assert metadata_path not in copied
        assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
            "cli_version": "0.0.1",
        }


def test_apply_template_overwrites_existing_metadata_with_force() -> None:
    with tempfile.TemporaryDirectory() as target_dir:
        target_root = Path(target_dir)
        metadata_path = target_root / TEMPLATE_METADATA_RELATIVE_PATH
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            "cli_version: 0.0.1\n",
            encoding="utf-8",
        )

        _, copied = apply_template(target_root, force=True, skill_destination="codex")

        assert metadata_path in copied
        assert yaml.safe_load(metadata_path.read_text(encoding="utf-8")) == {
            "cli_version": __version__,
        }


def test_main_warns_when_template_cli_version_differs() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        root.mkdir(parents=True)
        (root / "template-meta.yaml").write_text("cli_version: 9.9.9\n", encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["skills", "search", "sessions", "--root", str(root)])

        assert exit_code == 0
        assert "No sessions found." in stdout.getvalue()
        assert "applied with CLI version 9.9.9" in stderr.getvalue()
        assert __version__ in stderr.getvalue()


def test_main_does_not_warn_when_template_cli_version_matches() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        root.mkdir(parents=True)
        (root / "template-meta.yaml").write_text(f"cli_version: {__version__}\n", encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["skills", "search", "sessions", "--root", str(root)])

        assert exit_code == 0
        assert "No sessions found." in stdout.getvalue()
        assert stderr.getvalue() == ""


def test_main_renders_structured_error_for_invalid_front_matter() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        bad_file = root / "sessions" / "session-123" / "flow" / "bad.md"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("---\n- invalid\n---\n", encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(
                ["skills", "search", "knowledge", "--root", str(root), "--scope", "flow"]
            )

        assert exit_code == 2
        assert stdout.getvalue() == ""
        rendered = stderr.getvalue()
        assert "refinery_error: invalid_file_format" in rendered
        rendered_path = next(
            line.removeprefix("path: ")
            for line in rendered.splitlines()
            if line.startswith("path: ")
        )
        assert Path(rendered_path).resolve() == bad_file.resolve()
        assert "repair_skill: refinery-repair" in rendered
        assert "Traceback" not in rendered


def test_main_renders_structured_error_for_invalid_meta_yaml() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        meta_path = root / "sessions" / "session-123" / "meta.yaml"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text("- invalid\n", encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["skills", "search", "sessions", "--root", str(root)])

        assert exit_code == 2
        assert stdout.getvalue() == ""
        rendered = stderr.getvalue()
        assert "refinery_error: invalid_file_format" in rendered
        rendered_path = next(
            line.removeprefix("path: ")
            for line in rendered.splitlines()
            if line.startswith("path: ")
        )
        assert Path(rendered_path).resolve() == meta_path.resolve()
        assert "repair_skill: refinery-repair" in rendered


def test_main_renders_structured_error_for_refinery_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conflict = RefineryConflictError(
        summary="Multiple flow files resolve to the same review file.",
        path=Path("/repo/.refinery/sessions/s1/flow/topic.md"),
        detail="knowledge_id collision",
        expected="Each flow file in the same session should produce a unique review target.",
        suggested_action="Fix the conflicting knowledge_id and rerun the command.",
    )

    def fake_run_search_sessions(_args: Namespace) -> int:
        raise conflict

    monkeypatch.setattr(cli, "run_search_sessions", fake_run_search_sessions)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli.main(["skills", "search", "sessions"])

    assert exit_code == 2
    assert stdout.getvalue() == ""
    rendered = stderr.getvalue()
    assert "refinery_error: conflicting_knowledge" in rendered
    assert "repair_skill: refinery-repair" in rendered


def test_main_renders_structured_error_for_missing_review_file() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        missing_review_path = root / "shared" / "review" / "missing.md"

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(
                [
                    "skills",
                    "promote-review",
                    "--root",
                    str(root),
                    "--review-file",
                    str(missing_review_path),
                ]
            )

        assert exit_code == 2
        assert stdout.getvalue() == ""
        rendered = stderr.getvalue()
        assert "refinery_error: invalid_path" in rendered
        rendered_path = next(
            line.removeprefix("path: ")
            for line in rendered.splitlines()
            if line.startswith("path: ")
        )
        assert Path(rendered_path).resolve() == missing_review_path.resolve()
        assert "Traceback" not in rendered


def test_search_knowledge_lists_default_flow_and_stock_only() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        write_markdown(
            root / "sessions" / "session-123" / "raw" / "raw-note.md",
            """---
title: Raw Note
description: Raw observation
---

Body
""",
        )
        write_markdown(
            root / "sessions" / "session-123" / "flow" / "api-rate-limit.md",
            """---
title: API Rate Limit
description: Flow notes
summary: Summary text
tags:
  - domain/api
---

Observed retries
""",
        )
        write_markdown(
            root / "shared" / "stock" / "api-rate-limit.md",
            """---
title: API Rate Limit Stock
description: Stock notes
summary: Stable summary
knowledge_id: api-rate-limit
source_sessions:
  - session-123
derived_from:
  - .refinery/shared/review/session-123--api-rate-limit.md
tags:
  - domain/api
---

Stable body
""",
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(["skills", "search", "knowledge", "--root", str(root)])

        assert exit_code == 0
        output = stdout.getvalue()
        assert 'scope="flow"' in output
        assert 'scope="stock"' in output
        assert 'scope="raw"' not in output
        assert stderr.getvalue() == ""


def test_search_knowledge_supports_and_terms_and_exact_filters() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        write_markdown(
            root / "sessions" / "session-123" / "flow" / "api-rate-limit.md",
            """---
title: API Rate Limit
description: Flow notes
summary: Burst rate limits
knowledge_id: api-rate-limit
tags:
  - domain/api
  - issue/rate-limit
source_sessions:
  - session-123
---

Rate limit behavior for API retries
""",
        )
        write_markdown(
            root / "sessions" / "session-999" / "flow" / "auth.md",
            """---
title: Auth
description: Different topic
summary: Login notes
knowledge_id: auth-notes
tags:
  - domain/auth
---

No rate content
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "search",
                    "knowledge",
                    "API",
                    "rate",
                    "--root",
                    str(root),
                    "--scope",
                    "flow",
                    "--tag",
                    "domain/api",
                    "--knowledge-id",
                    "api-rate-limit",
                ]
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert '"knowledge_id"="api-rate-limit"' not in output
        assert 'knowledge_id="api-rate-limit"' in output
        assert 'title="API Rate Limit"' in output
        assert 'title="Auth"' not in output


def test_search_knowledge_raw_scope_respects_session_filter() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        write_markdown(
            root / "sessions" / "session-123" / "raw" / "first.md",
            """---
title: API Error
description: Raw note
---

Observed command failure
""",
        )
        write_markdown(
            root / "sessions" / "session-999" / "raw" / "second.md",
            """---
title: API Error
description: Other session
---

Observed elsewhere
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "search",
                    "knowledge",
                    "--root",
                    str(root),
                    "--scope",
                    "raw",
                    "--session-id",
                    "session-123",
                ]
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert "session-123/raw/first.md" in output
        assert "session-999/raw/second.md" not in output


def test_search_review_can_include_rejected_files() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        write_markdown(
            root / "shared" / "review" / "session-123--api-rate-limit.md",
            """---
title: API Rate Limit
description: Review note
summary: Active review
knowledge_id: api-rate-limit
source_sessions:
  - session-123
tags:
  - domain/api
---

Active body
""",
        )
        write_markdown(
            root / "shared" / "review" / "rejected" / "session-999--auth.md",
            """---
title: Auth Review
description: Rejected review note
summary: Rejected review
knowledge_id: auth-review
source_sessions:
  - session-999
tags:
  - domain/auth
---

Rejected body
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "search",
                    "review",
                    "--root",
                    str(root),
                    "--include-rejected",
                ]
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert 'knowledge_id="api-rate-limit"' in output
        assert 'knowledge_id="auth-review"' in output


def test_search_sessions_reads_meta_and_state_and_filters() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        session_root = root / "sessions" / "session-123"
        write_meta(
            session_root / "meta.yaml",
            """session_id: session-123
kind: task
title: Investigate API rate limit
task: Investigate retry strategy
created_at: 2026-04-17T00:00:00Z
created_by: user
repository: null
domain: backend
status: active
phase: capture
current_step: collecting notes
next_action: summarize findings
last_updated_at: 2026-04-17T00:00:00Z
closed_at: null
blocked_reason: null
resume_condition: null
parent_session_id: null
child_session_ids: []
related_sessions: []
depends_on: []
supersedes: []
superseded_by: null
evidence_status: collecting
flow_status: not_started
synthesis_status: not_started
coverage_status: unknown
confidence: low
raw_item_count: 0
flow_item_count: 0
last_flow_update_at: null
""",
        )
        write_markdown(
            session_root / "state.md",
            """---
title: Session State
description: Current state
---

- 目的: investigate API retry
- 進捗: captured evidence
""",
        )
        write_meta(
            root / "sessions" / "session-999" / "meta.yaml",
            """session_id: session-999
kind: task
title: Other work
task: Different task
created_at: 2026-04-17T00:00:00Z
created_by: user
repository: null
domain: frontend
status: closed
phase: done
current_step: none
next_action: none
last_updated_at: 2026-04-17T00:00:00Z
closed_at: null
blocked_reason: null
resume_condition: null
parent_session_id: null
child_session_ids: []
related_sessions: []
depends_on: []
supersedes: []
superseded_by: null
evidence_status: collecting
flow_status: done
synthesis_status: done
coverage_status: complete
confidence: medium
raw_item_count: 0
flow_item_count: 0
last_flow_update_at: null
""",
        )
        write_markdown(
            root / "sessions" / "session-999" / "state.md",
            """---
title: Session State
description: Current state
---

- 目的: other
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "search",
                    "sessions",
                    "captured",
                    "--root",
                    str(root),
                    "--status",
                    "active",
                    "--phase",
                    "capture",
                    "--domain",
                    "backend",
                ]
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert 'session_id="session-123"' in output
        assert 'title="Investigate API rate limit"' in output
        assert 'session_id="session-999"' not in output


def test_update_session_updates_selected_fields() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        session_root = root / "sessions" / "session-123"
        write_meta(
            session_root / "meta.yaml",
            """session_id: session-123
kind: task
title: Initial title
task: Initial task
created_at: 2026-04-17T00:00:00Z
created_by: user
repository: repo-a
domain: backend
status: active
phase: capture
current_step: collecting notes
next_action: summarize findings
last_updated_at: 2026-04-17T00:00:00Z
closed_at: null
blocked_reason: null
resume_condition: null
parent_session_id: null
child_session_ids: []
related_sessions: []
depends_on: []
supersedes: []
superseded_by: null
evidence_status: collecting
flow_status: not_started
synthesis_status: not_started
coverage_status: unknown
confidence: low
raw_item_count: 0
flow_item_count: 0
last_flow_update_at: null
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "update-session",
                    "--root",
                    str(root),
                    "--session-id",
                    "session-123",
                    "--status",
                    "paused",
                    "--phase",
                    "analysis",
                    "--next-action",
                    "wait for input",
                    "--flow-status",
                    "in_progress",
                ]
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert 'session_id="session-123"' in output
        assert 'status="paused"' in output
        assert 'phase="analysis"' in output
        assert 'flow_status="in_progress"' in output

        meta = yaml.safe_load((session_root / "meta.yaml").read_text(encoding="utf-8"))
        assert meta["status"] == "paused"
        assert meta["phase"] == "analysis"
        assert meta["next_action"] == "wait for input"
        assert meta["flow_status"] == "in_progress"
        assert meta["title"] == "Initial title"
        assert meta["last_flow_update_at"] is not None


def test_update_session_can_clear_nullable_fields() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        session_root = root / "sessions" / "session-123"
        write_meta(
            session_root / "meta.yaml",
            """session_id: session-123
kind: task
title: Initial title
task: Initial task
created_at: 2026-04-17T00:00:00Z
created_by: user
repository: repo-a
domain: backend
status: active
phase: capture
current_step: collecting notes
next_action: summarize findings
last_updated_at: 2026-04-17T00:00:00Z
closed_at: null
blocked_reason: blocked
resume_condition: reply
parent_session_id: null
child_session_ids: []
related_sessions: []
depends_on: []
supersedes: []
superseded_by: null
evidence_status: collecting
flow_status: not_started
synthesis_status: not_started
coverage_status: unknown
confidence: low
raw_item_count: 0
flow_item_count: 0
last_flow_update_at: null
""",
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.main(
                [
                    "skills",
                    "update-session",
                    "--root",
                    str(root),
                    "--session-id",
                    "session-123",
                    "--clear-blocked-reason",
                    "--clear-resume-condition",
                    "--clear-domain",
                    "--clear-repository",
                ]
            )

        assert exit_code == 0
        meta = yaml.safe_load((session_root / "meta.yaml").read_text(encoding="utf-8"))
        assert meta["blocked_reason"] is None
        assert meta["resume_condition"] is None
        assert meta["domain"] is None
        assert meta["repository"] is None


def test_update_session_requires_at_least_one_change() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        session_root = root / "sessions" / "session-123"
        write_meta(
            session_root / "meta.yaml",
            """session_id: session-123
kind: task
title: Initial title
task: Initial task
created_at: 2026-04-17T00:00:00Z
created_by: user
repository: null
domain: null
status: active
phase: capture
current_step: collecting notes
next_action: summarize findings
last_updated_at: 2026-04-17T00:00:00Z
closed_at: null
blocked_reason: null
resume_condition: null
parent_session_id: null
child_session_ids: []
related_sessions: []
depends_on: []
supersedes: []
superseded_by: null
evidence_status: collecting
flow_status: not_started
synthesis_status: not_started
coverage_status: unknown
confidence: low
raw_item_count: 0
flow_item_count: 0
last_flow_update_at: null
""",
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(
                [
                    "skills",
                    "update-session",
                    "--root",
                    str(root),
                    "--session-id",
                    "session-123",
                ]
            )

        assert exit_code == 2
        assert stdout.getvalue() == ""
        assert "refinery_error: session_update_required" in stderr.getvalue()
