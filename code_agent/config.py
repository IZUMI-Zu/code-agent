import hashlib
from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Make optional for static analysis, but enforced by validator at runtime
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = "https://api.openai.com/v1"
    brave_api_key: SecretStr | None = None

    # Use lightweight models for simple checks, heavyweight for reasoning
    lightweight_model: str = "gpt-4o-mini"
    reasoning_model: str = "gpt-4o"

    # Conversation Memory Management
    # Prevents context window overflow by auto-summarizing old messages
    summarization_trigger_tokens: int = 100000  # Trigger when exceeding N tokens
    summarization_keep_messages: int = 30  # Keep last N messages intact

    # Workspace Configuration
    workspace_root: Path = Path()

    @property
    def state_dir(self) -> Path:
        """
        Get the state directory for this workspace.

        Design: Separate agent state from user workspace
        - State dir: ~/.code_agent/{workspace_hash}/
        - This prevents `.code_agent/` from polluting the workspace
        - Each workspace gets a unique state dir based on path hash
        """
        # Use home directory as base (cross-platform)
        base = Path.home() / ".code_agent"

        # Create workspace-specific subdirectory using path hash
        # This allows multiple projects to have separate permission files
        workspace_hash = hashlib.sha256(str(self.workspace_root.resolve()).encode()).hexdigest()[
            :12
        ]  # First 12 chars is enough

        state_path = base / workspace_hash
        state_path.mkdir(parents=True, exist_ok=True)
        return state_path

    @property
    def allowed_patterns_file(self) -> Path:
        """Get the full path to the allowed patterns file"""
        return self.state_dir / "allowed_patterns.json"

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
