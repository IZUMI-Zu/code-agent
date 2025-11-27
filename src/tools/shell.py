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
  - Real-time output streaming (Claude Code style)
  - Smart error messages with platform-specific command suggestions
"""

import platform
import re
import subprocess
import threading
import time
from typing import Type

from pydantic import BaseModel, Field

from ..utils.event_bus import publish_tool_event
from ..utils.path import resolve_workspace_path
from .base import BaseTool

# ═══════════════════════════════════════════════════════════════
# Platform Command Mapping (Linux -> Windows)
# ═══════════════════════════════════════════════════════════════
LINUX_TO_WINDOWS_COMMANDS = {
    "ls": "dir",
    "ls -la": "dir",
    "ls -l": "dir",
    "ls -a": "dir /a",
    "cat": "type",
    "rm": "del",
    "rm -rf": "rmdir /s /q",
    "rm -r": "rmdir /s /q",
    "cp": "copy",
    "cp -r": "xcopy /s /e",
    "mv": "move",
    "mkdir -p": "mkdir",
    "touch": "type nul >",
    "pwd": "cd",
    "clear": "cls",
    "grep": "findstr",
    "head": "more",
    "tail": "more",
    "wc -l": "find /c /v \"\"",
    "echo -e": "echo",
}

# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def suggest_windows_command(failed_command: str, error_msg: str) -> str:
    """
    Analyze a failed command and suggest Windows equivalent.
    Returns suggestion string or empty string if no suggestion.
    """
    if platform.system() != "Windows":
        return ""
    
    # Check if error indicates command not found
    not_found_patterns = [
        "不是内部或外部命令",  # Chinese: not internal or external command
        "is not recognized",
        "command not found",
        "not found",
    ]
    
    is_command_not_found = any(p in error_msg.lower() or p in error_msg for p in not_found_patterns)
    if not is_command_not_found:
        return ""
    
    # Extract the base command (first word)
    parts = failed_command.strip().split()
    if not parts:
        return ""
    
    base_cmd = parts[0]
    
    # Check for direct mapping
    if base_cmd in LINUX_TO_WINDOWS_COMMANDS:
        win_cmd = LINUX_TO_WINDOWS_COMMANDS[base_cmd]
        # Try to construct full Windows command
        if len(parts) > 1:
            args = " ".join(parts[1:])
            suggested = f"{win_cmd} {args}"
        else:
            suggested = win_cmd
        return f"\n\n💡 RETRY SUGGESTION: This appears to be a Linux command. On Windows, try:\n   {suggested}"
    
    # Check for compound commands like "ls -la"
    for linux_cmd, win_cmd in LINUX_TO_WINDOWS_COMMANDS.items():
        if failed_command.strip().startswith(linux_cmd):
            rest = failed_command.strip()[len(linux_cmd):].strip()
            suggested = f"{win_cmd} {rest}".strip()
            return f"\n\n💡 RETRY SUGGESTION: This appears to be a Linux command. On Windows, try:\n   {suggested}"
    
    return ""


# ═══════════════════════════════════════════════════════════════
# Shell Execution Tool
# ═══════════════════════════════════════════════════════════════


class ShellArgs(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    cwd: str = Field(".", description="Working directory for execution")
    auto_yes: bool = Field(
        False,
        description="Auto-answer 'yes' to interactive prompts (e.g., npm install confirmations)",
    )
    timeout: int = Field(
        None,
        description="Custom timeout in seconds (default: 60). Use higher values for long-running commands like npm install, npx create-*, cargo build, etc.",
    )


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

TIPS:
- Use auto_yes=true for commands that may prompt for confirmation (e.g., npx, npm install)
- Or use flags like --yes, -y, --force where available
- Use timeout=300 (5 min) or higher for long-running commands like:
  * npx create-react-app, create-next-app (use timeout=300)
  * npm install with many dependencies (use timeout=180)
  * cargo build, go build (use timeout=300)

Returns stdout, stderr, and exit code.""",
            timeout=timeout,
            max_retries=0,  # Shell commands shouldn't be retried automatically
        )
        # Use same timeout for subprocess (first line of defense)
        self.subprocess_timeout = timeout

    def _run(
        self, command: str, cwd: str = ".", auto_yes: bool = False, timeout: int = None
    ) -> str:
        # Validate working directory
        try:
            work_dir = resolve_workspace_path(cwd)
        except ValueError as exc:
            raise ValueError(str(exc))

        if not work_dir.exists():
            raise FileNotFoundError(f"Working directory not found: {cwd}")

        # Use custom timeout if provided, otherwise use default
        effective_timeout = timeout if timeout is not None else self.subprocess_timeout

        # Execute command with real-time output streaming
        return self._run_with_streaming(command, work_dir, auto_yes, effective_timeout)

    def _run_with_streaming(
        self, command: str, work_dir, auto_yes: bool = False, timeout: int = 60
    ) -> str:
        """
        Execute command with real-time output streaming (Claude Code style)
        
        Design Philosophy:
          - User sees output as it happens, not after completion
          - Both stdout and stderr are streamed in real-time
          - Full output is still captured for return value
          - auto_yes: pipe 'y' to stdin for interactive prompts
        """
        stdout_lines = []
        stderr_lines = []
        
        # Publish shell start event
        publish_tool_event({
            "event_type": "shell_started",
            "command": command,
            "cwd": str(work_dir),
            "auto_yes": auto_yes,
            "timeout": timeout,
        })

        try:
            # Use Popen for real-time output
            # If auto_yes, we'll pipe stdin to auto-answer prompts
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(work_dir),
                stdin=subprocess.PIPE if auto_yes else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
            
            # If auto_yes, send 'y' and close stdin
            if auto_yes and process.stdin:
                try:
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    process.stdin.close()
                except Exception:
                    pass  # stdin might already be closed

            # Read stdout and stderr in separate threads
            def read_stream(stream, lines_list, stream_type):
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            line_stripped = line.rstrip("\n\r")
                            lines_list.append(line_stripped)
                            # Publish each line as it comes
                            publish_tool_event({
                                "event_type": "shell_output",
                                "stream": stream_type,
                                "line": line_stripped,
                            })
                finally:
                    stream.close()

            stdout_thread = threading.Thread(
                target=read_stream, args=(process.stdout, stdout_lines, "stdout")
            )
            stderr_thread = threading.Thread(
                target=read_stream, args=(process.stderr, stderr_lines, "stderr")
            )

            stdout_thread.start()
            stderr_thread.start()

            # Wait for process with timeout
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout_thread.join(timeout=1)
                stderr_thread.join(timeout=1)
                publish_tool_event({
                    "event_type": "shell_finished",
                    "command": command,
                    "status": "timeout",
                })
                raise RuntimeError(
                    f"Command timed out ({timeout}s): {command}"
                )

            # Wait for threads to finish reading
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)

            # Publish shell finished event
            publish_tool_event({
                "event_type": "shell_finished",
                "command": command,
                "return_code": return_code,
                "status": "completed" if return_code == 0 else "failed",
            })

        except Exception as e:
            if "timed out" not in str(e):
                publish_tool_event({
                    "event_type": "shell_finished",
                    "command": command,
                    "status": "error",
                    "error": str(e),
                })
            raise RuntimeError(f"Command execution error: {str(e)}")

        # Construct output (return full info for both success and failure)
        output_lines = [
            f"Command: {command}",
            f"Working Dir: {work_dir}",
            f"Return Code: {return_code}",
            "",
        ]

        stdout_text = "\n".join(stdout_lines)
        stderr_text = "\n".join(stderr_lines)

        if stdout_text:
            output_lines.extend(["─── STDOUT ───", stdout_text])

        if stderr_text:
            output_lines.extend(["─── STDERR ───", stderr_text])

        # Raise exception on failure (let base class catch it)
        if return_code != 0:
            error_msg = stderr_text if stderr_text else stdout_text
            # Add Windows command suggestion if applicable
            suggestion = suggest_windows_command(command, error_msg)
            raise RuntimeError(
                f"Command failed (Code {return_code}):\n{error_msg}{suggestion}"
            )

        return "\n".join(output_lines)

    def get_args_schema(self) -> Type[BaseModel]:
        return ShellArgs
