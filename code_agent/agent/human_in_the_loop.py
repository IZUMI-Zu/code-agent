import fnmatch
import json
import pathlib
import time
import uuid
from typing import Any

from langchain_core.tools import BaseTool
from langgraph.types import interrupt

from code_agent.config import settings
from code_agent.utils.event_bus import publish_tool_event
from code_agent.utils.logger import logger

from .context import get_current_worker


class PatternManager:
    """Manages allow patterns for tools."""

    def __init__(self):
        self.patterns: dict[str, list[str]] = {
            "allow": [],
            "deny": [],
            "ask": [],
        }
        self.pattern_file = settings.workspace_root / settings.allowed_patterns_file
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from file."""
        if self.pattern_file.exists():
            try:
                content = self.pattern_file.read_text(encoding="utf-8")
                data = json.loads(content)
                self.patterns = data.get("permissions", self.patterns)
                logger.info(f"Loaded permissions from {self.pattern_file}")
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")

    def add_pattern(self, pattern: str):
        if pattern not in self.patterns["allow"]:
            self.patterns["allow"].append(pattern)
            self._save_patterns()
            logger.info(f"Added allow pattern: {pattern}")

    def _save_patterns(self):
        """Save patterns to file."""
        try:
            # Ensure workspace exists
            settings.workspace_root.mkdir(parents=True, exist_ok=True)

            data = {"permissions": self.patterns}
            with pathlib.Path(self.pattern_file).open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

    def is_allowed(self, tool_name: str, args: dict[str, Any]) -> bool:
        # Check allow patterns
        return any(self._match_pattern(pattern, tool_name, args) for pattern in self.patterns["allow"])

    def _match_pattern(self, pattern: str, tool_name: str, args: dict[str, Any]) -> bool:
        # Pattern format: "ToolName" or "ToolName(arg_pattern)"

        # Simple tool name match
        if "(" not in pattern:
            return fnmatch.fnmatch(tool_name, pattern)

        # Parse ToolName(arg_pattern)
        try:
            p_tool_name, p_args = pattern.split("(", 1)
            p_args = p_args.rstrip(")")

            if not fnmatch.fnmatch(tool_name, p_tool_name):
                return False

            # If args pattern is "*", allow all args
            if p_args == "*":
                return True

            # For now, we only support simple string matching on args representation
            # A more robust implementation would parse args and match specific fields
            # But user example "Bash(python test_agent.py:*)" suggests string matching

            # Convert args to string for matching
            # This is a simplification. Ideally we should match specific keys.
            # But given the example, let's try to match the string representation of args values

            # If pattern contains ":", maybe it's "key:value_pattern"
            # Example: "Bash(python test_agent.py:*)" -> This looks like a command string match

            # Let's try to match against the string representation of the main argument
            # For shell tool, the main arg is usually 'commands' or 'cmd'

            args_str = str(args)
            return fnmatch.fnmatch(args_str, f"*{p_args}*")

        except Exception:
            return False


# Global instance
pattern_manager = PatternManager()


def wrap_tool_with_confirmation(tool: BaseTool) -> BaseTool:
    """Wraps a tool with human-in-the-loop confirmation."""

    # Store the original _run method
    original_func = tool._run

    def wrapped_func(*args, config=None, **kwargs):
        tool_name = tool.name
        # Extract arguments. LangChain tools usually receive arguments as kwargs
        # or a single dict in args[0] if invoked directly.
        # But when called via agent, it's usually kwargs.
        base_kwargs = dict(kwargs)

        def _args_preview() -> dict[str, Any]:
            if base_kwargs:
                return {k: v for k, v in base_kwargs.items() if k != "config"}
            if args:
                candidate = args[0]
                if isinstance(candidate, dict):
                    return candidate
            return {}

        args_snapshot = _args_preview()
        worker_name = get_current_worker()

        def _execute(decision_source: str = "auto"):
            call_id = str(uuid.uuid4())
            start_ts = time.time()
            publish_tool_event(
                {
                    "event_type": "tool_started",
                    "call_id": call_id,
                    "tool": tool_name,
                    "args": args_snapshot,
                    "decision": decision_source,
                    "worker": worker_name,
                }
            )

            call_kwargs = dict(base_kwargs)
            call_kwargs["config"] = config

            status = "completed"
            error_message = None
            result_preview = None
            try:
                result = original_func(*args, **call_kwargs)
                result_preview = str(result)
                return result
            except Exception as exc:
                # ═══════════════════════════════════════════════════════════════
                # Special handling for control flow exceptions
                # ═══════════════════════════════════════════════════════════════
                # PlanSubmittedException is NOT an error - it's a control flow signal
                # We must re-raise it so the worker_node can catch it
                from code_agent.tools.planning import PlanSubmittedException

                if isinstance(exc, PlanSubmittedException):
                    # Re-raise control flow exceptions
                    logger.info(f"Tool {tool_name}: Re-raising control flow exception")
                    status = "control_flow"  # Mark as control flow, not error
                    result_preview = f"Control flow: {exc!s}"
                    raise

                # For real errors, convert to string for agent retry
                status = "failed"
                error_message = str(exc)
                # Return error as string instead of raising
                # This allows the agent to see the error and retry with different approach
                return f"Error: {error_message}"
            finally:
                duration = time.time() - start_ts
                event_payload = {
                    "event_type": "tool_finished",
                    "call_id": call_id,
                    "tool": tool_name,
                    "status": status,
                    "duration": duration,
                    "args": args_snapshot,
                    "decision": decision_source,
                    "worker": worker_name,
                }
                if result_preview is not None and status == "completed":
                    event_payload["result_preview"] = result_preview[:400]
                if error_message:
                    event_payload["error"] = error_message[:400]
                publish_tool_event(event_payload)

        def _emit_rejection(decision_source: str):
            publish_tool_event(
                {
                    "event_type": "tool_rejected",
                    "tool": tool_name,
                    "status": "rejected",
                    "args": args_snapshot,
                    "decision": decision_source,
                    "worker": worker_name,
                }
            )

        # Check if allowed
        if pattern_manager.is_allowed(tool_name, args_snapshot):
            logger.info(f"Tool {tool_name} allowed by pattern.")
            return _execute("allow_pattern")

        # Interrupt
        logger.info(f"Interrupting tool {tool_name} for confirmation.")
        publish_tool_event(
            {
                "event_type": "tool_confirmation_requested",
                "tool": tool_name,
                "args": args_snapshot,
                "description": tool.description,
                "worker": worker_name,
            }
        )
        decision = interrupt(
            {
                "type": "tool_confirmation",
                "tool": tool_name,
                "args": args_snapshot,
                "description": tool.description,
            }
        )

        # Handle decision
        action = decision.get("action")
        if action == "approve":
            return _execute("user_approved")
        if action == "reject":
            _emit_rejection("user_rejected")
            reason = decision.get("reason", "")
            if reason:
                return f"Tool call {tool_name} rejected by user. Reason: {reason}"
            return f"Tool call {tool_name} rejected by user."
        if action == "allow_pattern":
            # Add pattern and execute
            pattern = decision.get("pattern")
            if pattern:
                pattern_manager.add_pattern(pattern)
            return _execute("session_allow")
        return f"Unknown decision action: {action}"

    # We need to handle both sync and async, but for now we focus on sync _run.
    # IMPORTANT: LangChain tools might expect 'config' in kwargs which is passed by Runnable.
    # We must ensure we accept any arguments and pass them through.

    tool._run = wrapped_func

    return tool
