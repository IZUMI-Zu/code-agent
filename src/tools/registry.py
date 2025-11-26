"""
═══════════════════════════════════════════════════════════════
工具注册中心 - 统一管理所有工具
═══════════════════════════════════════════════════════════════
设计哲学：
  - 单一注册点（消除分散的工具定义）
  - 延迟初始化（按需加载,节省资源）
  - 类型安全（避免运行时错误）
"""

from typing import Dict

from langchain_core.tools import StructuredTool

from .base import BaseTool
from .file_ops import ListFilesTool, ReadFileTool, WriteFileTool
from .shell import ShellTool

# ═══════════════════════════════════════════════════════════════
# 工具注册表（单例模式）
# ═══════════════════════════════════════════════════════════════


class ToolRegistry:
    """
    全局工具注册中心

    好品味体现：
      - 工具通过名称访问,无需 if/elif 判断类型
      - 统一初始化逻辑,消除重复代码
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """注册内置工具集"""
        default_tools = [ReadFileTool(), WriteFileTool(), ListFilesTool(), ShellTool()]

        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool):
        """注册新工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """获取工具（不存在时抛出明确异常）"""
        if name not in self._tools:
            available = ", ".join(self._tools.keys())
            raise KeyError(f"工具 '{name}' 未注册。可用工具: {available}")
        return self._tools[name]

    def list_all(self) -> list[BaseTool]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def get_all_tools(self) -> list[BaseTool]:
        """获取所有已注册工具(别名方法)"""
        return self.list_all()

    def get_tool_descriptions(self) -> list[StructuredTool]:
        """
        获取所有工具的描述（供 LLM 使用）

        返回格式：
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
# 全局单例
# ═══════════════════════════════════════════════════════════════

_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return _global_registry
