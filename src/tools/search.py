from typing import Type

import requests
from pydantic import BaseModel, Field

from ..config import settings
from .base import BaseTool


class SearchInput(BaseModel):
    query: str = Field(description="The search query to execute")
    count: int = Field(
        default=5, description="Number of results to return (default: 5, max: 20)"
    )


class BraveSearchTool(BaseTool):
    """
    Tool for searching the web using Brave Search API.
    Useful for finding documentation, examples, and API references.
    """

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for documentation, code examples, and API references using Brave Search.",
        )
        self.api_key = (
            settings.brave_api_key.get_secret_value()
            if settings.brave_api_key
            else None
        )
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def get_args_schema(self) -> Type[BaseModel]:
        return SearchInput

    def _run(self, query: str, count: int = 5) -> str:
        if not self.api_key:
            return "Error: Brave Search API key not configured. Please set BRAVE_API_KEY in .env file."

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
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            results = []

            # Process web results
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    title = item.get("title", "No title")
                    url = item.get("url", "No URL")
                    description = item.get("description", "No description")
                    results.append(
                        f"Title: {title}\nURL: {url}\nDescription: {description}\n"
                    )

            if not results:
                return f"No results found for query: {query}"

            return "\n---\n".join(results)

        except requests.exceptions.RequestException as e:
            return f"Error performing search: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
