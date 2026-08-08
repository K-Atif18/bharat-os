"""Lightweight retrieval over long documents, for grounding LLM extraction.

A gazette notification or a long ministry page can run to many pages. Sending
the whole thing to the model either exceeds a sane prompt budget or forces a
truncation that can silently cut off the exact section — eligibility criteria,
benefit amounts, document lists — that actually matters. This module retrieves
only the passages relevant to that kind of content, so what gets sent to the
model is small and on-topic instead of large and diluted.

Deliberately not embedding-based. Adding a vector store or an embedding model
dependency is a bigger commitment than this problem needs: a government
notice's relevant sections are reliably signalled by the vocabulary they use
("eligibility", "shall be entitled to", "documents required", ...), and a
plain keyword/overlap score finds them well enough. If a harder retrieval
problem shows up later — near-duplicate paraphrasing, no shared vocabulary —
that is the point to revisit this decision, not before.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Roughly one paragraph or a few sentences per chunk. Small enough that a
#: chunk is usually about one topic, large enough that a sentence is not
#: separated from the context it needs to be read correctly.
_CHUNK_TARGET_CHARS = 800
_MIN_CHUNK_CHARS = 200

#: Vocabulary associated with the content this pipeline actually cares about.
#: Deliberately over-inclusive — a chunk matching none of these is unlikely to
#: contain an eligibility criterion, a benefit figure or a document
#: requirement, which is the only content this system ever extracts.
_RELEVANCE_TERMS = (
    "eligib", "eligible", "criteria", "criterion", "qualify", "qualifies",
    "shall be entitled", "benefit", "subsidy", "grant", "loan", "assistance",
    "document", "certificate", "registration", "application", "deadline",
    "window", "last date", "turnover", "employee", "udyam", "dpiit", "msme",
    "startup", "scheme", "amendment", "revised", "w.e.f", "notification",
    "guideline",
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


def chunk_text(text: str) -> list[Chunk]:
    """Split text into roughly paragraph-sized chunks, on sentence boundaries.

    Splitting on sentence boundaries rather than a fixed character offset
    avoids cutting a sentence in half at a chunk edge, which would otherwise
    make the relevance score for that sentence meaningless in both halves.
    """
    sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]
    if not sentences:
        return []

    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        current.append(sentence)
        current_len += len(sentence) + 1
        if current_len >= _CHUNK_TARGET_CHARS:
            chunks.append(Chunk(index=len(chunks), text=" ".join(current)))
            current = []
            current_len = 0

    if current:
        joined = " ".join(current)
        # A trailing sliver shorter than the minimum is more useful merged
        # into the previous chunk than left to score (and likely lose) on
        # its own.
        if chunks and len(joined) < _MIN_CHUNK_CHARS:
            previous = chunks.pop()
            chunks.append(Chunk(index=previous.index, text=f"{previous.text} {joined}"))
        else:
            chunks.append(Chunk(index=len(chunks), text=joined))

    return chunks


def _relevance_score(chunk_text_lower: str) -> int:
    """Count of distinct relevance terms present in the chunk.

    A count, not a fraction or a weighted score: this only needs to rank
    chunks against each other well enough to pick the useful ones, not to
    produce a calibrated probability the way the LLM confidence scores do.
    """
    return sum(1 for term in _RELEVANCE_TERMS if term in chunk_text_lower)


def retrieve_relevant_chunks(
    text: str,
    *,
    max_chunks: int = 6,
) -> list[Chunk]:
    """The most relevant chunks of ``text``, most relevant first.

    Falls back to returning the first ``max_chunks`` chunks in document order
    if nothing scores above zero — a document that mentions none of the
    expected vocabulary is unusual enough that guessing which part matters
    would be worse than just preserving the original reading order and
    letting the model's own judgement (and confidence score) reflect that
    this document was a poor match.
    """
    chunks = chunk_text(text)
    if not chunks:
        return []

    scored = [(chunk, _relevance_score(chunk.text.lower())) for chunk in chunks]
    if all(score == 0 for _, score in scored):
        return chunks[:max_chunks]

    scored.sort(key=lambda pair: pair[1], reverse=True)
    top = [chunk for chunk, score in scored[:max_chunks] if score > 0]
    # Restore original document order among the selected chunks: a reviewer
    # or the model reading "clause 4 ... clause 2 ... clause 7" out of order
    # is more likely to misread a cross-reference than one reading a subset
    # in its original sequence.
    top.sort(key=lambda chunk: chunk.index)
    return top
