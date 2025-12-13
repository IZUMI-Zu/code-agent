from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Make optional for static analysis, but enforced by validator at runtime
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    brave_api_key: SecretStr | None = None

    # Model Stratification (Claude Code Architecture)
    # Use lightweight models for simple checks, heavyweight for reasoning
    # Performance: lightweight is 3-5x faster, 70% cheaper
    lightweight_model: str = "gpt-4o-mini"  # For: topic detection, format validation
    reasoning_model: str = "gpt-4o"  # For: planning, coding, reviewing

    # Conversation Memory Management
    # Prevents context window overflow by auto-summarizing old messages
    summarization_trigger_tokens: int = 4000  # Trigger when exceeding N tokens
    summarization_keep_messages: int = 20  # Keep last N messages intact

    # Workspace Configuration
    workspace_root: Path = Path()
    allowed_patterns_file: str = ".allowed_patterns"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_api_key(self) -> Self:
        if not self.openai_api_key:
            raise ValueError("openai_api_key is required. Please set OPENAI_API_KEY environment variable.")
        return self

    def _init_workspace(self) -> None:
        """Internal helper to ensure workspace directory exists"""
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    @model_validator(mode="after")
    def validate_workspace(self) -> Self:
        self._init_workspace()
        return self

    def override_workspace(self, workspace_path: Path) -> Self:
        self.workspace_root = workspace_path
        # Use internal helper instead of calling validator directly
        self._init_workspace()
        return self


settings = Settings()
