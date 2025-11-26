import fnmatch
import json
from typing import Any, Dict, List

from langchain_core.tools import BaseTool
from langgraph.types import interrupt

from ..config import settings
from ..utils.logger import logger


class PatternManager:
    """Manages allow patterns for tools."""

    def __init__(self):
        self.patterns: Dict[str, List[str]] = {
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
            with open(self.pattern_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

    def is_allowed(self, tool_name: str, args: Dict[str, Any]) -> bool:
        # Check allow patterns
        for pattern in self.patterns["allow"]:
            if self._match_pattern(pattern, tool_name, args):
                return True
        return False

    def _match_pattern(
        self, pattern: str, tool_name: str, args: Dict[str, Any]
    ) -> bool:
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
        tool_args = kwargs

        # Check if allowed
        if pattern_manager.is_allowed(tool_name, tool_args):
            logger.info(f"Tool {tool_name} allowed by pattern.")
            kwargs["config"] = config
            return original_func(*args, **kwargs)

        # Interrupt
        logger.info(f"Interrupting tool {tool_name} for confirmation.")
        decision = interrupt(
            {
                "type": "tool_confirmation",
                "tool": tool_name,
                "args": tool_args,
                "description": tool.description,
            }
        )

        # Handle decision
        action = decision.get("action")
        if action == "approve":
            kwargs["config"] = config
            return original_func(*args, **kwargs)
        elif action == "reject":
            return f"Tool call {tool_name} rejected by user."
        elif action == "allow_pattern":
            # Add pattern and execute
            pattern = decision.get("pattern")
            if pattern:
                pattern_manager.add_pattern(pattern)
            kwargs["config"] = config
            return original_func(*args, **kwargs)
        else:
            return f"Unknown decision action: {action}"

    # We need to handle both sync and async, but for now we focus on sync _run.
    # IMPORTANT: LangChain tools might expect 'config' in kwargs which is passed by Runnable.
    # We must ensure we accept any arguments and pass them through.

    tool._run = wrapped_func

    return tool
