# tests/test_config.py
import os
from sobes_core.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.zmq_session_port == 5555
    assert cfg.zmq_capturer_port == 5556
    assert cfg.zmq_asr_port == 5557
    assert cfg.zmq_prompt_port == 5558
    assert cfg.zmq_ui_port == 5559
    assert cfg.vosk_model_path == "models/vosk-model-small-ru-0.22"
    assert cfg.sample_rate == 16000
    assert cfg.chunk_duration_ms == 500
    assert "sobes" in cfg.data_dir


def test_config_from_env():
    os.environ["SOBES_VOSK_MODEL_PATH"] = "/custom/vosk/model"
    os.environ["SOBES_SAMPLE_RATE"] = "8000"
    cfg = Config()
    assert cfg.vosk_model_path == "/custom/vosk/model"
    assert cfg.sample_rate == 8000
    del os.environ["SOBES_VOSK_MODEL_PATH"]
    del os.environ["SOBES_SAMPLE_RATE"]


def test_config_data_dir_created(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "sobes_data"))
    assert os.path.isdir(tmp_path / "sobes_data")
