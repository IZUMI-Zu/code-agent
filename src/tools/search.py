import time

import requests
from pydantic import BaseModel, Field

from src.config import settings

from .base import BaseTool, RetryableError


class SearchInput(BaseModel):
    query: str = Field(description="The search query to execute")
    count: int = Field(default=5, description="Number of results to return (default: 5, max: 20)")


class BraveSearchTool(BaseTool):
    """
    Tool for searching the web using Brave Search API.
    Useful for finding documentation, examples, and API references.

    Configuration:
      - timeout: 30 seconds (network requests should be fast)
      - max_retries: 2 (network errors are retryable)
      - request_timeout: 10 seconds per HTTP request
      - rate_limit: 1 request per second
    """

    # Class-level rate limiting (shared across all instances)
    _last_request_time: float = 0.0
    _rate_limit_interval: float = 1.0  # 1 second between requests

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for documentation, code examples, and API references using Brave Search.",
            timeout=30,  # Total timeout for the tool
            max_retries=2,  # Retry on network errors
        )
        self.api_key = settings.brave_api_key.get_secret_value() if settings.brave_api_key else None
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.request_timeout = 10  # Per-request timeout

    def _wait_for_rate_limit(self):
        """Enforce rate limiting: wait if needed to ensure 1 request per second."""
        current_time = time.time()
        elapsed = current_time - BraveSearchTool._last_request_time
        if elapsed < self._rate_limit_interval:
            wait_time = self._rate_limit_interval - elapsed
            time.sleep(wait_time)
        BraveSearchTool._last_request_time = time.time()

    def get_args_schema(self) -> type[BaseModel]:
        return SearchInput

    def _run(self, query: str, count: int = 5) -> str:
        """
        Execute web search with timeout and retry support

        Design Philosophy:
          - Network errors raise RetryableError (automatic retry)
          - Configuration errors fail immediately (no retry)
          - Timeouts are enforced at HTTP level
          - Rate limiting: 1 request per second
        """
        if not self.api_key:
            # Configuration error - not retryable
            raise ValueError("Brave Search API key not configured. Please set BRAVE_API_KEY in .env file.")

        # Enforce rate limiting before making request
        self._wait_for_rate_limit()

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        params = {
            "q": query,
            "count": min(count, 20),  # Cap at 20
        }

        try:
            # Add timeout to prevent hanging
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            data = response.json()

            results = []

            # Process web results
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    title = item.get("title", "No title")
                    url = item.get("url", "No URL")
                    description = item.get("description", "No description")
                    results.append(f"Title: {title}\nURL: {url}\nDescription: {description}\n")

            if not results:
                return f"No results found for query: {query}"

            return "\n---\n".join(results)

        except requests.exceptions.Timeout:
            # Timeout is retryable
            raise RetryableError(f"Search request timed out after {self.request_timeout}s") from None
        except requests.exceptions.ConnectionError as e:
            # Network connection errors are retryable
            raise RetryableError(f"Network connection error: {e!s}") from e
        except requests.exceptions.RequestException as e:
            # Other request errors (4xx, 5xx) might not be retryable
            # But let's retry 5xx server errors
            if hasattr(e, "response") and e.response is not None and 500 <= e.response.status_code < 600:
                raise RetryableError(f"Server error {e.response.status_code}: {e!s}") from e
            # Client errors (4xx) fail immediately
            raise RuntimeError(f"Search request failed: {e!s}") from e
        except Exception as e:
            # Unexpected errors fail immediately
            raise RuntimeError(f"Unexpected error: {e!s}") from e
