"""Provider selection.

The active provider is chosen by configuration, never by import. Swapping Gemini
for the mock is an environment variable, which is what makes the test suite free
and a demo resilient to bad wifi.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from bharat_os.config import get_settings
from bharat_os.llm.base import (
    LLMError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMResponseError,
    parse_json_object,
)
from bharat_os.llm.mock import MockProvider

logger = logging.getLogger(__name__)


def build_provider(name: str | None = None) -> LLMProvider:
    """Construct a provider by name, defaulting to the configured one."""
    settings = get_settings()
    provider_name = name or settings.llm_provider

    if provider_name == "mock":
        return MockProvider()

    if provider_name == "gemini":
        # Imported lazily so the mock path never requires httpx to be installed
        # or the network to exist.
        from bharat_os.llm.gemini import GeminiProvider

        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)

    raise LLMError(f"Unknown LLM provider {provider_name!r}")


@lru_cache
def get_provider() -> LLMProvider:
    """The process-wide provider."""
    provider = build_provider()
    logger.info("LLM provider: %s (%s)", provider.name, provider.model)
    return provider


__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMResponseError",
    "MockProvider",
    "build_provider",
    "get_provider",
    "parse_json_object",
]
