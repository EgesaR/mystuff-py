"""app/services/transcription_service.py
Builds and manages sherpa-onnx recogniser instances.
Also handles accent-profile REST operations (learn / forget / inspect).

The recognisers are NOT instantiated at import time — they are lazy-loaded
on first WebSocket connection so the app starts instantly even without the
AI model files on disk (useful for testing other routes).
"""
import logging
from pathlib import Path
from typing import Any

from app.ai.accent.learner import get_learner

logger = logging.getLogger("app")

# Path to the sherpa-onnx streaming Zipformer model
_MODEL_DIR = Path(
    "app/ai/models/sherpa-onnx-streaming-zipformer-en-2023-06-26")


def _build_recogniser(
    rule1_silence: float = 2.4,
    rule2_silence: float = 1.2,
    utterance_length: int = 300,
) -> Any:
    """
    Build a sherpa_onnx OnlineRecognizer with the given silence thresholds.
    Raises ImportError if sherpa_onnx is not installed.
    Raises FileNotFoundError if the model files are missing.
    """
    try:
        import sherpa_onnx  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "sherpa_onnx is not installed. "
            "Run: pip install sherpa-onnx"
        ) from exc

    model_dir = str(_MODEL_DIR)

    return sherpa_onnx.OnlineRecognizer.from_transducer(
        encoder=f"{model_dir}/encoder-epoch-99-avg-1-chunk-16-left-128.onnx",
        decoder=f"{model_dir}/decoder-epoch-99-avg-1-chunk-16-left-128.onnx",
        joiner=f"{model_dir}/joiner-epoch-99-avg-1-chunk-16-left-128.onnx",
        tokens=f"{model_dir}/tokens.txt",
        num_threads=4,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=rule1_silence,
        rule2_min_trailing_silence=rule2_silence,
        rule3_min_utterance_length=utterance_length,
        provider="cpu",
        debug=False,
    )


class TranscriptionService:
    """Factory + accent-profile management for the transcription pipeline."""

    @staticmethod
    def build_speech_recogniser() -> Any:
        """
        Recogniser tuned for standard speech dictation.
        rule1=2.4s, rule2=1.2s — normal conversational pauses.
        """
        logger.info("Loading speech recogniser from %s …", _MODEL_DIR)
        return _build_recogniser(
            rule1_silence=2.4,
            rule2_silence=1.2,
            utterance_length=300,
        )

    @staticmethod
    def build_lyrics_recogniser() -> Any:
        """
        Recogniser tuned for singing / lyrics:
        - Longer silences: singers hold notes and breathe between phrases
        - Shorter utterance length: lyric lines are naturally shorter
        """
        logger.info("Loading lyrics recogniser from %s …", _MODEL_DIR)
        return _build_recogniser(
            rule1_silence=3.8,
            rule2_silence=2.2,
            utterance_length=150,
        )

    # ── Accent profile management ─────────────────────────────────────────────

    @staticmethod
    def submit_correction(raw: str, corrected: str) -> dict[str, Any]:
        """
        Learn a correction pair and return a summary of the updated profile.
        Called by the /accent/correct REST endpoint.
        """
        learner = get_learner()
        count = learner.learn(raw, corrected)
        rules = learner.learned_rules
        return {
            "pairs_extracted": count,
            "total_active_rules": len(rules),
            "message": (
                f"Extracted {count} correction pair(s). "
                f"{len(rules)} rule(s) now active."
            ),
        }

    @staticmethod
    def get_profile() -> dict[str, Any]:
        """Return the full accent profile for inspection."""
        learner = get_learner()
        # Safely read protected _builtin map using getattr to satisfy strict linters
        builtin_rules = getattr(learner, "_builtin", {})

        return {
            "builtin_rules": len(builtin_rules),
            "learned_corrections": learner.export_learned(),
            "active_rules": learner.learned_rules,
            "summary": learner.summary(),
        }

    @staticmethod
    def forget_correction(raw_token: str) -> dict[str, Any]:
        """Remove all learned corrections for a specific raw token."""
        get_learner().forget(raw_token)
        return {"removed": raw_token}
