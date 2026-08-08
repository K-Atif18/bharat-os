"""Turning extracted PDF text into a candidate scheme revision.

A gazette notification or circular describes a scheme change in prose. This module
asks a language model to structure that prose into the same shape
:class:`bharat_os.schemas.scheme.SchemeVersionIn` expects — but the result is a
*candidate*, staged in :class:`PendingRevision`. It is never passed to
:mod:`bharat_os.seed.loader` directly. A confidence below the review threshold is
flagged and must never bypass a human, no matter how confident the model sounds.
"""

from __future__ import annotations

from dataclasses import dataclass

from bharat_os.llm import LLMError, LLMRequest, LLMResponseError, get_provider
from bharat_os.llm.base import LLMProvider
from bharat_os.pdf.extraction import ExtractedDocument

#: Below this, extraction is flagged for review regardless of what the model
#: claims — mirrors the threshold used for soft-criteria judgements, because the
#: same principle applies: a confident-sounding wrong extraction is worse than an
#: extraction that admits uncertainty.
REVIEW_THRESHOLD = 0.7

REQUIRED_KEYS = ("scheme_name", "summary_of_change", "confidence", "extracted_fields")

SYSTEM_PROMPT = """\
You extract structured information about an Indian government scheme from the \
text of a gazette notification or ministry circular.

Rules:
- Extract only what the text actually states. Do not infer values it does not \
contain.
- If the document changes only some fields (for example, only a benefit ceiling), \
extract only those; leave everything else out of extracted_fields.
- confidence reflects how clearly the text supports your extraction — not how \
important the change is. A clearly worded small change should score higher than \
an ambiguous large one.
- This output goes to a human reviewer before anything is published. Flag \
ambiguity honestly rather than resolving it yourself.

Reply with a single JSON object:
{
  "scheme_name": "<name of the scheme this document concerns, as best determined>",
  "summary_of_change": "<one or two sentences, for a human reviewer>",
  "confidence": <0 to 1>,
  "extracted_fields": {<field name>: <value>, ...}
}\
"""


@dataclass(frozen=True)
class ExtractionResult:
    scheme_name: str
    summary_of_change: str
    confidence: float
    extracted_fields: dict
    requires_review: bool
    provider: str
    model: str


def extract_structured(
    document: ExtractedDocument,
    *,
    provider: LLMProvider | None = None,
) -> ExtractionResult:
    """Ask the model to structure a PDF's content, degrading safely on failure.

    On any failure this returns a result with ``requires_review=True`` and empty
    fields rather than raising — the calling pipeline stage still needs a
    :class:`PendingRevision` row to queue for a human, even when automated
    extraction could not produce one.
    """
    active_provider = provider or get_provider()

    if document.is_empty:
        return ExtractionResult(
            scheme_name="unknown",
            summary_of_change="No extractable text (likely a scanned image).",
            confidence=0.0,
            extracted_fields={},
            requires_review=True,
            provider=active_provider.name,
            model=active_provider.model,
        )

    request = LLMRequest(
        system=SYSTEM_PROMPT,
        prompt=f"Document text:\n\n{document.full_text[:12_000]}",
        required_keys=REQUIRED_KEYS,
        max_output_tokens=2048,
    )

    try:
        response = active_provider.complete(request)
        confidence = float(response.data["confidence"])
        if not 0.0 <= confidence <= 1.0:
            raise LLMResponseError(f"confidence {confidence} outside [0, 1]")
        fields = response.data["extracted_fields"]
        if not isinstance(fields, dict):
            raise LLMResponseError("extracted_fields was not an object")
    except (LLMError, KeyError, ValueError) as exc:
        return ExtractionResult(
            scheme_name="unknown",
            summary_of_change=f"Automated extraction failed: {exc}",
            confidence=0.0,
            extracted_fields={},
            requires_review=True,
            provider=active_provider.name,
            model=active_provider.model,
        )

    return ExtractionResult(
        scheme_name=str(response.data["scheme_name"]),
        summary_of_change=str(response.data["summary_of_change"]),
        confidence=confidence,
        extracted_fields=fields,
        requires_review=confidence < REVIEW_THRESHOLD,
        provider=response.provider,
        model=response.model,
    )
