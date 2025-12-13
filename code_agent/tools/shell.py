import atexit
import collections
import os
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Literal

import psutil
from pydantic import BaseModel, Field

from code_agent.config import settings  # Import settings for workspace_root
from code_agent.utils.event_bus import publish_tool_event
from code_agent.utils.logger import logger
from code_agent.utils.path import get_relative_path, resolve_workspace_path

from .base import BaseTool

# ═══════════════════════════════════════════════════════════════
# Global Process Registry
# ═══════════════════════════════════════════════════════════════


class ProcessInfo(BaseModel):
    pid: int
    command: str
    log_file: str
    start_time: float
    status: str = "running"


class ProcessRegistry:
    """
    Tracks processes started by the agent to ensure they can be managed and cleaned up.
    """

    def __init__(self):
        self._processes: dict[int, ProcessInfo] = {}
        # Register cleanup on exit
        atexit.register(self.cleanup_all)

    def register(self, pid: int, command: str, log_file: str):
        """Register a new background process"""
        self._processes[pid] = ProcessInfo(
            pid=pid,
            command=command,
            log_file=str(log_file),
            start_time=time.time(),
        )
        logger.info(f"Registered process PID {pid}: {command}")

    def get_active_processes(self) -> list[ProcessInfo]:
        """Get list of processes that are actually running"""
        active = []
        dead_pids = []

        for pid, info in self._processes.items():
            if psutil.pid_exists(pid):
                try:
                    p = psutil.Process(pid)
                    if p.status() != psutil.STATUS_ZOMBIE:
                        info.status = p.status()
                        active.append(info)
                    else:
                        dead_pids.append(pid)
                except psutil.NoSuchProcess:
                    dead_pids.append(pid)
            else:
                dead_pids.append(pid)

        # Cleanup registry
        for pid in dead_pids:
            self._processes.pop(pid, None)

        return active

    def get_process_info(self, pid: int) -> ProcessInfo | None:
        """Retrieve ProcessInfo for a given PID."""
        return self._processes.get(pid)

    def kill_process(self, pid: int) -> bool:
        """Kill a registered process"""
        if pid not in self._processes and not psutil.pid_exists(pid):
            return False

        try:
            parent = psutil.Process(pid)
            # Kill children first (recursive)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()

            self._processes.pop(pid, None)
            return True
        except psutil.NoSuchProcess:
            self._processes.pop(pid, None)
            return False
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return False

    def cleanup_all(self):
        """Kill all registered processes (for shutdown)"""
        if not self._processes:
            return

        logger.info(f"Cleaning up {len(self._processes)} background processes...")
        # Create a copy of keys since we modify the dict in kill_process
        pids = list(self._processes.keys())
        for pid in pids:
            self.kill_process(pid)


# Global Instance
_process_registry = ProcessRegistry()


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
        60,
        description="Custom timeout in seconds (default: 60). Use higher values for long-running commands. Ignored for background tasks.",
    )
    background: bool = Field(
        False,
        description="Run command in background (detached). Use for servers/watchers. Output logs to file.",
    )


