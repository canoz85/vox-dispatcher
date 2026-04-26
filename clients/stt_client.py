import logging
import importlib
import os
import tempfile
import wave
from typing import Any

from logging_config import log_extra

logger = logging.getLogger(__name__)


class FasterWhisperSTTClient:
    def __init__(
        self,
        model_size: str = "small.en",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "en",
        beam_size: int = 1,
        vad_filter: bool = True,
        sample_rate: int = 16_000,
        channels: int = 1,
    ):
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.sample_rate = sample_rate
        self.channels = channels
        try:
            whisper_module = importlib.import_module("faster_whisper")
            whisper_model_cls = getattr(whisper_module, "WhisperModel")
        except Exception as exc:  # pragma: no cover - import guard for optional dependency
            raise RuntimeError(
                "Missing dependency 'faster-whisper'. Install with: pip install faster-whisper"
            ) from exc

        self._model = whisper_model_cls(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type,
        )

    def _record_wav(self, duration_sec: float) -> str:
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0")

        try:
            np = importlib.import_module("numpy")
        except Exception as exc:  # pragma: no cover - import guard for optional dependency
            raise RuntimeError("Missing dependency 'numpy'. Install with: pip install numpy") from exc

        try:
            sd = importlib.import_module("sounddevice")
        except Exception as exc:  # pragma: no cover - import guard for optional dependency
            raise RuntimeError(
                "Missing dependency 'sounddevice'. Install with: pip install sounddevice"
            ) from exc

        total_samples = int(self.sample_rate * duration_sec)
        audio = sd.rec(
            total_samples,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        sd.wait()
        mono = np.squeeze(audio)

        temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp.name
        temp.close()

        with wave.open(temp_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(mono.tobytes())

        return temp_path

    def transcribe_file(self, audio_path: str) -> str:
        segments, info = self._model.transcribe(
            audio_path,
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        logger.info(
            "Transcribed language=%s duration=%.2fs text_chars=%s",
            getattr(info, "language", self.language),
            float(getattr(info, "duration", 0.0) or 0.0),
            len(text),
            extra=log_extra("STT"),
        )
        return text

    def listen_and_transcribe_once(self, duration_sec: float = 3.0, min_chars: int = 2) -> str:
        audio_path = self._record_wav(duration_sec)
        try:
            text = self.transcribe_file(audio_path)
            if len(text.strip()) < min_chars:
                return ""
            return text
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
