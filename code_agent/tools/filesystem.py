"""
Filesystem Tools - Cross-Platform Abstraction
Design Philosophy:
    - Good Taste: Hide platform differences, provide unified interface
    - Simplicity: Each tool does ONE thing (create dir, copy file, etc.)
    - Pragmatism: Use Python stdlib, no external dependencies needed

Good Code vs Bad Code:
    ❌ Bad: Expose 'mkdir -p' vs 'mkdir' difference to Agent
    ✅ Good: Provide create_directory() that works everywhere
"""

import shutil

from pydantic import BaseModel, Field

from code_agent.utils.path import get_relative_path, resolve_workspace_path

from .base import BaseTool

# Directory Operations


class CreateDirectoryArgs(BaseModel):
    path: str = Field(..., description="Path to create")
    recursive: bool = Field(True, description="Create parent directories if needed (default: True)")


class CreateDirectoryTool(BaseTool):
    """
    Create directory (cross-platform)

    Good Taste:
      - Single line of implementation: Path.mkdir(parents=True, exist_ok=True)
      - No special cases for Windows/Linux/Mac
      - No shell commands, pure Python
    """

    def __init__(self):
        super().__init__(
            name="create_directory",
            description="Create a directory. Automatically creates parent directories. Works on all platforms.",
        )

    def _run(self, path: str, recursive: bool = True) -> str:
        target = resolve_workspace_path(path)

        rel_path = get_relative_path(target)

        # Check if already exists
        if target.exists():
            if target.is_dir():
                return f"Directory already exists: {rel_path}"
            raise FileExistsError(f"Path exists but is not a directory: {rel_path}")

        # Create directory
        target.mkdir(parents=recursive, exist_ok=True)

        return f"Created directory: {rel_path}"

    def get_args_schema(self) -> type[BaseModel]:
        return CreateDirectoryArgs


# File Operations


class CopyFileArgs(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination path")


class CopyFileTool(BaseTool):
    """
    Copy file (cross-platform)

    Good Taste:
      - Use shutil.copy2 (preserves metadata)
      - Handles both file-to-file and file-to-directory
      - No shell commands needed
    """

    def __init__(self):
        super().__init__(
            name="copy_file",
            description="Copy a file to another location. Preserves metadata. Works on all platforms.",
        )

    def _run(self, source: str, destination: str) -> str:
        src = resolve_workspace_path(source)
        dst = resolve_workspace_path(destination)

        # Validate source
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        if not src.is_file():
            raise ValueError(f"Source is not a file: {src}")

        # If destination is a directory, preserve filename
        if dst.is_dir():
            dst = dst / src.name

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy
        shutil.copy2(src, dst)

        return f"Copied {get_relative_path(src)} → {get_relative_path(dst)}"

    def get_args_schema(self) -> type[BaseModel]:
        return CopyFileArgs


class MoveFileArgs(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination path")


class MoveFileTool(BaseTool):
    """
    Move/rename file (cross-platform)

    Good Taste:
      - Single shutil.move() call
      - Works across drives on Windows
      - Handles both files and directories
    """

    def __init__(self):
        super().__init__(
            name="move_file",
            description="Move or rename a file/directory. Works across drives and platforms.",
        )

    def _run(self, source: str, destination: str) -> str:
        src = resolve_workspace_path(source)
        dst = resolve_workspace_path(destination)

        if not src.exists():
            raise FileNotFoundError(f"Source not found: {get_relative_path(src)}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Move
        shutil.move(str(src), str(dst))

        return f"Moved {get_relative_path(src)} → {get_relative_path(dst)}"

    def get_args_schema(self) -> type[BaseModel]:
        return MoveFileArgs


class DeletePathArgs(BaseModel):
    path: str = Field(..., description="Path to delete")
    recursive: bool = Field(False, description="Delete directories recursively (default: False)")


class DeletePathTool(BaseTool):
    """
    Delete file or directory (cross-platform)

    Good Taste:
      - Unified deletion API (no rm vs del difference)
      - Safe by default (recursive=False)
      - Clear error messages
    """

    def __init__(self):
        super().__init__(
            name="delete_path",
            description="Delete a file or directory. Use recursive=True for non-empty directories.",
        )

    def _run(self, path: str, recursive: bool = False) -> str:
        target = resolve_workspace_path(path)

        rel_path = get_relative_path(target)

        if not target.exists():
            raise FileNotFoundError(f"Path not found: {rel_path}")

        # Delete based on type
        if target.is_file():
            target.unlink()
            return f"Deleted file: {rel_path}"
        if target.is_dir():
            if recursive:
                shutil.rmtree(target)
                return f"Deleted directory (recursive): {rel_path}"
            # Check if empty
            if any(target.iterdir()):
                raise ValueError(f"Directory not empty. Use recursive=True to delete: {rel_path}")
            target.rmdir()
            return f"Deleted directory: {rel_path}"
        raise ValueError(f"Unknown path type: {rel_path}")

    def get_args_schema(self) -> type[BaseModel]:
        return DeletePathArgs


# Path Operations


class PathExistsArgs(BaseModel):
    path: str = Field(..., description="Path to check")


class PathExistsTool(BaseTool):
    """
    Check if path exists

    Good Taste:
      - Simple boolean check
      - Returns structured info (exists + type)
    """

    def __init__(self):
        super().__init__(
            name="path_exists",
            description="Check if a path exists and return its type (file/directory/none).",
        )

    def _run(self, path: str) -> str:
        target = resolve_workspace_path(path)

        rel_path = get_relative_path(target)

        if not target.exists():
            return f"Path does not exist: {rel_path}"

        if target.is_file():
            size = target.stat().st_size
            return f"File exists: {rel_path} (size: {size} bytes)"
        if target.is_dir():
            count = sum(1 for _ in target.iterdir())
            return f"Directory exists: {rel_path} (contains {count} items)"
        return f"Path exists (unknown type): {rel_path}"

    def get_args_schema(self) -> type[BaseModel]:
        return PathExistsArgs
