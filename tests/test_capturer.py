# tests/test_capturer.py
import time
from sobes_modules.audio.capturer import AudioCapturer, list_audio_devices
from sobes_core.config import Config


def test_list_audio_devices():
    devices = list_audio_devices()
    assert isinstance(devices, list)


def test_audio_capturer_init(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    capturer = AudioCapturer(cfg)
    assert capturer.sample_rate == 16000
    assert capturer.chunk_size > 0
    assert capturer.running is False


def test_audio_capturer_chunk_size_calculation(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    cfg.sample_rate = 16000
    cfg.chunk_duration_ms = 500
    cfg.channels = 1
    cfg.sample_width = 2
    capturer = AudioCapturer(cfg)
    expected = int(16000 * 1 * 2 * 0.5)
    assert capturer.chunk_size == expected


def test_audio_capturer_start_stop_no_real_device(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    capturer = AudioCapturer(cfg)

    chunks = []

    def dummy_callback(data: bytes, timestamp: float):
        chunks.append(data)

    capturer.set_callback(dummy_callback)
    capturer.start()
    time.sleep(0.1)
    capturer.stop()

    assert capturer.running is False
