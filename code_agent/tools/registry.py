"""
Tool Registry - Centralized Tool Management
Design Philosophy:
  - Single Registry Point (Eliminate scattered tool definitions)
  - Lazy Initialization (Load on demand, save resources)
  - Type Safety (Avoid runtime errors)
"""

from langchain_core.tools import (
    StructuredTool,
)

from code_agent.utils.logger import logger

from .base import BaseTool
from .edit import (
    AppendFileTool,
    DeleteLinesTool,
    InsertLinesTool,
    StrReplaceTool,
)
from .file_ops import ListFilesTool, ReadFileTool, WriteFileTool
from .filesystem import (
    CopyFileTool,
    CreateDirectoryTool,
    DeletePathTool,
    MoveFileTool,
    PathExistsTool,
)
from .grep import GrepTool
from .planning import SubmitPlanTool
from .search import BraveSearchTool
from .shell import ProcessManagementTool, ShellTool

# Tool Registry (Singleton Pattern)


class ToolRegistry:
    """
    Global Tool Registry

    Good Taste:
      - Access tools by name, no if/elif type checking
      - Unified initialization logic, eliminating duplicate code
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """
        Register built-in tools

        Good Taste:
          - Cross-platform filesystem tools come first
          - Shell tool is still available for advanced use
          - Tools are organized by category
        """
        default_tools = [
            # File I/O (Basic)
            ReadFileTool(),
            WriteFileTool(),
            ListFilesTool(),
            # Code Search
            GrepTool(),  # Fast code search with ripgrep
            # Precision Edit Tools (RECOMMENDED for modifications)
            StrReplaceTool(),  # Replace exact string match
            InsertLinesTool(),  # Insert at specific line
            DeleteLinesTool(),  # Delete line range
            AppendFileTool(),  # Append to end of file
            # Filesystem Operations (Cross-platform)
            CreateDirectoryTool(),
            CopyFileTool(),
            MoveFileTool(),
            DeletePathTool(),
            PathExistsTool(),
            # Shell (Advanced)
            ShellTool(),
            ProcessManagementTool(),
            # Planning
            SubmitPlanTool(),
            # Sub-Agent (Context Isolation)
            # External
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
            raise KeyError(f"Tool '{name}' not registered. Available tools: {available}")
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


# Global Singleton

_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get global tool registry"""
    return _global_registry
