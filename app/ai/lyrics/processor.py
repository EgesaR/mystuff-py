"""Lyrics post-processing: melisma collapse, structural annotation."""

import re

_MELISMA_RE = re.compile(r"(.)\1{3,}")
_BREATH_RE = re.compile(r"\*huh\*", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")

_STRUCTURE_TAGS = (
    (("[chorus", "(chorus"), "\nCHORUS:"),
    (("[verse", "(verse"), "\nVERSE:"),
    (("[bridge", "(bridge"), "\nBRIDGE:"),
)


def clean_lyric_line(text: str) -> str:
    """Lightweight single-line cleanup for live interim display."""
    if not text:
        return ""
    # Collapse repeated characters (melisma / held notes)
    text = _MELISMA_RE.sub(r"\1\1", text)
    # Remove breath tokens
    text = _BREATH_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _structure_tag(lower_line: str) -> str | None:
    for prefixes, tag in _STRUCTURE_TAGS:
        if lower_line.startswith(prefixes):
            return tag
    return None


def process_lyrics(text: str, structure: bool = True) -> str:
    """Final lyrics pipeline: melisma cleanup + optional structural blocks."""
    if not text:
        return ""
    lines = [clean_lyric_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not structure:
        return "\n".join(lines)

    out: list[str] = []
    for line in lines:
        tag = _structure_tag(line.lower())
        out.append(tag if tag is not None else line)
    return "\n".join(out).strip()
