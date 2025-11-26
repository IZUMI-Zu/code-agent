"""
═══════════════════════════════════════════════════════════════
Shell Command Execution Tool
═══════════════════════════════════════════════════════════════
Security Design:
  - Timeout limits (prevent zombie processes)
  - Capture stderr (provide full diagnostic info)
  - Explicit working directory (avoid path confusion)

Design Philosophy:
  - Shell is for ADVANCED operations (git, npm, compilers, etc.)
  - For basic filesystem ops, use dedicated cross-platform tools
  - Keep raw power available, but warn about alternatives
"""

import platform
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
    """
    Execute Shell Command (Advanced)

    Good Taste:
      - Provides raw shell access for power users
      - But description guides users to better alternatives
      - Platform info helps Agent make informed choices

    Configuration:
      - timeout: 60 seconds (commands should complete quickly)
      - max_retries: 0 (shell timeouts are usually not retryable)
      - subprocess_timeout: Same as tool timeout (subprocess-level enforcement)
    """

    def __init__(self, timeout: int = 60):
        # Detect platform
        system = platform.system()
        shell_type = "cmd.exe" if system == "Windows" else "bash/zsh"

        super().__init__(
            name="shell",
            description=f"""Execute shell command (Current shell: {shell_type} on {system}).

IMPORTANT: For basic filesystem operations, prefer these cross-platform tools:
- create_directory: Create directories (instead of mkdir)
- copy_file: Copy files (instead of cp/copy)
- move_file: Move/rename (instead of mv/move)
- delete_path: Delete files/dirs (instead of rm/del)

Use shell ONLY for:
- Version control (git commands)
- Package managers (npm, pip, cargo)
- Build tools (make, gcc, cargo build)
- Process management (ps, kill)
- System queries (which, env)

Returns stdout, stderr, and exit code.""",
            timeout=timeout,
            max_retries=0,  # Shell commands shouldn't be retried automatically
        )
        # Use same timeout for subprocess (first line of defense)
        self.subprocess_timeout = timeout

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
                timeout=self.subprocess_timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Command timed out ({self.subprocess_timeout}s): {command}"
            )
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
