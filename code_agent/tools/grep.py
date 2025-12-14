"""
Grep Tool - Fast Code Search with ripgrep
Design Philosophy:
  - Use ripgrep for blazing fast search
  - Fallback to Python's grep if ripgrep not available
  - Return structured results with context
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from code_agent.utils.logger import logger
from code_agent.utils.path import resolve_workspace_path

from .base import BaseTool


class GrepInput(BaseModel):
    """Input schema for grep search"""

    pattern: str = Field(description="Regex pattern to search for (use Rust regex syntax for ripgrep)")
    path: str = Field(
        default=".",
        description="Directory or file to search in (default: current directory)",
    )
    case_sensitive: bool = Field(default=False, description="Whether search should be case-sensitive")
    file_pattern: str | None = Field(
        default=None,
        description="Glob pattern to filter files (e.g., '*.py', '*.js')",
    )
    max_results: int = Field(default=50, description="Maximum number of results to return")


class GrepTool(BaseTool):
    """
    Fast code search using ripgrep

    Features:
      - Blazing fast search with ripgrep
      - Regex pattern matching
      - File type filtering
      - Context lines around matches
      - Fallback to Python grep if ripgrep not available

    Examples:
      - Search for function definitions: pattern="def \\w+\\("
      - Search in Python files only: pattern="import", file_pattern="*.py"
      - Case-sensitive search: pattern="TODO", case_sensitive=True
    """

    def __init__(self):
        super().__init__(
            name="grep_search",
            description="""Search for text patterns in files using regex.

Use this tool to:
- Find function/class definitions
- Search for TODO/FIXME comments
- Locate specific code patterns
- Find imports or dependencies

Examples:
- Find all TODO comments: pattern="TODO"
- Find function definitions: pattern="def \\w+\\("
- Search in JS files only: pattern="useState", file_pattern="*.js"
""",
            timeout=30,
        )

    def get_args_schema(self) -> type[BaseModel]:
        """Return input schema"""
        return GrepInput

    def _run(self, **kwargs) -> str:
        """Execute grep search"""
        pattern = kwargs["pattern"]
        path_input = kwargs.get("path", ".")
        case_sensitive = kwargs.get("case_sensitive", False)
        file_pattern = kwargs.get("file_pattern")
        max_results = kwargs.get("max_results", 50)

        # Resolve path to absolute workspace path
        try:
            resolved_path = resolve_workspace_path(path_input)
        except ValueError as e:
            return f"Path error: {e}"

        # Verify path exists
        if not resolved_path.exists():
            return f"Path not found: {path_input}"

        # Check if ripgrep is available
        has_ripgrep = shutil.which("rg") is not None

        if has_ripgrep:
            return self._ripgrep_search(pattern, resolved_path, case_sensitive, file_pattern, max_results)
        logger.warning("ripgrep not found, using Python fallback (slower)")
        return self._python_grep(pattern, resolved_path, case_sensitive, file_pattern, max_results)

    def _ripgrep_search(
        self,
        pattern: str,
        path: Path,
        case_sensitive: bool,
        file_pattern: str | None,
        max_results: int,
    ) -> str:
        """Search using ripgrep (fast)"""
        cmd = ["rg", "--line-number", "--with-filename", "--context", "2"]

        # Case sensitivity
        if not case_sensitive:
            cmd.append("--ignore-case")

        # File pattern
        if file_pattern:
            cmd.extend(["--glob", file_pattern])

        # Max results
        cmd.extend(["--max-count", str(max_results)])

        # Pattern and path (use absolute path)
        cmd.extend([pattern, str(path)])

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd(),
                encoding="utf-8",
                errors="replace",  # Replace invalid characters instead of failing
            )

            if result.returncode == 0:
                output = result.stdout
                if output:
                    output = output.strip()
                if not output:
                    return f"No matches found for pattern: {pattern}"

                # Count matches
                match_count = len([line for line in output.split("\n") if "--" not in line and line.strip()])

                return f"Found {match_count} matches:\n\n{output}"

            if result.returncode == 1:
                # No matches found
                return f"No matches found for pattern: {pattern}"
            # Error occurred
            error = result.stderr
            if error:
                error = error.strip()
            return f"Search failed: {error if error else 'Unknown error'}"

        except subprocess.TimeoutExpired:
            return "Search timed out (30s limit). Try narrowing your search."
        except Exception as e:
            logger.error(f"ripgrep search failed: {e}")
            return f"Search failed: {e!s}"

    def _python_grep(
        self,
        pattern: str,
        path: Path,
        case_sensitive: bool,
        file_pattern: str | None,
        max_results: int,
    ) -> str:
        """Fallback Python implementation (slower)"""
        try:
            # Compile regex
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            # Get files to search (path is already a Path object)
            search_path = path
            if search_path.is_file():
                files = [search_path]
            else:
                # Get all files recursively
                if file_pattern:
                    files = list(search_path.rglob(file_pattern))
                else:
                    files = [f for f in search_path.rglob("*") if f.is_file() and not self._should_ignore(f)]

            results = []
            match_count = 0

            for file_path in files:
                if match_count >= max_results:
                    break

                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if match_count >= max_results:
                            break

                        if regex.search(line):
                            match_count += 1
                            # Add context (2 lines before and after)
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = "".join(lines[start:end])

                            results.append(f"{file_path}:{i + 1}:\n{context}\n")

                except Exception as e:
                    logger.debug(f"Skipping {file_path}: {e}")
                    continue

            if not results:
                return f"No matches found for pattern: {pattern}"

            output = "\n".join(results)
            return f"Found {match_count} matches:\n\n{output}"

        except re.error as e:
            return f"Invalid regex pattern: {e}"
        except Exception as e:
            logger.error(f"Python grep failed: {e}")
            return f"Search failed: {e!s}"

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        ignore_patterns = [
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".egg-info",
        ]

        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)
