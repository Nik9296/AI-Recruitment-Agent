"""LLM chat-model factory. Phase 1 wires Gemini only."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings
from app.core.exceptions import LLMConfigurationError


def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return _build_gemini(settings.llm_model, settings.llm_temperature, settings.google_api_key)
    raise NotImplementedError(
        f"LLM provider '{settings.llm_provider}' is not wired in Phase 1. "
        "Set LLM_PROVIDER=gemini or extend app.core.llm.get_chat_model."
    )


def _build_gemini(model: str, temperature: float, api_key: str | None) -> BaseChatModel:
    if not api_key:
        raise LLMConfigurationError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
    )
