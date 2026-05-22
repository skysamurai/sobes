# tests/test_prompt_engine.py
import time
from sobes_modules.prompt.engine import PromptEngine
from sobes_core.config import Config
from sobes_core.messages import AsrFinal, PromptHint


def test_prompt_engine_searches_scripts(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = PromptEngine(cfg)

    engine.add_script("s1", "расскажи про опыт с Go и микросервисами")
    engine.add_script("s2", "почему ушёл из прошлой компании")
    engine.add_script("s3", "какие у тебя зарплатные ожидания")

    hints = []
    engine.set_callback(lambda h: hints.append(h))

    question = AsrFinal(text="расскажи про твой опыт работы с го", timestamp=time.time(), speaker="interviewer")
    engine.process_question(question)

    assert len(hints) == 1
    assert isinstance(hints[0], PromptHint)
    assert hints[0].confidence > 0
    assert "s1" in hints[0].source_script


def test_prompt_engine_no_match(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = PromptEngine(cfg)

    engine.add_script("s1", "расскажи про Go и микросервисы")

    hints = []
    engine.set_callback(lambda h: hints.append(h))

    question = AsrFinal(text="какой твой любимый цвет", timestamp=time.time(), speaker="interviewer")
    engine.process_question(question)

    assert len(hints) == 0


def test_prompt_engine_multiple_matches_best_first(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = PromptEngine(cfg)

    engine.add_script("s1", "опыт работы с Python и Django")
    engine.add_script("s2", "опыт работы с Go и высоконагруженными системами")

    hints = []
    engine.set_callback(lambda h: hints.append(h))

    question = AsrFinal(text="расскажи про твой опыт с Go бэкендом", timestamp=time.time(), speaker="interviewer")
    engine.process_question(question)

    assert len(hints) == 1
    assert "s2" in hints[0].source_script
