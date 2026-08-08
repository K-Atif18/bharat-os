"""A deterministic provider that makes no network calls.

Used by the entire test suite and available as a demo fallback. It is not a stub
that returns a fixed blob: it produces plausible, varied, schema-valid judgements
derived deterministically from the prompt, so tests exercise real parsing and
aggregation paths rather than a happy-path constant.

Determinism comes from hashing the prompt, so the same question always yields the
same answer, and different questions yield different ones.
"""

from __future__ import annotations

import hashlib
from typing import Any

from bharat_os.llm.base import LLMProvider, LLMRequest, LLMResponse

#: Sentinel prompt fragments that force a specific failure, so error handling can
#: be tested without monkeypatching internals.
FORCE_MALFORMED = "[[force-malformed]]"
FORCE_MISSING_KEY = "[[force-missing-key]]"
FORCE_ERROR = "[[force-error]]"


class MockProvider(LLMProvider):
    """Deterministic, offline, free."""

    name = "mock"
    model = "mock-deterministic-v1"

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        from bharat_os.llm.base import LLMError

        self.calls.append(request)

        if FORCE_ERROR in request.prompt:
            raise LLMError("Simulated provider failure")

        if FORCE_MALFORMED in request.prompt:
            return LLMResponse(
                data={},
                provider=self.name,
                model=self.model,
                prompt=request.prompt,
                raw_text="I'm afraid I can't answer that in JSON.",
            )

        digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100

        # The mock has to answer two distinct shapes of question: eligibility
        # judgements and narrative drafting. Dispatching on required_keys, rather
        # than always returning the judgement shape, is what let the "returns text
        # for narrative fields" path go untested until it broke against a live
        # server — the fix is here, and the regression test is in test_drafting.py.
        if request.required_keys == ("text",):
            data: dict[str, Any] = {"text": self._narrative(bucket)}
        else:
            data = self._judgement(bucket, omit_confidence=FORCE_MISSING_KEY in request.prompt)

        return LLMResponse(
            data=data,
            provider=self.name,
            model=self.model,
            prompt=request.prompt,
            raw_text=str(data),
            usage={"prompt_tokens": len(request.prompt) // 4, "completion_tokens": 64},
        )

    def _narrative(self, bucket: int) -> str:
        """Deterministic mock prose for narrative drafting fields."""
        openings = (
            "This business operates in an early stage, focused on building a "
            "product suited to its declared sector.",
            "The applicant is working on a technology-oriented offering "
            "consistent with the profile details supplied.",
            "Based on the information provided, this is a young enterprise "
            "developing its core product.",
        )
        return openings[bucket % len(openings)]

    def _judgement(self, bucket: int, *, omit_confidence: bool) -> dict[str, Any]:
        """Spread outcomes across the range so aggregation is exercised properly."""
        if bucket < 40:
            verdict, confidence = "likely_met", 0.55 + (bucket % 30) / 100
        elif bucket < 60:
            verdict, confidence = "uncertain", 0.30 + (bucket % 20) / 100
        elif bucket < 80:
            verdict, confidence = "likely_unmet", 0.45 + (bucket % 25) / 100
        else:
            verdict, confidence = "uncertain", 0.20 + (bucket % 15) / 100

        judgement: dict[str, Any] = {
            "verdict": verdict,
            "confidence": round(min(confidence, 0.95), 2),
            "reasoning": (
                "Deterministic mock judgement. The profile describes an early-stage "
                "technology business, which is consistent with the criterion, but the "
                "profile does not contain the product detail needed to be certain."
            ),
            "evidence_that_would_strengthen": [
                "A product description covering what is technically novel",
                "Evidence of customer traction, such as pilot users or revenue",
            ],
        }
        if omit_confidence:
            del judgement["confidence"]
        return judgement
