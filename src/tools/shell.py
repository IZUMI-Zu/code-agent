"""
═══════════════════════════════════════════════════════════════
Shell Command Execution Tool
═══════════════════════════════════════════════════════════════
Security Design:
  - Timeout limits (prevent zombie processes)
  - Capture stderr (provide full diagnostic info)
  - Explicit working directory (avoid path confusion)
"""

import subprocess
from pathlib import Path
from typing import Type

from pydantic import BaseModel, Field

from .base import BaseTool

# ═══════════════════════════════════════════════════════════════
# Shell Execution Tool
# ═══════════════════════════════════════════════════════════════


class ShellArgs(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    cwd: str = Field(".", description="Working directory for execution")


class ShellTool(BaseTool):
    """Execute Shell Command"""

    def __init__(self, timeout: int = 60):
        super().__init__(
            name="shell",
            description="Execute command in system shell. Returns stdout and stderr.",
        )
        self.timeout = timeout

    def _run(self, command: str, cwd: str = ".") -> str:
        # Validate working directory
        work_dir = Path(cwd).resolve()
        if not work_dir.exists():
            raise FileNotFoundError(f"Working directory not found: {cwd}")

        # Execute command (unified timeout and error handling)
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out ({self.timeout}s): {command}")
        except Exception as e:
            raise RuntimeError(f"Command execution error: {str(e)}")

        # Construct output (return full info for both success and failure)
        output_lines = [
            f"Command: {command}",
            f"Working Dir: {work_dir}",
            f"Return Code: {result.returncode}",
            "",
        ]

        if result.stdout:
            output_lines.extend(["─── STDOUT ───", result.stdout.strip()])

        if result.stderr:
            output_lines.extend(["─── STDERR ───", result.stderr.strip()])

        # Raise exception on failure (let base class catch it)
        if result.returncode != 0:
            # If stderr exists, prioritize it
            error_msg = (
                result.stderr.strip() if result.stderr else result.stdout.strip()
            )
            raise RuntimeError(
                f"Command failed (Code {result.returncode}):\n{error_msg}"
            )

        return "\n".join(output_lines)

    def get_args_schema(self) -> Type[BaseModel]:
        return ShellArgs
