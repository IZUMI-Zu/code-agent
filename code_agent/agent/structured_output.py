"""
Structured Output Models
强制 Agent 输出结构化数据, 避免脆弱的字符串解析

Architecture: Based on Claude Code's best practices
- Use Pydantic models for type safety
- Let LLM output JSON, validate with schemas
- Eliminate regex-based parsing (brittle and error-prone)

Benefits:
- 100% reliable state extraction
- Auto-validation of output format
- Type-safe data flow
"""

from typing import ClassVar, Literal

from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    """
    Reviewer Agent 的结构化输出
    """

    status: Literal["passed", "needs_fixes"]
    summary: str = Field(
        description="1-2 sentence summary of the review",
        min_length=10,
        max_length=500,
    )
    files_checked: list[str] = Field(
        description="List of files that were verified",
        default_factory=list,
    )
    issues: list[str] = Field(
        description="List of issues found (only if status='needs_fixes'). "
        "Format: 'file_path:line_number - description'",
        default_factory=list,
    )

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "examples": [
                {
                    "status": "passed",
                    "summary": "All files have valid syntax and dependencies are correctly declared.",
                    "files_checked": ["src/main.py", "requirements.txt"],
                    "issues": [],
                },
                {
                    "status": "needs_fixes",
                    "summary": "Found syntax error and missing dependency.",
                    "files_checked": ["src/main.py", "requirements.txt"],
                    "issues": [
                        "src/main.py:15 - Missing colon after if statement",
                        "requirements.txt - Missing 'pydantic' dependency",
                    ],
                },
            ]
        }


class CodeReference(BaseModel):
    """
    标准化的代码引用格式

    Claude Code convention: `file_path:line_number`
    Example: `src/agent/graph.py:142`
    """

    file_path: str = Field(description="Relative path from workspace root")
    line_number: int | None = Field(
        default=None,
        description="Line number (optional)",
    )

    def __str__(self) -> str:
        """Format as `file_path:line_number`"""
        if self.line_number:
            return f"`{self.file_path}:{self.line_number}`"
        return f"`{self.file_path}`"

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "examples": [
                {"file_path": "src/agent/graph.py", "line_number": 142},
                {"file_path": "README.md", "line_number": None},
            ]
        }


class TaskProgress(BaseModel):
    """
    任务进度报告(供 Coder 使用)

    Optional: Coder can report progress for long-running implementations
    """

    task_id: int = Field(description="Task ID from the plan")
    status: Literal["in_progress", "completed", "blocked"]
    progress_summary: str = Field(
        description="What was done",
        max_length=200,
    )
    files_modified: list[str] = Field(
        description="Files created/modified",
        default_factory=list,
    )
    blocker_reason: str | None = Field(
        default=None,
        description="Why task is blocked (if status='blocked')",
    )

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "examples": [
                {
                    "task_id": 2,
                    "status": "completed",
                    "progress_summary": "Created Navigation component with domain filtering logic",
                    "files_modified": ["src/components/Navigation.js"],
                    "blocker_reason": None,
                },
                {
                    "task_id": 3,
                    "status": "blocked",
                    "progress_summary": "Cannot implement API client - missing API key in requirements",
                    "files_modified": [],
                    "blocker_reason": "Need Brave API key for web search functionality",
                },
            ]
        }
