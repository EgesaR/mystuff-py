"""Lyrics post-processing: melisma collapse, structural annotation."""

import re


def clean_lyric_line(text: str) -> str:
    """Lightweight single-line cleanup for live interim display."""
    if not text:
        return ""
    # Collapse repeated characters (melisma / held notes)
    text = re.sub(r"(.)\1{3,}", r"\1\1", text)
    # Remove breath tokens
    text = re.sub(r"\*huh\*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def process_lyrics(text: str, structure: bool = True) -> str:
    """Final lyrics pipeline: melisma cleanup + optional structural blocks."""
    if not text:
        return ""
    lines = [clean_lyric_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not structure:
        return "\n".join(lines)

    # Naïve structural annotation
    out: list[str] = []
    for line in lines:
        lower = line.lower()
        if lower.startswith("[chorus") or lower.startswith("(chorus"):
            out.append(f"\nCHORUS:")
        elif lower.startswith("[verse") or lower.startswith("(verse"):
            out.append(f"\nVERSE:")
        elif lower.startswith("[bridge") or lower.startswith("(bridge"):
            out.append(f"\nBRIDGE:")
        else:
            out.append(line)
    return "\n".join(out).strip()