class ShellTool(BaseTool):
    """
    Execute Shell Command (Advanced)

    Capabilities:
    - Blocking execution with real-time output streaming
    - Background execution with process tracking and logging
    - Auto-cleanup of background processes on exit
    """

    def __init__(self, timeout: int = 60):
        # Detect platform
        system = platform.system()
        shell_type = "cmd.exe" if system == "Windows" else "bash/zsh"

        super().__init__(
            name="shell",
            description=f"""Execute shell command (Current shell: {shell_type} on {system}).

Use for:
- Git, NPM, Pip, Cargo, Build tools, System queries

Background Execution:
- Set `background=True` for long-running tasks (servers, watchers)
- Returns PID and Log Path immediately
- Processes are auto-tracked and can be managed via `process_manager` tool
- Logs are automatically stored in `logs/processes/` within the workspace.

Timeout:
- Applies to BLOCKING commands only
- Background commands run indefinitely until killed
""",
            timeout=timeout,
            max_retries=0,
        )
        self.subprocess_timeout = timeout

    def _run(
        self,
        command: str,
        cwd: str = ".",
        auto_yes: bool = False,
        timeout: int = 60,
        background: bool = False,
    ) -> str:
        try:
            work_dir = resolve_workspace_path(cwd)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        if not work_dir.exists():
            raise FileNotFoundError(f"Working directory not found: {cwd}")

        effective_timeout = timeout if timeout is not None else self.subprocess_timeout

        if background:
            return self._run_background(command, work_dir, auto_yes)

        return self._run_with_streaming(command, work_dir, auto_yes, effective_timeout)

    def _run_background(
        self,
        command: str,
        work_dir,
        auto_yes: bool = False,
    ) -> str:
        # Determine log file path (default to logs/processes/)
        log_dir = settings.workspace_root / "logs" / "processes"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        safe_cmd = re.sub(r"[^a-zA-Z0-9]", "_", command[:20])
        log_path = log_dir / f"proc_{timestamp}_{safe_cmd}.log"

        publish_tool_event(
            {
                "event_type": "shell_started",
                "command": command,
                "cwd": str(work_dir),
                "mode": "background",
            }
        )

        try:
            full_command = f'{command} > "{log_path}" 2>&1'

            process = psutil.Popen(
                full_command,
                shell=True,
                cwd=str(work_dir),
                stdin=subprocess.PIPE if auto_yes else None,
                text=True,
            )

            if auto_yes and process.stdin:
                try:
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    process.stdin.close()
                except Exception:
                    pass

            # Validation wait (2s)
            try:
                return_code = process.wait(timeout=2.0)

                # Failed immediately
                if return_code != 0:
                    error_output = ""
                    if log_path.exists():
                        with open(log_path, encoding="utf-8", errors="replace") as lf:
                            error_output = lf.read()
                    else:
                        error_output = "(Log file not created)"

                    raise RuntimeError(f"Background command failed immediately (Code {return_code}):\n{error_output}")
                # Finished successfully immediately (rare for 'background', but possible)
                output = ""
                if log_path.exists():
                    with open(log_path, encoding="utf-8", errors="replace") as lf:
                        output = lf.read()

                # Remove log file if process finished immediately without errors and no output
                if not output and log_path.exists():
                    os.remove(log_path)
                    return "Command finished immediately (Code 0). No output, log file removed."

                return f"Command finished immediately (Code 0). Output saved to: {get_relative_path(log_path)}"

            except psutil.TimeoutExpired:
                # Successfully running in background

                # REGISTER PROCESS
                _process_registry.register(process.pid, command, str(log_path))

                return (
                    f"Command started in background.\n"
                    f"PID: {process.pid}\n"
                    f"Manage: Use 'process_manager' tool (action='list', action='kill', action='logs' for PID {process.pid}) for control."
                )

        except Exception as e:
            raise RuntimeError(f"Failed to start background command: {e}") from e

    def _run_with_streaming(
        self,
        command: str,
        work_dir,
        auto_yes: bool = False,
        timeout: int = 60,
    ) -> str:
        stdout_lines = []
        stderr_lines = []

        publish_tool_event(
            {
                "event_type": "shell_started",
                "command": command,
                "cwd": str(work_dir),
                "auto_yes": auto_yes,
                "timeout": timeout,
            }
        )

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(work_dir),
                stdin=subprocess.PIPE if auto_yes else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            if auto_yes and process.stdin:
                try:
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    process.stdin.close()
                except Exception:
                    pass

            def read_stream(stream, lines_list, stream_type):
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            line_stripped = line.rstrip("\n\r")
                            lines_list.append(line_stripped)
                            publish_tool_event(
                                {
                                    "event_type": "shell_output",
                                    "stream": stream_type,
                                    "line": line_stripped,
                                }
                            )
                finally:
                    stream.close()

            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines, "stdout"))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines, "stderr"))

            stdout_thread.start()
            stderr_thread.start()

            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout_thread.join(timeout=1)
                stderr_thread.join(timeout=1)
                publish_tool_event(
                    {
                        "event_type": "shell_finished",
                        "command": command,
                        "status": "timeout",
                    }
                )
                raise RuntimeError(f"Command timed out ({timeout}s): {command}") from None

            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)

            publish_tool_event(
                {
                    "event_type": "shell_finished",
                    "command": command,
                    "return_code": return_code,
                    "status": "completed" if return_code == 0 else "failed",
                }
            )

        except Exception as e:
            if "timed out" not in str(e):
                publish_tool_event(
                    {
                        "event_type": "shell_finished",
                        "command": command,
                        "status": "error",
                        "error": str(e),
                    }
                )
            raise RuntimeError(f"Command execution error: {e!s}") from e

        output_lines = [
            f"Command: {command}",
            f"Working Dir: {get_relative_path(work_dir) or '.'}",
            f"Return Code: {return_code}",
            "",
        ]

        stdout_text = "\n".join(stdout_lines)
        stderr_text = "\n".join(stderr_lines)

        if stdout_text:
            output_lines.extend(["─── STDOUT ───", stdout_text])
        if stderr_text:
            output_lines.extend(["─── STDERR ───", stderr_text])

        if return_code != 0:
            error_msg = stderr_text if stderr_text else stdout_text
            raise RuntimeError(f"Command failed (Code {return_code}):\n{error_msg}")

        return "\n".join(output_lines)

    def get_args_schema(self) -> type[BaseModel]:
        return ShellArgs


