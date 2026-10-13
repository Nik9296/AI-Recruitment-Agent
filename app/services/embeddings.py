"""Embedding factory. Reuses GOOGLE_API_KEY from existing settings."""

from __future__ import annotations

from typing import Protocol

from app.config.settings import get_settings
from app.services.llm import LLMConfigurationError


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


def get_embedding_model() -> Embedder:
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return _build_gemini_embeddings(
            settings.embedding_model, settings.google_api_key
        )
    raise NotImplementedError(
        f"Embeddings for LLM provider '{settings.llm_provider}' are not wired yet. "
        "Set LLM_PROVIDER=gemini."
    )


def _build_gemini_embeddings(model: str, api_key: str | None) -> Embedder:
    if not api_key:
        raise LLMConfigurationError(
            "GOOGLE_API_KEY is required when LLM_PROVIDER=gemini"
        )
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
