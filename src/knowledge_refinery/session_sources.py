"""Discover and stream stored Codex rollout files."""

from collections.abc import Iterator
from contextlib import contextmanager
from io import BufferedIOBase
from pathlib import Path
import re
import sys


if sys.version_info >= (3, 14):
    from compression import zstd
else:
    from backports import zstd


def rollout_paths(roots: list[Path]) -> list[Path]:
    """Find each physical JSONL or zstd-compressed JSONL path once."""
    return sorted(
        {
            p.resolve()
            for root in roots
            for p in root.expanduser().rglob("*.jsonl*")
            if p.name.endswith((".jsonl", ".jsonl.zst"))
        }
    )


@contextmanager
def open_rollout(path: Path) -> Iterator[BufferedIOBase]:
    """Read JSONL bytes while keeping access to the underlying file descriptor."""
    with path.open("rb") as raw:
        if path.suffix == ".zst":
            try:
                with zstd.ZstdFile(raw) as stream:
                    yield stream
            except (EOFError, zstd.ZstdError) as error:
                raise ValueError(f"Cannot decompress rollout {path}: {error}") from error
        else:
            yield raw


def rollout_segment(path: Path, chat_id: str) -> str | None:
    """Identify a Codex-named base or continuation belonging to this metadata chat ID."""
    match = re.fullmatch(
        rf"rollout-\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}-\d{{2}}-\d{{2}}-{re.escape(chat_id)}"
        r"(?:_([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}))?\.jsonl(?:\.zst)?",
        path.name,
    )
    return (match[1] or "base") if match else None
