"""
Workspace path helpers.

These utilities ensure all filesystem interactions stay inside the configured
workspace root. Tools should resolve every incoming path through
`resolve_workspace_path` before attempting to read or write.
"""

from pathlib import Path

from src.config import settings


def resolve_workspace_path(path_str: str) -> Path:
    """Resolve *path_str* against the workspace root and validate containment."""
    path = Path(path_str)
    if not path.is_absolute():
        path = settings.workspace_root / path

    resolved_path = path.resolve()
    workspace_root = settings.workspace_root.resolve()

    try:
        resolved_path.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"Access denied: Path {path_str} is outside the workspace") from exc

    return resolved_path


def get_relative_path(absolute_path: Path) -> str:
    """
    Convert an absolute path to a workspace-relative path string.

    This hides the actual filesystem location from the agent,
    making it think it's operating in the current directory.
    """
    workspace_root = settings.workspace_root.resolve()
    try:
        rel = absolute_path.resolve().relative_to(workspace_root)
        # Return "." for workspace root itself
        return str(rel) if str(rel) != "." else "."
    except ValueError:
        # Fallback to absolute path if not in workspace (shouldn't happen)
        return str(absolute_path)
