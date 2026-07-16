from __future__ import annotations

from contextlib import AbstractContextManager
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Durably replace a text file without exposing a partially written result."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        if path.exists():
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:  # pragma: no cover - platform and filesystem dependent
        return
    try:
        os.fsync(descriptor)
    except OSError:  # pragma: no cover - platform and filesystem dependent
        pass
    finally:
        os.close(descriptor)


class InterprocessLock(AbstractContextManager["InterprocessLock"]):
    """Small O_EXCL lock with timeout and conservative stale-lock recovery."""

    def __init__(
        self,
        target: Path,
        *,
        timeout: float = 10.0,
        stale_after: float = 60.0,
        poll_interval: float = 0.05,
    ) -> None:
        self.path = target.with_name(f".{target.name}.lock")
        self.timeout = timeout
        self.stale_after = stale_after
        self.poll_interval = poll_interval
        self.token = f"{os.getpid()}:{secrets.token_hex(16)}"
        self.acquired = False

    def __enter__(self) -> InterprocessLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                self._remove_if_stale()
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Timed out waiting for document lock: {self.path}"
                    ) from None
                time.sleep(self.poll_interval)
                continue
            try:
                os.write(descriptor, self.token.encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self.acquired = True
            return self

    def _remove_if_stale(self) -> None:
        try:
            age = time.time() - self.path.stat().st_mtime
        except FileNotFoundError:
            return
        if age <= self.stale_after:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if not self.acquired:
            return
        try:
            owner = self.path.read_text(encoding="ascii")
        except FileNotFoundError:
            return
        if owner == self.token:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        self.acquired = False


def interprocess_lock(
    target: Path,
    *,
    timeout: float = 10.0,
    stale_after: float = 60.0,
) -> InterprocessLock:
    return InterprocessLock(target, timeout=timeout, stale_after=stale_after)
