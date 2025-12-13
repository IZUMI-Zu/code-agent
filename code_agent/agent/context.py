"""
Agent execution context helpers.

Provides a ContextVar so any nested tooling calls can know which
worker (Planner/Coder/Reviewer) is currently active.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_current_worker: ContextVar[str | None] = ContextVar("current_worker", default=None)


def get_current_worker() -> str | None:
    """Return the worker name currently executing, if any."""
    return _current_worker.get()


@contextmanager
def worker_context(name: str) -> Iterator[None]:
    """Context manager that sets the current worker name for nested calls."""
    token = _current_worker.set(name)
    try:
        yield
    finally:
        _current_worker.reset(token)


__all__ = ["get_current_worker", "worker_context"]
