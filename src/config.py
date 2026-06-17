import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    # LLM provider config
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1"

    #API keys
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Agent behavor
    max_turns: int = 3
    log_level: str = "INFO"

    # MemorySaver
    checkpoint_db: str = "checkpoints.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic")
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when LLM_PROVIDER=openai")
        return self

def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

settings = Settings()
configure_logging(settings.log_level)