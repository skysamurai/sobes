# sobes_core/config.py
import os
import platform


class Config:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or self._default_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)

        self.zmq_session_port = int(os.getenv("SOBES_ZMQ_SESSION_PORT", "5555"))
        self.zmq_capturer_port = int(os.getenv("SOBES_ZMQ_CAPTURER_PORT", "5556"))
        self.zmq_asr_port = int(os.getenv("SOBES_ZMQ_ASR_PORT", "5557"))
        self.zmq_prompt_port = int(os.getenv("SOBES_ZMQ_PROMPT_PORT", "5558"))
        self.zmq_ui_port = int(os.getenv("SOBES_ZMQ_UI_PORT", "5559"))

        default_model = "models/vosk-model-small-ru-0.22"
        self.vosk_model_path = os.getenv("SOBES_VOSK_MODEL_PATH", default_model)
        self.sample_rate = int(os.getenv("SOBES_SAMPLE_RATE", "16000"))
        self.chunk_duration_ms = int(os.getenv("SOBES_CHUNK_DURATION_MS", "500"))
        self.channels = 1
        self.sample_width = 2

        self.chroma_dir = os.path.join(self.data_dir, "chroma")
        self.sqlite_path = os.path.join(self.data_dir, "sobes.db")
        self.embedding_model = os.getenv(
            "SOBES_EMBEDDING_MODEL",
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.script_confidence_threshold = float(
            os.getenv("SOBES_CONFIDENCE_THRESHOLD", "0.75")
        )

    @staticmethod
    def _default_data_dir():
        if platform.system() == "Windows":
            base = os.getenv("APPDATA", os.path.expanduser("~"))
        else:
            base = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(base, "sobes")
