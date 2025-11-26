"""
═══════════════════════════════════════════════════════════════
File Operation Tools
═══════════════════════════════════════════════════════════════
Implementation Principles:
  - Each tool does one thing (read/write/list)
  - Parameter validation upfront, avoiding deep nesting
  - Clear and actionable error messages
"""

from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import BaseTool

# ═══════════════════════════════════════════════════════════════
# File Read Tool
# ═══════════════════════════════════════════════════════════════


class ReadFileArgs(BaseModel):
    file_path: str = Field(
        ..., description="Path to the file to read (absolute or relative)"
    )
    start_line: Optional[int] = Field(None, description="Start line number (1-based)")
    end_line: Optional[int] = Field(None, description="End line number (inclusive)")


class ReadFileTool(BaseTool):
    """Read file content"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read content of a file. Supports reading specific line ranges.",
        )

    def _run(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        path = Path(file_path)

        # Upfront validation
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Read content
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try fallback encoding
            content = path.read_text(encoding="latin-1")

        lines = content.splitlines()
        total_lines = len(lines)

        # Handle line range
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else total_lines

            # Boundary check
            start = max(0, start)
            end = min(total_lines, end)

            if start >= end:
                return f"File {file_path} (Range {start_line}-{end_line} is empty)"

            selected_lines = lines[start:end]
            content = "\n".join(selected_lines)
            return f"File {file_path} (Lines {start + 1}-{end}/{total_lines}):\n\n{content}"

        return f"File Content ({len(content)} chars):\n\n{content}"

    def get_args_schema(self) -> Type[BaseModel]:
        return ReadFileArgs


# ═══════════════════════════════════════════════════════════════
# File Write Tool
# ═══════════════════════════════════════════════════════════════


class WriteFileArgs(BaseModel):
    file_path: str = Field(..., description="Target file path")
    content: str = Field(..., description="Content to write")


class WriteFileTool(BaseTool):
    """Write file content (Overwrite mode)"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write content to a file. Overwrites if exists, creates if not.",
        )

    def _run(self, file_path: str, content: str) -> str:
        path = Path(file_path)

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} chars to: {file_path}"

    def get_args_schema(self) -> Type[BaseModel]:
        return WriteFileArgs


# ═══════════════════════════════════════════════════════════════
# File List Tool
# ═══════════════════════════════════════════════════════════════


class ListFilesArgs(BaseModel):
    directory: str = Field(".", description="Directory path to list")
    recursive: bool = Field(
        False, description="Whether to list subdirectories recursively"
    )
    limit: int = Field(100, description="Maximum number of files to return")


class ListFilesTool(BaseTool):
    """List files in a directory"""

    def __init__(self):
        super().__init__(
            name="list_files",
            description="List all files and subdirectories in the specified directory.",
        )

    def _run(
        self, directory: str = ".", recursive: bool = False, limit: int = 100
    ) -> str:
        path = Path(directory)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        items = []

        # Define ignore patterns
        ignore_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".idea",
            ".vscode",
        }

        def scan(p: Path, depth: int = 0):
            if len(items) >= limit:
                return

            try:
                # Sort: directories first, then files
                entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))

                for entry in entries:
                    if len(items) >= limit:
                        break

                    if entry.is_dir():
                        if entry.name in ignore_dirs:
                            continue
                        items.append(f"{'  ' * depth}📁 {entry.name}/")
                        if recursive:
                            scan(entry, depth + 1)
                    else:
                        items.append(f"{'  ' * depth}📄 {entry.name}")
            except PermissionError:
                items.append(f"{'  ' * depth}🚫 {p.name} (Permission Denied)")

        scan(path)

        output = [f"Directory: {path.absolute()}"]
        output.extend(items)

        if len(items) >= limit:
            output.append(f"\n... (Truncated, showing first {limit} items)")

        return "\n".join(output)

    def get_args_schema(self) -> Type[BaseModel]:
        return ListFilesArgs
