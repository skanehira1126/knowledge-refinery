from pathlib import Path

from knowledge_refinery.errors import RefineryConflictError
from knowledge_refinery.errors import RefineryFormatError


def test_repairable_errors_reference_distributed_maintenance_skill() -> None:
    format_error = RefineryFormatError(
        summary="Malformed document",
        path=Path("document.md"),
        detail="invalid YAML",
        expected="valid YAML",
    )
    conflict_error = RefineryConflictError(
        summary="Conflicting document",
        path=Path("document.md"),
        detail="stale revision",
        expected="current revision",
        suggested_action="Read and reconcile",
    )

    assert format_error.repair_skill == "refinery-maintenance"
    assert conflict_error.repair_skill == "refinery-maintenance"
    assert "repair_skill: refinery-maintenance" in format_error.render()
    assert str(format_error) == "Malformed document"
