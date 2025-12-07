"""
═══════════════════════════════════════════════════════════════
Tool Registry - Centralized Tool Management
═══════════════════════════════════════════════════════════════
Design Philosophy:
  - Single Registry Point (Eliminate scattered tool definitions)
  - Lazy Initialization (Load on demand, save resources)
  - Type Safety (Avoid runtime errors)
  - MCP Integration (Load tools from MCP servers)
"""

import asyncio
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_core.tools import StructuredTool

from ..utils.logger import logger
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
      - MCP tools loaded asynchronously on demand
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._mcp_tools: List[LangChainBaseTool] = []
        self._mcp_loaded: bool = False
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
            GrepTool(),            # Fast code search with ripgrep
            # Precision Edit Tools (RECOMMENDED for modifications)
            StrReplaceTool(),      # Replace exact string match
            InsertLinesTool(),     # Insert at specific line
            DeleteLinesTool(),     # Delete line range
            AppendFileTool(),      # Append to end of file
            # Filesystem Operations (Cross-platform)
            CreateDirectoryTool(),
            CopyFileTool(),
            MoveFileTool(),
            DeletePathTool(),
            PathExistsTool(),
            # Shell (Advanced)
            ShellTool(),
            # Planning
            SubmitPlanTool(),
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
    
    async def load_mcp_tools(self, server_configs: Optional[Dict] = None):
        """
        Load tools from MCP servers
        
        Args:
            server_configs: Optional MCP server configurations
                           If None, uses default config (fetch server)
        
        Note:
            - Only loads once (cached)
            - Call reload_mcp_tools() to refresh
        """
        if self._mcp_loaded:
            logger.info("MCP tools already loaded (using cache)")
            return
        
        try:
            from .mcp_loader import load_mcp_tools
            
            logger.info("Loading MCP tools...")
            self._mcp_tools = await load_mcp_tools(server_configs)
            self._mcp_loaded = True
            
            logger.info(f"Loaded {len(self._mcp_tools)} MCP tools")
            
        except ImportError:
            logger.warning(
                "langchain-mcp-adapters not installed. "
                "Install with: uv add langchain-mcp-adapters"
            )
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            logger.warning("Continuing without MCP tools")
    
    async def reload_mcp_tools(self, server_configs: Optional[Dict] = None):
        """
        Reload MCP tools (clears cache)
        
        Args:
            server_configs: Optional MCP server configurations
        """
        self._mcp_loaded = False
        self._mcp_tools = []
        await self.load_mcp_tools(server_configs)
    
    def get_all_tools_with_mcp(self) -> List:
        """
        Get all tools including MCP tools
        
        Returns:
            List of all tools (built-in + MCP)
            
        Note:
            - MCP tools must be loaded first with load_mcp_tools()
            - Returns only built-in tools if MCP not loaded
        """
        built_in = self.list_all()
        return built_in + self._mcp_tools

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
        
        Note:
            - Only returns built-in tools
            - Use get_tool_descriptions_with_mcp() for MCP tools
        """
        return [tool.to_langchain_tool() for tool in self._tools.values()]
    
    def get_tool_descriptions_with_mcp(self) -> List:
        """
        Get descriptions of all tools including MCP tools
        
        Returns:
            List of all tool descriptions (built-in + MCP)
        """
        built_in = self.get_tool_descriptions()
        return built_in + self._mcp_tools


# ═══════════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════════

_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get global tool registry"""
    return _global_registry
