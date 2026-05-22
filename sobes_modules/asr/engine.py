# sobes_modules/asr/engine.py
import json
import logging
from sobes_core.messages import AsrPartial, AsrFinal

logger = logging.getLogger(__name__)

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class AsrEngine:
    def __init__(self, config, model_path: str):
        self.config = config
        self.model_path = model_path
        self.sample_rate = config.sample_rate
        self._callback = None
        self._model = None
        self._recognizer = None

    def initialize(self):
        if not VOSK_AVAILABLE:
            raise RuntimeError("Vosk not installed")
        self._model = vosk.Model(self.model_path)
        self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        self._recognizer.SetWords(False)

    def set_callback(self, callback):
        self._callback = callback

    def _emit(self, message):
        if self._callback:
            self._callback(message)

    def process_chunk(self, audio_data: bytes, timestamp: float):
        if self._recognizer is None:
            logger.warning("Recognizer not initialized, skipping chunk")
            return

        if self._recognizer.AcceptWaveform(audio_data):
            final_text = json.loads(self._recognizer.FinalResult()).get("text", "")
            if final_text.strip():
                self._emit(AsrFinal(text=final_text, timestamp=timestamp, speaker="unknown"))
        else:
            partial_text = json.loads(self._recognizer.PartialResult()).get("partial", "")
            if partial_text.strip():
                self._emit(AsrPartial(text=partial_text, is_partial=True, timestamp=timestamp))

    def reset(self):
        if self._model and VOSK_AVAILABLE:
            try:
                self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
                self._recognizer.SetWords(False)
            except Exception:
                logger.debug("Failed to re-create KaldiRecognizer during reset")
        elif self._model:
            logger.debug("Vosk not available, skipping recognizer reset")
