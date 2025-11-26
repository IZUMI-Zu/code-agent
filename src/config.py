from typing import Optional

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: SecretStr
    openai_model_name: str = "gpt-4o"
    openai_base_url: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_api_key(self):
        if not self.openai_api_key:
            raise ValueError(
                "openai_api_key is required. Please set OPENAI_API_KEY environment variable."
            )
        return self


settings = Settings()
