"""knowledge_refinery package."""

__all__ = ["__version__", "get_version"]

__version__ = "0.5.0"


def get_version() -> str:
    """Return the installed Knowledge Refinery version."""
    return __version__
