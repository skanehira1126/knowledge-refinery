from pathlib import Path

import yaml

from knowledge_refinery.front_matter import split_front_matter
from knowledge_refinery.session_metadata import build_directory_agents
from knowledge_refinery.session_metadata import init_session
from knowledge_refinery.session_metadata import update_session
from knowledge_refinery.session_metadata import write_yaml


def test_write_yaml_strips_disallowed_yaml_characters(tmp_path: Path) -> None:
    path = tmp_path / "meta.yaml"

    write_yaml(
        path,
        {
            "title": "Alpha\x00Beta",
            "tags": ["one\x1ftwo", "three"],
            "note": "line1\nline2",
        },
    )

    rendered = path.read_text(encoding="utf-8")

    assert "\x00" not in rendered
    assert 'title: "AlphaBeta"' in rendered
    assert 'note: "line1\\nline2"' in rendered
    assert '  - "onetwo"' in rendered or '- "onetwo"' in rendered
    assert yaml.safe_load(rendered) == {
        "title": "AlphaBeta",
        "tags": ["onetwo", "three"],
        "note": "line1\nline2",
    }


def test_build_directory_agents_quotes_yaml_sensitive_text() -> None:
    rendered = build_directory_agents(
        title="Needs: quoting\nsecond\x00line",
        description="desc\x1fvalue",
        layer="raw",
        body_lines=["keep body"],
    )

    assert 'title: "Needs: quoting\\nsecondline"' in rendered
    assert 'description: "descvalue"' in rendered

    header, body = split_front_matter(rendered)

    assert header == {
        "title": "Needs: quoting\nsecondline",
        "description": "descvalue",
        "kind": "directory_rules",
        "layer": "raw",
    }
    assert body == "- keep body"


def test_init_session_sanitizes_user_text_before_writing_meta_yaml(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"

    session_root = init_session(
        root,
        task="Investigate\x00 YAML",
        kind="investigation",
        title="Bad:\nTitle\x1f",
        created_by="codex",
        repository=None,
        domain=None,
    )

    rendered = (session_root / "meta.yaml").read_text(encoding="utf-8")
    assert 'task: "Investigate YAML"' in rendered
    assert 'title: "Bad:\\nTitle"' in rendered

    meta = yaml.safe_load(rendered)
    assert meta["task"] == "Investigate YAML"
    assert meta["title"] == "Bad:\nTitle"


def test_update_session_updates_selected_fields_and_preserves_others(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    session_root = init_session(
        root,
        task="Initial task",
        kind="task",
        title="Initial title",
        created_by="codex",
        repository="repo-a",
        domain="backend",
    )
    session_id = session_root.name

    meta_path, updated = update_session(
        root,
        session_id=session_id,
        updates={
            "status": "paused",
            "phase": "analysis",
            "next_action": "wait for input",
            "flow_status": "in_progress",
        },
        clear_fields=[],
    )

    assert meta_path == session_root / "meta.yaml"
    assert updated["title"] == "Initial title"
    assert updated["repository"] == "repo-a"
    assert updated["status"] == "paused"
    assert updated["phase"] == "analysis"
    assert updated["next_action"] == "wait for input"
    assert updated["flow_status"] == "in_progress"
    assert updated["last_updated_at"] is not None
    assert updated["last_flow_update_at"] is not None


def test_update_session_can_clear_nullable_fields(tmp_path: Path) -> None:
    root = tmp_path / ".refinery"
    session_root = init_session(
        root,
        task="Initial task",
        kind="task",
        title="Initial title",
        created_by="codex",
        repository="repo-a",
        domain="backend",
    )
    session_id = session_root.name

    _meta_path, updated = update_session(
        root,
        session_id=session_id,
        updates={"blocked_reason": "waiting", "resume_condition": "reply arrives"},
        clear_fields=[],
    )
    assert updated["blocked_reason"] == "waiting"
    assert updated["resume_condition"] == "reply arrives"

    _meta_path, cleared = update_session(
        root,
        session_id=session_id,
        updates={},
        clear_fields=["blocked_reason", "resume_condition", "domain", "repository"],
    )

    assert cleared["blocked_reason"] is None
    assert cleared["resume_condition"] is None
    assert cleared["domain"] is None
    assert cleared["repository"] is None
