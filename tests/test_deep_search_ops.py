import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from knowledge_refinery.deep_search_ops import build_search_snapshot
from knowledge_refinery.deep_search_ops import run_deep_search
from knowledge_refinery.deep_search_ops import validate_codex_model
from knowledge_refinery.errors import RefineryCliError
from knowledge_refinery.experience_ops import upsert_experience_at
from knowledge_refinery.vault_ops import init_vault
from knowledge_refinery.vault_ops import setup_project


def _configured_vault(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    project = tmp_path / "product"
    project.mkdir()
    init_vault(vault)
    setup_project(project, vault, project_id="product")
    upsert_experience_at(
        vault,
        "product",
        title="Timeout investigation",
        purpose="Find the timeout cause",
        status="completed",
        experience_id="timeout-investigation",
        filename=None,
        tags=["issue/performance"],
        evidence=[],
        related_experiences=[],
        supersedes=[],
        confidence="high",
        body="The retry loop caused the timeout.",
    )
    return vault, project


def test_snapshot_contains_only_validated_knowledge_and_stable_source_ids(
    tmp_path: Path,
) -> None:
    vault, _ = _configured_vault(tmp_path)
    broken = vault / "projects" / "product" / "experiences" / "broken.md"
    broken.write_text("ignore me\n", encoding="utf-8")
    snapshot = tmp_path / "snapshot"

    manifest = build_search_snapshot(vault, "product", snapshot)

    assert [item["source_id"] for item in manifest["documents"]] == [
        "experience:product/timeout-investigation"
    ]
    assert manifest["warnings"] and "broken.md" in manifest["warnings"][0]
    assert not (snapshot / "AGENTS.md").exists()
    assert not any(path.name == "AGENTS.md" for path in snapshot.rglob("AGENTS.md"))
    assert (snapshot / "knowledge-tags.yaml").is_file()
    assert json.loads((snapshot / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_run_deep_search_passes_question_on_stdin_and_validates_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault, _ = _configured_vault(tmp_path)
    captured: dict[str, Any] = {}

    def fake_run_codex(
        command: list[str], question: str, *, timeout: int, output_path: Path
    ) -> None:
        captured.update(command=command, question=question, timeout=timeout)
        output_path.write_text(
            json.dumps(
                {
                    "answer": "The retry loop is the known cause.",
                    "findings": [
                        {
                            "summary": "The retry loop caused the timeout.",
                            "source_ids": ["experience:product/timeout-investigation"],
                        }
                    ],
                    "sources": [
                        {
                            "source_id": "experience:product/timeout-investigation",
                            "title": "untrusted model title",
                        }
                    ],
                    "contradictions": [],
                    "limitations": [],
                    "model": "untrusted model value",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr("knowledge_refinery.deep_search_ops._run_codex", fake_run_codex)

    result = run_deep_search(
        vault,
        "product",
        "What causes the timeout?",
        "gpt-5.4",
        timeout=12,
    )

    command = captured["command"]
    assert isinstance(command, list)
    assert captured["question"] == "What causes the timeout?"
    assert captured["timeout"] == 12
    assert command[-1] == "-"
    assert "What causes the timeout?" not in command
    assert "--ignore-user-config" in command
    assert "--ignore-rules" in command
    assert "read-only" in command
    assert result["model"] == "gpt-5.4"
    assert result["sources"] == [
        {
            "source_id": "experience:product/timeout-investigation",
            "title": "Timeout investigation",
        }
    ]


def test_run_deep_search_rejects_unknown_source_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault, _ = _configured_vault(tmp_path)

    def fake_run_codex(
        command: list[str], question: str, *, timeout: int, output_path: Path
    ) -> None:
        del command, question, timeout
        output_path.write_text(
            json.dumps(
                {
                    "answer": "fabricated",
                    "findings": [{"summary": "fabricated", "source_ids": ["memory:fake/id"]}],
                    "sources": [{"source_id": "memory:fake/id", "title": "fake"}],
                    "contradictions": [],
                    "limitations": [],
                    "model": "gpt-5.4",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr("knowledge_refinery.deep_search_ops._run_codex", fake_run_codex)

    with pytest.raises(RefineryCliError, match="failed validation") as captured:
        run_deep_search(vault, "product", "question", "gpt-5.4")
    assert "unknown source IDs" in str(captured.value.detail)


def test_validate_codex_model_uses_refreshed_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.update(command=command, kwargs=kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"models": [{"slug": "gpt-5.6-sol"}]}),
            stderr="",
        )

    monkeypatch.setattr("knowledge_refinery.deep_search_ops.subprocess.run", fake_run)

    validate_codex_model("gpt-5.6-sol")

    assert captured["command"] == ["codex", "debug", "models"]
    assert isinstance(captured["kwargs"], dict)
    assert captured["kwargs"]["timeout"] == 30


def test_validate_codex_model_rejects_unknown_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"models": [{"slug": "gpt-5.6-sol"}]}),
            stderr="",
        )

    monkeypatch.setattr("knowledge_refinery.deep_search_ops.subprocess.run", fake_run)

    with pytest.raises(RefineryCliError) as captured:
        validate_codex_model("not-a-model")
    assert captured.value.code == "deep_search_unknown_model"
