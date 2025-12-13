"""
MCP (Model Context Protocol) Tool Loader
Integrates MCP servers as LangChain tools using langchain-mcp-adapters.

Architecture:
  - MultiServerMCPClient: Manages multiple MCP servers
  - Stateless by default: Each tool call creates a fresh session
  - Async-first: All MCP operations are async

Reference:
  - https://docs.langchain.com/oss/python/langchain/mcp
"""

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from code_agent.utils.logger import logger


class MCPToolLoader:
    """
    Load tools from MCP servers and convert them to LangChain tools

    Example MCP server config:
    {
        "fetch": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-fetch"]
        },
        "filesystem": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-filesystem", "/path/to/allowed/dir"]
        }
    }

    Transport types:
        - "stdio": Local subprocess (for uvx, npx, node commands)
        - "sse": Server-Sent Events (for HTTP streaming)
        - "websocket": WebSocket connection
        - "streamable_http": HTTP streaming
    """

    def __init__(self, server_configs: dict | None = None):
        """
        Initialize MCP tool loader

        Args:
            server_configs: Dict of MCP server configurations
                           If None, uses default config (fetch server)
        """
        self.server_configs = server_configs or self._get_default_config()
        self.client: MultiServerMCPClient | None = None
        self._tools_cache: list[BaseTool] | None = None

    def _get_default_config(self) -> dict:
        """
        Get default MCP server configuration

        Returns:
            Default config with fetch server
        """
        return {
            "fetch": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["mcp-server-fetch"],
            }
        }

    async def load_tools(self) -> list[BaseTool]:
        """
        Load tools from all configured MCP servers

        Returns:
            List of LangChain tools from MCP servers

        Note:
            - Tools are cached after first load
            - Call reload_tools() to refresh
        """
        if self._tools_cache is not None:
            logger.info(f"Using cached MCP tools ({len(self._tools_cache)} tools)")
            return self._tools_cache

        try:
            logger.info(f"Loading MCP tools from {len(self.server_configs)} servers...")

            # Create MCP client
            self.client = MultiServerMCPClient(self.server_configs)

            # Get tools from all servers
            tools = await self.client.get_tools()

            self._tools_cache = tools
            logger.info(f"Successfully loaded {len(tools)} MCP tools")

            # Log tool names for debugging
            tool_names = [t.name for t in tools]
            logger.debug(f"MCP tools: {tool_names}")

            return tools

        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            logger.warning("Continuing without MCP tools")
            return []

    async def reload_tools(self) -> list[BaseTool]:
        """
        Reload tools from MCP servers (clears cache)

        Returns:
            Fresh list of LangChain tools
        """
        self._tools_cache = None
        self.client = None

        return await self.load_tools()

    async def close(self):
        """Close MCP client and cleanup resources"""
        # MultiServerMCPClient is stateless/manages its own sessions,
        # so no explicit close is needed.


# Singleton instance for easy access

_mcp_loader: MCPToolLoader | None = None


def get_mcp_loader(server_configs: dict | None = None) -> MCPToolLoader:
    """
    Get singleton MCP tool loader instance

    Args:
        server_configs: Optional server configs (only used on first call)

    Returns:
        MCPToolLoader instance
    """
    global _mcp_loader
    if _mcp_loader is None:
        _mcp_loader = MCPToolLoader(server_configs)
    return _mcp_loader


async def load_mcp_tools(server_configs: dict | None = None) -> list[BaseTool]:
    """
    Convenience function to load MCP tools

    Args:
        server_configs: Optional server configs

    Returns:
        List of LangChain tools from MCP servers

    Example:
        >>> tools = await load_mcp_tools()
        >>> print([t.name for t in tools])
        ['fetch', 'fetch_html', ...]
    """
    loader = get_mcp_loader(server_configs)
    return await loader.load_tools()
