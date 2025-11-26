import fnmatch
from typing import Any, Dict, List

from langchain_core.tools import BaseTool
from langgraph.types import interrupt

from ..config import settings
from ..utils.logger import logger


class PatternManager:
    """Manages allow patterns for tools."""

    def __init__(self):
        self.patterns: List[str] = []
        self.pattern_file = settings.workspace_root / settings.allowed_patterns_file
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from file."""
        if self.pattern_file.exists():
            try:
                content = self.pattern_file.read_text(encoding="utf-8")
                self.patterns = [
                    line.strip() for line in content.splitlines() if line.strip()
                ]
                logger.info(
                    f"Loaded {len(self.patterns)} patterns from {self.pattern_file}"
                )
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")

    def add_pattern(self, pattern: str):
        if pattern not in self.patterns:
            self.patterns.append(pattern)
            self._save_pattern(pattern)
            logger.info(f"Added allow pattern: {pattern}")

    def _save_pattern(self, pattern: str):
        """Append pattern to file."""
        try:
            # Ensure workspace exists
            settings.workspace_root.mkdir(parents=True, exist_ok=True)

            with open(self.pattern_file, "a", encoding="utf-8") as f:
                f.write(f"{pattern}\n")
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")

    def is_allowed(self, tool_name: str, args: Dict[str, Any]) -> bool:
        # Construct a string representation to match against
        # For simplicity, we match against "tool_name" or "tool_name args_str"
        # But usually patterns are like "read_file *" or "read_file src/*"

        # Let's support simple tool name matching first, and maybe arg matching
        # Pattern format: "tool_name" or "tool_name:arg_value_pattern"?
        # The user said "like claude". Claude usually allows "Always allow read_file".

        # Check exact tool name match
        if tool_name in self.patterns:
            return True

        # Check glob patterns
        for pattern in self.patterns:
            if fnmatch.fnmatch(tool_name, pattern):
                return True

        return False


# Global instance
pattern_manager = PatternManager()


def wrap_tool_with_confirmation(tool: BaseTool) -> BaseTool:
    """Wraps a tool with human-in-the-loop confirmation."""

    original_func = tool._run

    def wrapped_func(*args, **kwargs):
        tool_name = tool.name
        tool_args = kwargs if kwargs else (args[0] if args else {})

        # Check if allowed
        if pattern_manager.is_allowed(tool_name, tool_args):
            logger.info(f"Tool {tool_name} allowed by pattern.")
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
            return original_func(*args, **kwargs)
        elif action == "reject":
            return f"Tool call {tool_name} rejected by user."
        elif action == "allow_pattern":
            # Add pattern and execute
            pattern = decision.get("pattern")
            if pattern:
                pattern_manager.add_pattern(pattern)
            return original_func(*args, **kwargs)
        else:
            return f"Unknown decision action: {action}"

    # Patch the tool instance to intercept execution
    # This ensures we catch the call regardless of how the tool is invoked
    tool._run = wrapped_func

    return tool
