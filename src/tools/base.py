"""
═══════════════════════════════════════════════════════════════
工具基类 - 消除特殊情况的抽象
═══════════════════════════════════════════════════════════════
设计哲学：
  - 好品味：所有工具都是统一接口,无需判断类型
  - 简洁执念：每个工具只做一件事
  - 实用主义：异常处理内聚,调用者无需关心细节
"""

from abc import ABC, abstractmethod
from typing import Any
from langchain_core.tools import StructuredTool
import time


# ═══════════════════════════════════════════════════════════════
# 工具基类（统一抽象）
# ═══════════════════════════════════════════════════════════════

class BaseTool(ABC):
    """
    工具的最小化抽象

    好品味体现：
      - 只有一个公共方法 execute()
      - 内部处理所有异常,外部永远得到统一结构
      - 无需子类处理错误,专注业务逻辑
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def _run(self, **kwargs: Any) -> str:
        """
        子类实现的核心逻辑（无需处理异常）

        Args:
            **kwargs: 工具参数

        Returns:
            执行结果字符串
        """
        pass

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        统一执行入口（处理异常+计时）

        返回结构（无论成功失败都一致）：
        {
            "tool_name": str,
            "success": bool,
            "output": str,
            "duration_ms": float
        }
        """
        start = time.perf_counter()

        try:
            output = self._run(**kwargs)
            success = True
        except Exception as e:
            output = f"工具执行失败: {str(e)}"
            success = False

        duration = (time.perf_counter() - start) * 1000

        return {
            "tool_name": self.name,
            "success": success,
            "output": output,
            "duration_ms": round(duration, 2)
        }

    def to_langchain_tool(self) -> StructuredTool:
        """
        转换为 LangChain StructuredTool

        好品味体现:
          - 直接返回 LangChain 的 Tool 对象
          - 无需手动序列化/反序列化
          - 类型安全
        """
        return StructuredTool.from_function(
            func=self._run,
            name=self.name,
            description=self.description,
            args_schema=self._get_parameters()
        )

    @abstractmethod
    def _get_parameters(self) -> dict[str, Any]:
        """
        定义工具参数 schema（JSON Schema 格式）
        """
        pass
