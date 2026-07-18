from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RefineryCliError(Exception):
    code: str
    summary: str
    path: Path | None = None
    detail: str | None = None
    expected: str | None = None
    repair_skill: str | None = None
    suggested_action: str | None = None
    exit_code: int = 2

    def __str__(self) -> str:
        return self.summary

    def render(self) -> str:
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
    def __init__(
        self,
        *,
        summary: str,
        path: Path,
        detail: str,
        expected: str,
        suggested_action: str,
    ) -> None:
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
    def __init__(
        self,
        *,
        summary: str,
        path: Path,
        detail: str,
        expected: str,
        suggested_action: str,
    ) -> None:
        super().__init__(
            code="invalid_path",
            summary=summary,
            path=path,
            detail=detail,
            expected=expected,
            suggested_action=suggested_action,
        )
