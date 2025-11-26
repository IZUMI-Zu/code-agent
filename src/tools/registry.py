"""
═══════════════════════════════════════════════════════════════
Tool Registry - Centralized Tool Management
═══════════════════════════════════════════════════════════════
Design Philosophy:
  - Single Registry Point (Eliminate scattered tool definitions)
  - Lazy Initialization (Load on demand, save resources)
  - Type Safety (Avoid runtime errors)
"""

from typing import Dict

from langchain_core.tools import StructuredTool

from ..utils.logger import logger
from .base import BaseTool
from .file_ops import ListFilesTool, ReadFileTool, WriteFileTool
from .planning import SubmitPlanTool
from .search import BraveSearchTool
from .shell import ShellTool

# ═══════════════════════════════════════════════════════════════
# Tool Registry (Singleton Pattern)
# ═══════════════════════════════════════════════════════════════


class ToolRegistry:
    """
    Global Tool Registry

    Good Taste:
      - Access tools by name, no if/elif type checking
      - Unified initialization logic, eliminating duplicate code
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register built-in tools"""
        default_tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListFilesTool(),
            ShellTool(),
            SubmitPlanTool(),
            BraveSearchTool(),
        ]

        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool):
        """Register a new tool"""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool:
        """Get tool (Raise explicit exception if not found)"""
        if name not in self._tools:
            available = ", ".join(self._tools.keys())
            raise KeyError(
                f"Tool '{name}' not registered. Available tools: {available}"
            )
        return self._tools[name]

    def list_all(self) -> list[BaseTool]:
        """List all registered tools"""
        return list(self._tools.values())

    def get_all_tools(self) -> list[BaseTool]:
        """Get all registered tools (Alias)"""
        return self.list_all()

    def get_tool_descriptions(self) -> list[StructuredTool]:
        """
        Get descriptions of all tools (For LLM use)

        Return Format:
        [
            {
                "name": "read_file",
                "description": "...",
                "parameters": {...}
            },
            ...
        ]
        """
        return [tool.to_langchain_tool() for tool in self._tools.values()]


# ═══════════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════════

_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get global tool registry"""
    return _global_registry
