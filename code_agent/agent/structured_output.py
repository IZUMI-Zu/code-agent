"""
Structured Output Models
"""

from typing import ClassVar, Literal

from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    """
    Reviewer Agent
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
