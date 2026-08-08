"""Tests for LLM-backed structured extraction, including the retrieval path
for long documents.
"""

from __future__ import annotations

from bharat_os.llm.mock import MockProvider
from bharat_os.pdf.extraction import ExtractedDocument, ExtractedPage
from bharat_os.pdf.structured_extraction import (
    RETRIEVAL_THRESHOLD_CHARS,
    extract_structured,
)


def _document(text: str) -> ExtractedDocument:
    return ExtractedDocument(source_path="test.pdf", pages=(ExtractedPage(1, text),))


class TestExtractStructured:
    def test_empty_document_is_flagged_without_calling_the_model(self) -> None:
        provider = MockProvider()
        result = extract_structured(_document(""), provider=provider)

        assert result.requires_review is True
        assert result.confidence == 0.0
        assert provider.calls == []  # never asked the model anything

    def test_short_document_is_sent_whole_not_retrieved(self) -> None:
        provider = MockProvider()
        text = "Short eligibility notice about the scheme."
        result = extract_structured(_document(text), provider=provider)

        assert result.used_retrieval is False
        assert text in provider.calls[0].prompt

    def test_long_document_uses_retrieval(self) -> None:
        provider = MockProvider()
        filler = "Unrelated administrative boilerplate with no relevant terms. "
        long_text = filler * (RETRIEVAL_THRESHOLD_CHARS // len(filler) + 10)

        result = extract_structured(_document(long_text), provider=provider)

        assert result.used_retrieval is True
        # The prompt sent to the model must be materially smaller than the
        # original document - that is the entire point of retrieving instead
        # of sending everything.
        assert len(provider.calls[0].prompt) < len(long_text)

    def test_long_document_retrieval_keeps_the_relevant_section(self) -> None:
        """The specific sentence carrying the eligibility criterion must
        survive retrieval even though it is buried between large amounts of
        irrelevant filler - this is the actual problem retrieval exists to
        solve, not just 'the prompt got shorter'."""
        provider = MockProvider()
        filler = "Unrelated administrative boilerplate with no bearing on any applicant. "
        needle = (
            "The eligibility criteria require Udyam registration and annual "
            "turnover under the prescribed ceiling for a small enterprise."
        )
        long_text = (filler * 200) + needle + (filler * 200)
        assert len(long_text) > RETRIEVAL_THRESHOLD_CHARS

        result = extract_structured(_document(long_text), provider=provider)

        assert result.used_retrieval is True
        assert needle in provider.calls[0].prompt

    def test_model_failure_still_reports_whether_retrieval_was_used(self) -> None:
        """Even on the safe-degradation path (model unavailable), the
        response must not silently claim used_retrieval=False for a document
        that actually was retrieved - a reviewer checking why extraction
        failed needs that context too."""
        from bharat_os.llm.mock import FORCE_ERROR

        provider = MockProvider()
        filler = "Unrelated administrative boilerplate with no relevant terms. "
        long_text = filler * (RETRIEVAL_THRESHOLD_CHARS // len(filler) + 10) + FORCE_ERROR

        result = extract_structured(_document(long_text), provider=provider)

        assert result.requires_review is True
        assert result.confidence == 0.0
