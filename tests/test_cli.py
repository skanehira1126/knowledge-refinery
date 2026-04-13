from __future__ import annotations

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
from knowledge_refinery.errors import RefineryPathError
from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.front_matter import list_headers_filtered
from knowledge_refinery.session_metadata import read_yaml_mapping
from knowledge_refinery.template_ops import TEMPLATE_METADATA_RELATIVE_PATH
from knowledge_refinery.template_ops import apply_template
from knowledge_refinery.template_ops import copy_tree


def test_parser_accepts_update_template() -> None:
    args = cli.build_parser().parse_args(
        ["update-template", "--target", "/tmp/example", "--skill-destination", "agent"]
    )

    assert args.handler is cli.run_update_template
    assert args.target == "/tmp/example"
    assert args.skill_destination == "agent"


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
            exit_code = cli.main(["list-sessions", "--root", str(root)])

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
            exit_code = cli.main(["list-sessions", "--root", str(root)])

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
            exit_code = cli.main(["list-headers", "--root", str(root)])

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
            exit_code = cli.main(["list-sessions", "--root", str(root)])

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

    def fake_run_list_sessions(_args: Namespace) -> int:
        raise conflict

    monkeypatch.setattr(cli, "run_list_sessions", fake_run_list_sessions)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli.main(["list-sessions"])

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


def test_run_list_headers_session_id_without_scope_implies_raw_and_flow() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        target_raw = root / "sessions" / "s1" / "raw" / "raw.md"
        target_flow = root / "sessions" / "s1" / "flow" / "flow.md"
        other_flow = root / "sessions" / "s2" / "flow" / "other.md"
        review = root / "shared" / "review" / "s1--review.md"
        for path in (target_raw, target_flow, other_flow, review):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n"
                "title: T\n"
                "description: D\n"
                "---\n",
                encoding="utf-8",
            )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = cli.run_list_headers(
                Namespace(root=str(root), scope=[], session_id="s1")
            )

        assert exit_code == 0
        output = stdout.getvalue()
        assert target_raw.as_posix() in output
        assert target_flow.as_posix() in output
        assert other_flow.as_posix() not in output
        assert review.as_posix() not in output


def test_list_headers_filtered_with_flow_scope_and_session_id_filters_results() -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        target_flow = root / "sessions" / "s1" / "flow" / "flow.md"
        other_flow = root / "sessions" / "s2" / "flow" / "other.md"
        for path in (target_flow, other_flow):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n"
                "title: T\n"
                "description: D\n"
                "---\n",
                encoding="utf-8",
            )

        entries = list_headers_filtered(root, scopes=["flow"], session_id="s1")

        assert [path for path, _header in entries] == [target_flow]


def test_list_headers_filtered_wraps_unreadable_file_as_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir) / ".refinery"
        target = root / "sessions" / "s1" / "flow" / "flow.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("---\ntitle: T\ndescription: D\n---\n", encoding="utf-8")
        original_read_text = Path.read_text

        def fake_read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path == target:
                raise PermissionError("denied")
            return original_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fake_read_text)

        with pytest.raises(RefineryPathError):
            list_headers_filtered(root, scopes=["flow"], session_id="s1")


def test_read_yaml_mapping_wraps_unreadable_file_as_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as root_dir:
        meta_path = Path(root_dir) / ".refinery" / "sessions" / "s1" / "meta.yaml"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text("session_id: s1\n", encoding="utf-8")
        original_read_text = Path.read_text

        def fake_read_text(path: Path, *args: object, **kwargs: object) -> str:
            if path == meta_path:
                raise FileNotFoundError("missing")
            return original_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fake_read_text)

        with pytest.raises(RefineryPathError):
            read_yaml_mapping(meta_path)
