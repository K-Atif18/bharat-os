"""Extracting text from gazette notifications and ministry circulars.

Text extraction only. Turning that text into a structured candidate scheme
revision is a judgement call and belongs to
:mod:`bharat_os.pdf.structured_extraction`, which routes through an LLM and — like
everything downstream of a crawler — ends in the verification queue, never in the
live corpus directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PDFExtractionError(RuntimeError):
    """A PDF could not be read or contained no extractable text."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    source_path: str
    pages: tuple[ExtractedPage, ...]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)

    @property
    def is_empty(self) -> bool:
        """True when no page yielded text — typically a scanned image with no OCR.

        Distinguished from an extraction error: the PDF opened fine, it simply has
        nothing this pipeline can read, which needs a different remedy (OCR) than
        a corrupt file does.
        """
        return not any(page.text.strip() for page in self.pages)


def extract_text(path: Path | str) -> ExtractedDocument:
    """Extract text from a PDF, page by page.

    Uses pdfplumber, which handles the tabular layouts common in government
    circulars (benefit tables, document checklists) better than a plain text
    dump would.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise PDFExtractionError(
            "pdfplumber is not installed. Install it with `pip install pdfplumber`."
        ) from exc

    source_path = str(path)
    try:
        with pdfplumber.open(source_path) as pdf:
            pages = tuple(
                ExtractedPage(page_number=index + 1, text=page.extract_text() or "")
                for index, page in enumerate(pdf.pages)
            )
    except Exception as exc:  # pdfplumber wraps pdfminer's varied exception types.
        raise PDFExtractionError(f"Could not read {source_path}: {exc}") from exc

    return ExtractedDocument(source_path=source_path, pages=pages)
