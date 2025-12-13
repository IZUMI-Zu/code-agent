import difflib
import pathlib

from pydantic import BaseModel, Field

from code_agent.utils.logger import logger
from code_agent.utils.path import get_relative_path, resolve_workspace_path

from .base import BaseTool


class StrReplaceArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to edit")
    old_str: str = Field(
        ...,
        description="The exact string to find and replace. Must match exactly (including whitespace and indentation).",
    )
    new_str: str = Field(
        ...,
        description="The new string to replace with. Can be empty to delete the old_str.",
    )


class StrReplaceTool(BaseTool):
    """
    Replace exact string match in a file.

    This is the RECOMMENDED way to edit files because:
    1. Precise: Only changes what you specify
    2. Safe: Fails if match is ambiguous (multiple matches)
    3. Efficient: Only sends the changed parts

    CRITICAL RULES:
    1. old_str must match EXACTLY (including whitespace, indentation)
    2. old_str must be unique in the file (only one match allowed)
    3. Include enough context to make the match unique

    Example:
        old_str: "def hello():\n    print('hi')"
        new_str: "def hello():\n    print('hello world')"
    """

    def __init__(self):
        super().__init__(
            name="str_replace",
            description=(
                "Replace an exact string in a file. "
                "The old_str must match exactly ONE location in the file. "
                "Include enough context (2-3 lines) to make the match unique. "
                "This is safer and more efficient than rewriting the entire file."
            ),
        )

    def _run(self, file_path: str, old_str: str, new_str: str) -> str:
        # Resolve path
        try:
            path = resolve_workspace_path(file_path)
        except ValueError as e:
            return f"Error: {e}"

        # Validate file exists
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        # Validate old_str is not empty
        if not old_str:
            return "Error: old_str cannot be empty"

        # Count occurrences
        count = content.count(old_str)

        if count == 0:
            # Try to find similar matches for helpful error
            similar = self._find_similar(content, old_str)
            if similar:
                return f"Error: old_str not found in {file_path}.\nDid you mean one of these?\n{similar}"
            return (
                f"Error: old_str not found in {file_path}.\n"
                f"Make sure the string matches exactly, including whitespace and indentation."
            )

        if count > 1:
            # Find line numbers of all matches
            match_lines = []
            search_pos = 0
            for _ in range(count):
                pos = content.find(old_str, search_pos)
                line_num = content[:pos].count("\n") + 1
                match_lines.append(line_num)
                search_pos = pos + 1

            return (
                f"Error: old_str found {count} times in {file_path} (lines: {match_lines}).\n"
                f"Include more context to make the match unique."
            )

        # Perform replacement
        new_content = content.replace(old_str, new_str, 1)

        # Write back
        path.write_text(new_content, encoding="utf-8")

        # Calculate stats
        old_lines = old_str.count("\n") + 1
        new_lines = new_str.count("\n") + 1
        line_diff = new_lines - old_lines

        # Find the line number where replacement occurred
        pos = content.find(old_str)
        line_num = content[:pos].count("\n") + 1

        logger.info(f"str_replace: {file_path} line {line_num}, {old_lines} lines -> {new_lines} lines")

        return (
            f"Successfully replaced in {get_relative_path(path)} at line {line_num}.\n"
            f"Changed {old_lines} lines to {new_lines} lines ({line_diff:+d})."
        )

    def _find_similar(self, content: str, target: str, max_results: int = 3) -> str:
        """Find similar strings in content for helpful error messages"""
        # Split target into lines and find similar lines
        target_lines = target.strip().split("\n")
        if not target_lines:
            return ""

        first_line = target_lines[0].strip()
        if len(first_line) < 5:
            return ""

        # Search for lines containing similar content
        content_lines = content.split("\n")
        similar = []

        for i, line in enumerate(content_lines):
            # Use fuzzy matching
            ratio = difflib.SequenceMatcher(None, first_line, line.strip()).ratio()
            if ratio > 0.6:
                # Show context (line before and after)
                start = max(0, i - 1)
                end = min(len(content_lines), i + 2)
                context = "\n".join(f"  {j + 1}: {content_lines[j]}" for j in range(start, end))
                similar.append(f"Near line {i + 1}:\n{context}")

            if len(similar) >= max_results:
                break

        return "\n\n".join(similar)

    def get_args_schema(self) -> type[BaseModel]:
        return StrReplaceArgs


# ═══════════════════════════════════════════════════════════════
# Insert Lines Tool
# ═══════════════════════════════════════════════════════════════


class InsertLinesArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to edit")
    line_number: int = Field(
        ...,
        description="Line number to insert BEFORE (1-based). Use 0 to insert at the beginning.",
    )
    content: str = Field(..., description="Content to insert")


