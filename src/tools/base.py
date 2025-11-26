"""
═══════════════════════════════════════════════════════════════
Tool Base Class - Abstraction to Eliminate Special Cases
═══════════════════════════════════════════════════════════════
Design Philosophy:
  - Good Taste: All tools share a unified interface, no type checking needed
  - Simplicity: Each tool does one thing only
  - Pragmatism: Exception handling is cohesive, callers don't need to worry about details
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from ..utils.logger import logger

# ═══════════════════════════════════════════════════════════════
# Tool Base Class (Unified Abstraction)
# ═══════════════════════════════════════════════════════════════


class BaseTool(ABC):
    """
    Minimalist Tool Abstraction

    Good Taste:
      - Only one public method execute()
      - Internal handling of all exceptions, external always gets unified structure
      - Subclasses don't handle errors, focus on business logic
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> str:
        """
        Core logic implemented by subclasses (no exception handling needed)

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Execution result string
        """
        pass

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Unified execution entry point (exception handling + timing)

        Return Structure (Consistent for success/failure):
        {
            "tool_name": str,
            "success": bool,
            "output": str,
            "duration_ms": float
        }
        """
        start = time.perf_counter()
        logger.debug(f"Executing tool: {self.name} with args: {kwargs}")

        try:
            output = self._run(**kwargs)
            success = True
            logger.info(f"Tool {self.name} executed successfully.")
        except Exception as e:
            output = f"Tool execution failed: {str(e)}"
            success = False
            logger.error(f"Tool {self.name} failed: {str(e)}")

        duration = (time.perf_counter() - start) * 1000

        return {
            "tool_name": self.name,
            "success": success,
            "output": output,
            "duration_ms": round(duration, 2),
        }

    def to_langchain_tool(self) -> StructuredTool:
        """
        Convert to LangChain StructuredTool

        Good Taste:
          - Directly return LangChain Tool object
          - No manual serialization/deserialization
          - Type safe
        """
        return StructuredTool.from_function(
            func=self._run,
            name=self.name,
            description=self.description,
            args_schema=self.get_args_schema(),
        )

    @abstractmethod
    def get_args_schema(self) -> Type[BaseModel]:
        """
        Define tool argument schema (Pydantic Model)
        """
        pass
