"""Utility for generating URL-safe slugs from titles."""
import re
import unicodedata


def slugify(value: str) -> str:
    """Convert a string into a lowercase, hyphenated, URL-safe slug.

    Args:
        value (str): Source string, typically a title.

    Returns:
        str: URL-safe slug.
    """
    value = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)
