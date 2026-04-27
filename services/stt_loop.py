import logging
import threading
import time
from collections.abc import Callable

from clients import FasterWhisperSTTClient
from logging_config import log_extra

logger = logging.getLogger(__name__)


class STTLoop:
    def __init__(
        self,
        stt_client: FasterWhisperSTTClient | None,
        process_command: Callable[[str], str],
        chunk_duration: float,
    ) -> None:
        self._stt_client = stt_client
        self._process_command = process_command
        self._chunk_duration = chunk_duration
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._stt_client is None or self._thread is not None:
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        if self._stt_client is None:
            return

        while not self._stop_event.is_set():
            try:
                logger.info(
                    "Listening for %.1fs... speak now",
                    self._chunk_duration,
                    extra=log_extra("STT"),
                )
                transcript = self._stt_client.listen_and_transcribe_once(
                    duration_sec=self._chunk_duration,
                )
                if not transcript:
                    continue

                logger.info("STT_TEXT: %s", transcript, extra=log_extra("APP"))
                self._process_command(transcript)
            except Exception:
                logger.exception("STT worker loop failed", extra=log_extra("APP"))
                time.sleep(0.5)