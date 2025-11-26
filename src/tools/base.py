"""
═══════════════════════════════════════════════════════════════
Tool Base Class - Abstraction to Eliminate Special Cases
═══════════════════════════════════════════════════════════════
Design Philosophy:
  - Good Taste: All tools share a unified interface, no type checking needed
  - Simplicity: Each tool does one thing only
  - Pragmatism: Exception handling is cohesive, callers don't need to worry about details
  - Resilience: Built-in timeout and retry for production reliability
"""

import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils.logger import logger

# ═══════════════════════════════════════════════════════════════
# Exception Types
# ═══════════════════════════════════════════════════════════════


class ToolTimeoutError(Exception):
    """Raised when tool execution exceeds timeout"""

    pass


class RetryableError(Exception):
    """Base class for errors that should trigger retry"""

    pass


# ═══════════════════════════════════════════════════════════════
# Tool Base Class (Unified Abstraction)
# ═══════════════════════════════════════════════════════════════


class BaseTool(ABC):
    """
    Minimalist Tool Abstraction with Resilience

    Good Taste:
      - Only one public method execute()
      - Internal handling of all exceptions, external always gets unified structure
      - Subclasses don't handle errors, focus on business logic
      - Built-in timeout and retry for production reliability

    Configuration:
      - timeout: Max execution time in seconds (default: 120)
      - max_retries: Number of retry attempts for retryable errors (default: 2)
      - retry_min_wait: Min wait between retries in seconds (default: 1)
      - retry_max_wait: Max wait between retries in seconds (default: 10)
    """

    def __init__(
        self,
        name: str,
        description: str,
        timeout: int = 120,
        max_retries: int = 2,
        retry_min_wait: int = 1,
        retry_max_wait: int = 10,
    ):
        self.name = name
        self.description = description
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait
        self._executor = ThreadPoolExecutor(max_workers=1)

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

    def _run_with_retry(self, **kwargs: Any) -> str:
        """
        Internal wrapper for _run with retry logic

        Design Philosophy:
          - Dynamic retry decorator based on instance config
          - Only retries on RetryableError (network, timeout, etc.)
          - Non-retryable errors (permission, file not found) fail immediately
        """
        # Create retry decorator dynamically based on instance config
        retry_decorator = retry(
            retry=retry_if_exception_type(RetryableError),
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(
                min=self.retry_min_wait, max=self.retry_max_wait
            ),
            before_sleep=lambda retry_state: logger.warning(
                f"Tool {self.name} retry {retry_state.attempt_number}/{self.max_retries} "
                f"after error: {retry_state.outcome.exception()}"
            ),
        )

        # Apply retry decorator to _run
        retryable_run = retry_decorator(self._run)
        return retryable_run(**kwargs)

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Unified execution entry point with timeout and retry

        Return Structure (Consistent for success/failure):
        {
            "tool_name": str,
            "success": bool,
            "output": str,
            "duration_ms": float
        }

        Good Taste:
          - Timeout applies to entire retry sequence (not per attempt)
          - Unified error format regardless of failure type
          - Callers get simple dict, never see internal exceptions
        """
        start = time.perf_counter()
        logger.debug(f"Executing tool: {self.name} with args: {kwargs}")

        try:
            # Execute with timeout using ThreadPoolExecutor
            future = self._executor.submit(self._run_with_retry, **kwargs)
            output = future.result(timeout=self.timeout)
            success = True
            logger.info(f"Tool {self.name} executed successfully.")

        except FutureTimeoutError:
            output = f"Tool execution timed out after {self.timeout}s"
            success = False
            logger.error(f"Tool {self.name} timed out after {self.timeout}s")

        except Exception as e:
            # Extract inner exception if it's from tenacity
            error_msg = str(e)
            if hasattr(e, "__cause__") and e.__cause__:
                error_msg = str(e.__cause__)

            output = f"Tool execution failed: {error_msg}"
            success = False
            logger.error(f"Tool {self.name} failed: {error_msg}")

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