# ═══════════════════════════════════════════════════════════════
# Process Management Tool
# ═══════════════════════════════════════════════════════════════


class ProcessArgs(BaseModel):
    action: Literal["list", "kill", "logs"] = Field(
        ...,
        description="Action to perform: 'list' (active processes), 'kill' (terminate), 'logs' (tail log of process)",
    )
    pid: int = Field(..., description="Process ID (required for 'kill' and 'logs')")
    lines: int = Field(20, description="Number of lines to read for 'logs' (default: 20)")


class ProcessManagementTool(BaseTool):
    """
    Manage background processes and view logs.

    Actions:
    - list: Show all running background processes started by the agent.
    - kill: Terminate a specific process by PID.
    - logs: Tail the last N lines of a log file associated with a PID.
    """

    def __init__(self):
        super().__init__(
            name="process_manager",
            description="Manage background processes (list, kill, logs).",
        )

    def _run(
        self,
        action: Literal["list", "kill", "logs"],
        pid: int | None = None,
        lines: int = 20,
    ) -> str:
        if action == "list":
            return self._list_processes()
        if action == "kill":
            if pid is None:
                raise ValueError("PID is required for 'kill' action")
            return self._kill_process(pid)
        if action == "logs":
            if pid is None:
                raise ValueError("PID is required for 'logs' action")
            return self._tail_log(pid, lines)
        raise ValueError(f"Unknown action: {action}")

    def _list_processes(self) -> str:
        active = _process_registry.get_active_processes()
        if not active:
            return "No active background processes found."

        output = [
            "Active Background Processes:",
            "PID   | Status  | Started (s) | Command",
        ]
        output.append("-" * 60)
        now = time.time()
        for p in active:
            elapsed = int(now - p.start_time)
            cmd_preview = (p.command[:30] + "...") if len(p.command) > 30 else p.command
            output.append(f"{p.pid:<5} | {p.status:<7} | {elapsed:<11} | {cmd_preview}")

        return "\n".join(output)

    def _kill_process(self, pid: int) -> str:
        if _process_registry.kill_process(pid):
            return f"Successfully terminated process {pid}."
        return f"Failed to terminate process {pid}. It may have already exited or does not exist."

    def _tail_log(self, pid: int, lines: int) -> str:
        proc_info = _process_registry.get_process_info(pid)
        if not proc_info:
            return f"No registered process found with PID: {pid}"

        try:
            path = Path(proc_info.log_file)
            if not path.exists():
                return f"Log file for PID {pid} not found: {get_relative_path(path)}"

            with open(path, encoding="utf-8", errors="replace") as f:
                tail_lines = collections.deque(f, maxlen=lines)

            content = "".join(tail_lines)
            return f"Last {len(tail_lines)} lines of log for PID {pid} ({get_relative_path(path)}):\n\n{content}"
        except Exception as e:
            return f"Error reading log file for PID {pid}: {e}"

    def get_args_schema(self) -> type[BaseModel]:
        return ProcessArgs
