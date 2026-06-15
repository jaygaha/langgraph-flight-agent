"""
Building a BYOM (Bring Your Own Model) Factory

To make our agent flexible enough to swap between local Ollama, Claude Code, OpenAI, or any other provider seamlessly,
 we will implement an LLM Factory Pattern. This decouples our business logic (nodes) from the specific model
 implementation.
"""
import os
import logging
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


def get_llm() -> BaseChatModel:
    """Factory function to return the configured LLM provider based on environment variables."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model_name = os.getenv("LLM_MODEL", "llama3.1")

    logger.info("Initializing LLM | provider=%s model=%s", provider, model_name)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name, temperature=0)
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, temperature=0, api_key=api_key)
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider!r}")