"""Stripping HTML down to plain text for LLM extraction.

Deliberately not a full HTML parser or a new dependency: government pages
handled here are simple content pages, not applications, and the only thing
this needs to do is remove markup noise (script/style blocks, tags) so an LLM
reads prose instead of angle brackets. A mis-stripped tag produces slightly
noisier text, not a wrong extraction — the LLM step downstream already
degrades safely (see :func:`bharat_os.pdf.structured_extraction.extract_structured`),
so this does not need to be perfect, only good enough to feed it.
"""

from __future__ import annotations

import re

_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")

_ENTITY_REPLACEMENTS = {
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&rsquo;": "'",
    "&ndash;": "-",
    "&mdash;": "-",
}


def html_to_text(html: str) -> str:
    """Reduce HTML to readable plain text, good enough for LLM extraction."""
    text = _SCRIPT_OR_STYLE.sub(" ", html)
    text = _TAG.sub("\n", text)
    for entity, replacement in _ENTITY_REPLACEMENTS.items():
        text = text.replace(entity, replacement)
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()
