# sobes_modules/audio/capturer.py
import logging
import time
import threading
import pyaudio

logger = logging.getLogger(__name__)

HOST_API_INDEX = 0
CHUNK = 1024


def _fix_device_name(name: str) -> str:
    """Fix mojibake in Windows device names with Cyrillic characters."""
    pairs = [
        ('cp1251', 'utf-8'),   # UTF-8 bytes decoded as Windows Cyrillic
        ('latin-1', 'utf-8'),  # UTF-8 bytes decoded as Latin-1
        ('cp866', 'utf-8'),    # UTF-8 bytes decoded as DOS Cyrillic
        ('cp1251', 'cp866'),   # DOS Cyrillic decoded as Windows Cyrillic
        ('latin-1', 'cp1251'), # Windows Cyrillic decoded as Latin-1
        ('latin-1', 'cp866'),  # DOS Cyrillic decoded as Latin-1
    ]
    for src, dst in pairs:
        try:
            fixed = name.encode(src).decode(dst)
            if _is_better(name, fixed):
                return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    return name


def _count_rare_chars(s: str) -> int:
    """Count chars that are unlikely in genuine Russian text."""
    rare = set(
        'ЂЅІЇЈЉЊЋЌЎЏ'
        'ђѕіїјљњћќўџ'
        'ЀЁЃЄЍѐѓєѝ'
    )
    return sum(1 for c in s if c in rare)


def _has_cyrillic(s: str) -> bool:
    return any('А' <= c <= 'я' or c in 'Ёё' for c in s)


def _is_better(original: str, fixed: str) -> bool:
    """True if fixed is a genuine improvement over original."""
    if fixed == original or not fixed.strip():
        return False
    # If original has no Cyrillic and fixed does — definite improvement
    if not _has_cyrillic(original) and _has_cyrillic(fixed):
        return True
    # If both have Cyrillic, prefer the one with fewer rare/un-Russian chars
    if _has_cyrillic(original) and _has_cyrillic(fixed):
        return _count_rare_chars(fixed) < _count_rare_chars(original)
    return False


def list_audio_devices() -> list[dict]:
    pa = pyaudio.PyAudio()
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        devices.append({
            "index": i,
            "name": _fix_device_name(info["name"]),
            "max_input_channels": info["maxInputChannels"],
            "max_output_channels": info["maxOutputChannels"],
            "default_sample_rate": info["defaultSampleRate"],
        })
    pa.terminate()
    return devices


class AudioCapturer:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config.sample_rate
        self.channels = config.channels
        self.sample_width = config.sample_width
        self.chunk_duration_ms = config.chunk_duration_ms
        self.device_index = config.audio_device_index
        self.chunk_size = int(
            self.sample_rate * self.channels * self.sample_width
            * (self.chunk_duration_ms / 1000)
        )
        self.running = False
        self._callback = None
        self._thread = None
        self._pa = None

    def set_callback(self, callback):
        self._callback = callback

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _capture_loop(self):
        self._pa = pyaudio.PyAudio()
        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=(self.device_index if self.device_index >= 0 else None),
                frames_per_buffer=CHUNK,
            )
            while self.running and self._callback:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    ts = time.time()
                    self._callback(data, ts)
                except Exception as e:
                    logger.error(f"Capture error: {e}")
                    break
            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"Audio device error: {e}")
        finally:
            self._pa.terminate()