class InsertLinesTool(BaseTool):
    """
    Insert content at a specific line number.

    Use this when you need to ADD new content without replacing existing content.

    Example:
        line_number: 10
        content: "# New comment\ndef new_function():\n    pass"

        This inserts the content BEFORE line 10.
    """

    def __init__(self):
        super().__init__(
            name="insert_lines",
            description=(
                "Insert content at a specific line number. "
                "Content is inserted BEFORE the specified line. "
                "Use line_number=0 to insert at the beginning of the file."
            ),
        )

    def _run(self, file_path: str, line_number: int, content: str) -> str:
        # Resolve path
        try:
            path = resolve_workspace_path(file_path)
        except ValueError as e:
            return f"Error: {e}"

        # Validate file exists
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content
        try:
            file_content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            file_content = path.read_text(encoding="latin-1")

        lines = file_content.split("\n")
        total_lines = len(lines)

        # Validate line number
        if line_number < 0:
            return f"Error: line_number must be >= 0 (got {line_number})"

        if line_number > total_lines + 1:
            return f"Error: line_number {line_number} is beyond file end (file has {total_lines} lines)"

        # Insert content
        new_lines = content.split("\n")
        insert_idx = line_number if line_number > 0 else 0

        # Handle insertion
        if line_number == 0:
            # Insert at beginning
            result_lines = new_lines + lines
        elif line_number > total_lines:
            # Append at end
            result_lines = lines + new_lines
        else:
            # Insert before specified line
            result_lines = lines[: insert_idx - 1] + new_lines + lines[insert_idx - 1 :]

        # Write back
        new_content = "\n".join(result_lines)
        path.write_text(new_content, encoding="utf-8")

        logger.info(f"insert_lines: {file_path} at line {line_number}, inserted {len(new_lines)} lines")

        return f"Successfully inserted {len(new_lines)} lines at line {line_number} in {get_relative_path(path)}."

    def get_args_schema(self) -> type[BaseModel]:
        return InsertLinesArgs


# ═══════════════════════════════════════════════════════════════
# Delete Lines Tool
# ═══════════════════════════════════════════════════════════════


class DeleteLinesArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to edit")
    start_line: int = Field(..., description="First line to delete (1-based, inclusive)")
    end_line: int = Field(..., description="Last line to delete (1-based, inclusive)")


class DeleteLinesTool(BaseTool):
    """
    Delete a range of lines from a file.

    Use this when you need to REMOVE content without replacing it.

    Example:
        start_line: 10
        end_line: 15

        This deletes lines 10 through 15 (inclusive).
    """

    def __init__(self):
        super().__init__(
            name="delete_lines",
            description=("Delete a range of lines from a file. Both start_line and end_line are inclusive (1-based)."),
        )

    def _run(self, file_path: str, start_line: int, end_line: int) -> str:
        # Resolve path
        try:
            path = resolve_workspace_path(file_path)
        except ValueError as e:
            return f"Error: {e}"

        # Validate file exists
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content
        try:
            file_content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            file_content = path.read_text(encoding="latin-1")

        lines = file_content.split("\n")
        total_lines = len(lines)

        # Validate line numbers
        if start_line < 1:
            return f"Error: start_line must be >= 1 (got {start_line})"

        if end_line < start_line:
            return f"Error: end_line ({end_line}) must be >= start_line ({start_line})"

        if start_line > total_lines:
            return f"Error: start_line {start_line} is beyond file end (file has {total_lines} lines)"

        # Clamp end_line to file length
        end_line = min(end_line, total_lines)

        # Delete lines
        deleted_lines = lines[start_line - 1 : end_line]
        result_lines = lines[: start_line - 1] + lines[end_line:]

        # Write back
        new_content = "\n".join(result_lines)
        path.write_text(new_content, encoding="utf-8")

        deleted_count = len(deleted_lines)
        logger.info(f"delete_lines: {file_path} lines {start_line}-{end_line}, deleted {deleted_count} lines")

        return f"Successfully deleted {deleted_count} lines ({start_line}-{end_line}) from {get_relative_path(path)}."

    def get_args_schema(self) -> type[BaseModel]:
        return DeleteLinesArgs


# ═══════════════════════════════════════════════════════════════
# Append to File Tool
# ═══════════════════════════════════════════════════════════════


class AppendFileArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to append to")
    content: str = Field(..., description="Content to append at the end of the file")


class AppendFileTool(BaseTool):
    """
    Append content to the end of a file.

    Use this when you need to ADD content at the end without reading the whole file.
    Automatically adds a newline before the content if the file doesn't end with one.
    """

    def __init__(self):
        super().__init__(
            name="append_file",
            description=("Append content to the end of a file. Automatically handles newline formatting."),
        )

    def _run(self, file_path: str, content: str) -> str:
        # Resolve path
        try:
            path = resolve_workspace_path(file_path)
        except ValueError as e:
            return f"Error: {e}"

        # Validate file exists
        if not path.exists():
            return f"Error: File not found: {file_path}. Use write_file to create new files."

        if not path.is_file():
            return f"Error: Path is not a file: {file_path}"

        # Read current content to check ending
        try:
            current = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            current = path.read_text(encoding="latin-1")

        # Add newline if needed
        if current and not current.endswith("\n"):
            content = "\n" + content

        # Append content
        with pathlib.Path(path).open("a", encoding="utf-8") as f:
            f.write(content)

        lines_added = content.count("\n") + (0 if content.endswith("\n") else 1)
        logger.info(f"append_file: {file_path}, appended {lines_added} lines")

        return f"Successfully appended {len(content)} chars ({lines_added} lines) to {get_relative_path(path)}."

    def get_args_schema(self) -> type[BaseModel]:
        return AppendFileArgs
