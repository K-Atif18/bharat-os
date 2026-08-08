"""Tests for the lightweight retrieval used to ground LLM extraction."""

from __future__ import annotations

from bharat_os.pdf.retrieval import chunk_text, retrieve_relevant_chunks


class TestChunkText:
    def test_empty_text_yields_no_chunks(self) -> None:
        assert chunk_text("") == []

    def test_short_text_is_a_single_chunk(self) -> None:
        chunks = chunk_text("A single short sentence.")
        assert len(chunks) == 1
        assert chunks[0].text == "A single short sentence."

    def test_long_text_is_split_into_multiple_chunks(self) -> None:
        sentence = "The eligibility criteria for this scheme are described here. "
        long_text = sentence * 40  # well past the chunk target size
        chunks = chunk_text(long_text)
        assert len(chunks) > 1

    def test_chunks_are_indexed_in_order(self) -> None:
        sentence = "This is a filler sentence about the scheme. "
        long_text = sentence * 40
        chunks = chunk_text(long_text)
        assert [c.index for c in chunks] == list(range(len(chunks)))

    def test_a_trailing_sliver_is_merged_rather_than_left_alone(self) -> None:
        """A short leftover at the end should not become its own chunk below
        the minimum size - it is merged into the previous one."""
        sentence = "Filler sentence about the eligibility criteria here. "
        long_text = sentence * 30 + "Short tail."
        chunks = chunk_text(long_text)
        assert all(c.char_count >= 200 or c.index == 0 for c in chunks)
        assert "Short tail." in chunks[-1].text

    def test_no_sentence_is_split_across_a_chunk_boundary(self) -> None:
        text = (
            "First sentence about eligibility criteria for the scheme overall. "
            "Second sentence about the required documents for applicants. "
        ) * 20
        chunks = chunk_text(text)
        for chunk in chunks:
            assert chunk.text.strip().endswith((".", "!", "?"))


class TestRetrieveRelevantChunks:
    def test_empty_text_returns_nothing(self) -> None:
        assert retrieve_relevant_chunks("") == []

    def test_prefers_chunks_mentioning_eligibility_vocabulary(self) -> None:
        text = (
            "This document begins with a long unrelated preamble about the "
            "history of the ministry and its founding in a previous decade, "
            "with no bearing on any applicant whatsoever, filler filler filler. "
            "The eligibility criteria require the applicant to hold a valid "
            "Udyam registration and an annual turnover under the prescribed "
            "ceiling for a micro or small enterprise. "
            "This document concludes with more unrelated administrative "
            "boilerplate about office addresses and filing procedures unrelated "
            "to eligibility whatsoever, filler filler filler filler filler."
        )
        chunks = retrieve_relevant_chunks(text, max_chunks=1)
        assert len(chunks) == 1
        assert "eligibility" in chunks[0].text.lower()

    def test_returns_at_most_max_chunks(self) -> None:
        sentence = "The eligibility criteria and required documents are listed below. "
        long_text = sentence * 100
        chunks = retrieve_relevant_chunks(long_text, max_chunks=3)
        assert len(chunks) <= 3

    def test_selected_chunks_preserve_original_document_order(self) -> None:
        text = (
            "Eligibility criteria are described in this first relevant chunk "
            "about the scheme and its applicants and requirements overall. "
            + ("Unrelated filler paragraph with no relevant vocabulary at all. " * 15)
            + "Required documents are described in this later relevant chunk "
            "about the scheme and its applicants and requirements overall."
        )
        chunks = retrieve_relevant_chunks(text, max_chunks=5)
        indices = [c.index for c in chunks]
        assert indices == sorted(indices)

    def test_falls_back_to_document_order_when_nothing_scores(self) -> None:
        """A document that matches none of the expected vocabulary should not
        have chunks reordered by a meaningless zero-vs-zero comparison."""
        text = ("Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 40)
        chunks = retrieve_relevant_chunks(text, max_chunks=3)
        assert len(chunks) == 3
        assert [c.index for c in chunks] == [0, 1, 2]
