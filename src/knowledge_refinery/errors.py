"""Define structured user-facing errors for CLI and storage operations."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RefineryCliError(Exception):
    """Represent an actionable error that can be rendered for CLI users."""

    code: str
    summary: str
    path: Path | None = None
    detail: str | None = None
    expected: str | None = None
    repair_skill: str | None = None
    suggested_action: str | None = None
    exit_code: int = 2

    def __str__(self) -> str:
        """Return the concise error summary."""
        return self.summary

    def render(self) -> str:
        """Render all available diagnostic and repair fields as plain text."""
        lines = [
            f"refinery_error: {self.code}",
            f"summary: {self.summary}",
        ]
        if self.path is not None:
            lines.append(f"path: {self.path.as_posix()}")
        if self.detail:
            lines.append(f"detail: {self.detail}")
        if self.expected:
            lines.append(f"expected: {self.expected}")
        if self.repair_skill:
            lines.append(f"repair_skill: {self.repair_skill}")
        if self.suggested_action:
            lines.append(f"suggested_action: {self.suggested_action}")
        return "\n".join(lines)


class RefineryFormatError(RefineryCliError):
    """Report malformed persisted Knowledge Refinery data."""

    def __init__(
        self,
        *,
        summary: str,
        path: Path,
        detail: str,
        expected: str,
        suggested_action: str = (
            "Repair the file format, then rerun the same knowledge-refinery command."
        ),
    ) -> None:
        """Initialize a format error with the invalid path and expectation."""
        super().__init__(
            code="invalid_file_format",
            summary=summary,
            path=path,
            detail=detail,
            expected=expected,
            repair_skill="refinery-maintenance",
            suggested_action=suggested_action,
        )


class RefineryConflictError(RefineryCliError):
    """Report a conflicting update that requires rereading current data."""

    def __init__(
        self,
        *,
        summary: str,
        path: Path,
        detail: str,
        expected: str,
        suggested_action: str,
    ) -> None:
        """Initialize a conflict error with resolution guidance."""
        super().__init__(
            code="conflicting_knowledge",
            summary=summary,
            path=path,
            detail=detail,
            expected=expected,
            repair_skill="refinery-maintenance",
            suggested_action=suggested_action,
        )


class RefineryPathError(RefineryCliError):
    """Report a path that falls outside an allowed Knowledge Refinery root."""

    def __init__(
        self,
        *,
        summary: str,
        path: Path,
        detail: str,
        expected: str,
        suggested_action: str,
    ) -> None:
        """Initialize an invalid-path error with the expected boundary."""
        super().__init__(
            code="invalid_path",
            summary=summary,
            path=path,
            detail=detail,
            expected=expected,
            suggested_action=suggested_action,
        )
