"""Accent substitution tables and custom vocabularies."""

from typing import Dict, List, Set, Tuple

# Pre-built phonetic substitution tables for common accent families.
ACCENT_TABLES: dict[str, list[tuple[str, str]]] = {
    "east_african": [
        (r"\bde\b", "the"),
        (r"\bdis\b", "this"),
        (r"\bdat\b", "that"),
        (r"\bden\b", "then"),
    ],
    "indian": [
        (r"\bfroyd\b", "fried"),
    ],
    "west_african": [
        (r"\babi\b", "above"),
    ],
    "british": [],
    "american": [],
}

# Regex-based custom mappings applied in text_utils.
CUSTOM_MAPPINGS: dict[str, str] = {
    r"\bta\b": "to",
    r"\bgonna\b": "going to",
    r"\bwanna\b": "want to",
}

# Short words that are real and should NOT be glued during BPE healing.
REAL_SHORT_WORDS: set[str] = {
    "a", "i", "an", "as", "at", "be", "by", "do", "go", "he", "if", "in",
    "is", "it", "me", "my", "no", "of", "on", "or", "ox", "pi", "so", "to",
    "up", "us", "we",
}

# Domain-specific vocabulary that bypasses spell-checking / splitting.
CUSTOM_VOCAB: set[str] = set()
