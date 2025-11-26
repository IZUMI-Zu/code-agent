from pathlib import Path
from typing import Optional

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: SecretStr
    openai_model_name: str = "gpt-4o"
    openai_base_url: Optional[str] = None

    # Workspace Configuration
    workspace_root: Path = Path(".")
    allowed_patterns_file: str = ".allowed_patterns"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_api_key(self):
        if not self.openai_api_key:
            raise ValueError(
                "openai_api_key is required. Please set OPENAI_API_KEY environment variable."
            )
        return self

    @model_validator(mode="after")
    def validate_workspace(self):
        # Ensure workspace exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        return self


settings = Settings()
