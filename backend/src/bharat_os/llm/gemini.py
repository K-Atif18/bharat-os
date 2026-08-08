"""Google Gemini provider.

Uses the REST API over plain HTTP rather than a vendor SDK, which keeps the
dependency surface small and makes the request shape visible at the call site.

The model name is never hardcoded — it comes from configuration, because model
identifiers change and pinning one in source guarantees a future outage.
"""

from __future__ import annotations

import json
import logging

import httpx

from bharat_os.llm.base import (
    LLMError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    parse_json_object,
)

logger = logging.getLogger(__name__)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT_SECONDS = 45.0


class GeminiProvider(LLMProvider):
    """Gemini via the Generative Language API."""

    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError(
                "BHARAT_OS_GEMINI_API_KEY is not set. Set it, or run with "
                "BHARAT_OS_LLM_PROVIDER=mock."
            )
        self._api_key = api_key
        self.model = model

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
                # Ask for JSON explicitly. The parser is still tolerant, because
                # asking is not the same as receiving.
                "responseMimeType": "application/json",
            },
        }

        url = f"{API_ROOT}/models/{self.model}:generateContent"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self._api_key},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Gemini: {exc}") from exc

        if response.status_code != 200:
            # The API key must never reach a log or an error message.
            raise LLMError(f"Gemini returned HTTP {response.status_code}: {response.text[:300]}")

        try:
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise LLMError(f"Unexpected Gemini response shape: {exc}") from exc

        usage_meta = body.get("usageMetadata", {})
        return LLMResponse(
            data=parse_json_object(text, request.required_keys),
            provider=self.name,
            model=self.model,
            prompt=request.prompt,
            raw_text=text,
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            },
        )
