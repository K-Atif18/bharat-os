"""The language model boundary.

Everything the rest of the system knows about language models lives behind this
interface. Three reasons that matters here more than usual:

**Substitutability.** A dead API key or a rate limit at the wrong moment must be a
configuration change, not a debugging session.

**Testability.** :class:`MockProvider` returns deterministic, realistic responses
with no network access, so the suite runs offline, instantly and for free — and so
does a demo on bad conference wifi.

**Auditability.** Every call returns the prompt and the model identity alongside
the answer, so a judgement shown to a user can always be traced back to what was
actually asked and which model answered.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """A provider could not be reached or returned something unusable."""


class LLMResponseError(LLMError):
    """The model replied, but not in the shape that was demanded."""


@dataclass(frozen=True)
class LLMRequest:
    """A structured-output request."""

    #: Instructions describing the model's role and constraints.
    system: str
    #: The specific question.
    prompt: str
    #: Keys the response object must contain. Absence is an error, not a default.
    required_keys: tuple[str, ...]
    #: Low by default: this is a classification task, and creative variation in
    #: an eligibility judgement is a defect rather than a feature.
    temperature: float = 0.1
    max_output_tokens: int = 1024


@dataclass(frozen=True)
class LLMResponse:
    """A parsed response, with everything needed to audit it later."""

    data: dict[str, Any]
    #: Provider identifier, e.g. ``"gemini"`` or ``"mock"``.
    provider: str
    #: Exact model version that answered, recorded because model behaviour drifts
    #: between versions and an old judgement must stay explicable.
    model: str
    #: The prompt as sent, stored for the audit trail.
    prompt: str
    raw_text: str = ""
    #: True when the answer came from cache rather than the provider.
    cached: bool = False
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(ABC):
    """A language model that returns JSON objects."""

    name: str
    model: str

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Answer ``request``, or raise :class:`LLMError`."""


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_object(text: str, required_keys: tuple[str, ...]) -> dict[str, Any]:
    """Extract a JSON object from model output.

    Models wrap JSON in prose or code fences even when told not to, so the
    tolerant path is taken deliberately. What is *not* tolerated is a missing
    required key: silently defaulting one would fabricate a judgement, which is
    the specific failure this whole design exists to prevent.
    """
    candidate = text.strip()

    fenced = _JSON_BLOCK.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(
            f"Model output was not valid JSON: {exc}. Received: {text[:200]!r}"
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMResponseError(f"Expected a JSON object, got {type(parsed).__name__}")

    missing = [key for key in required_keys if key not in parsed]
    if missing:
        raise LLMResponseError(
            f"Model response is missing required keys {missing}. "
            "Refusing to substitute defaults, because a fabricated judgement is "
            "worse than no judgement."
        )

    return parsed
