# tests/test_asr.py
from sobes_modules.asr.engine import AsrEngine
from sobes_core.config import Config
from sobes_core.messages import AsrPartial, AsrFinal


class FakeVoskModel:
    def __init__(self, *args, **kwargs):
        pass


class FakeVoskRecognizer:
    def __init__(self, model, sample_rate):
        self.calls = 0

    def AcceptWaveform(self, data):
        self.calls += 1
        return 0 if self.calls <= 2 else 1

    def SetWords(self, val):
        pass

    def PartialResult(self):
        return '{"partial":"тестовый"}'

    def FinalResult(self):
        return '{"text":"тестовый вопрос"}'


def test_asr_engine_process_chunk(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = AsrEngine(cfg, model_path="/fake/model")

    engine._model = FakeVoskModel()
    engine._recognizer = FakeVoskRecognizer(engine._model, cfg.sample_rate)

    messages = []
    engine.set_callback(lambda msg: messages.append(msg))

    engine.process_chunk(b"\x00" * 16000, 1234.5)

    assert len(messages) > 0
    assert any(isinstance(m, AsrPartial) for m in messages)


def test_asr_engine_callbacks(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = AsrEngine(cfg, model_path="/fake/model")

    messages = []
    engine.set_callback(lambda msg: messages.append(msg))

    engine._model = FakeVoskModel()
    engine._recognizer = FakeVoskRecognizer(engine._model, cfg.sample_rate)

    engine.process_chunk(b"\x00" * 8000, 500.0)

    assert len(messages) >= 1


def test_asr_engine_multiple_chunks_reset(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = AsrEngine(cfg, model_path="/fake/model")
    engine._model = FakeVoskModel()
    engine._recognizer = FakeVoskRecognizer(engine._model, cfg.sample_rate)

    msgs1 = []
    engine.set_callback(lambda m: msgs1.append(m))
    engine.process_chunk(b"\x00" * 8000, 1.0)
    assert len(msgs1) >= 1

    engine.reset()
    msgs2 = []
    engine.set_callback(lambda m: msgs2.append(m))
    engine.process_chunk(b"\x00" * 8000, 2.0)
    assert len(msgs2) >= 1
