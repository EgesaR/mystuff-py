"""app/ai/lyrics/cleaner.py
Lightweight single-line cleanup for live interim display during lyrics transcription.
Re-exports from processor to keep the module boundary clean.
"""
from app.ai.lyrics.processor import clean_lyric_line

__all__ = ["clean_lyric_line"]
