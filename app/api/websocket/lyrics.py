"""Lyrics / singing transcription WebSocket handler."""

import logging

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ai.nlp.text_utils import fine_tune_final, fine_tune_text
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger("app")
router = APIRouter()


class LyricsRecognizerState:
    """Holds the lazy-loaded lyrics recognizer instance."""

    def __init__(self) -> None:
        self._instance = None

    def get(self):
        """Return the lazily-loaded lyrics recognizer instance."""
        if self._instance is None:
            self._instance = TranscriptionService.build_lyrics_recogniser()
        return self._instance


# Module-level state holder
state = LyricsRecognizerState()


@router.websocket("/ws/lyrics")
async def ws_lyrics(websocket: WebSocket) -> None:
    """Musical / lyrics transcription WebSocket handler."""
    recogniser = state.get()
    await websocket.accept()
    stream = recogniser.create_stream()
    last_interim: str = ""

    logger.info("lyrics: client connected")

    try:
        while True:
            message = await websocket.receive_bytes()

            samples = (
                np.frombuffer(message, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            stream.accept_waveform(16000, waveform=samples)

            while recogniser.is_ready(stream):
                recogniser.decode_stream(stream)

            result = recogniser.get_result(stream)
            raw_text: str = (
                result if isinstance(result, str)
                else getattr(result, "text", "")
            )

            if recogniser.is_endpoint(stream):
                final = fine_tune_final(raw_text.strip(), mode="lyrics")
                if final:
                    await websocket.send_text(f"__FINAL__:{final}")
                recogniser.reset(stream)
                last_interim = ""
            else:
                cleaned = fine_tune_text(raw_text, mode="lyrics")
                if cleaned != last_interim:
                    await websocket.send_text(cleaned)
                    last_interim = cleaned

    except (WebSocketDisconnect, RuntimeError, ConnectionError):
        logger.info("lyrics: client disconnected")
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        logger.exception("lyrics: unexpected error — %s", exc)
