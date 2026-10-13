import pytest

from app.core.config import get_settings
from app.core.exceptions import LLMConfigurationError
from app.core.llm import get_chat_model


def test_gemini_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(LLMConfigurationError):
        get_chat_model()
    get_settings.cache_clear()


def test_non_gemini_provider_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    with pytest.raises(NotImplementedError):
        get_chat_model()
    get_settings.cache_clear()
