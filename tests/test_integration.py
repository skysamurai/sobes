# tests/test_integration.py
import time
from sobes_core.config import Config
from sobes_core.storage import SqliteStore
from sobes_modules.preparation.service import PreparationService
from sobes_modules.prompt.engine import PromptEngine
from sobes_core.messages import AsrFinal


def test_full_flow_prepare_to_hint(tmp_path):
    """End-to-end: preparation -> prompt search -> hint generation"""
    cfg = Config(data_dir=str(tmp_path))

    store = SqliteStore(cfg.sqlite_path)
    store.initialize()

    prep = PreparationService(cfg, store)
    profile = prep.create_session_profile(company="Яндекс", role="Backend", interview_type="tech")
    prep.add_script(profile["id"], "опыт с Go", "Работал с Go 3 года, highload-проекты", ["go"])
    prep.add_script(profile["id"], "уход", "Ушёл из-за отсутствия роста 2 года", ["уход"])
    prep.index_scripts(profile["id"])

    scripts = prep.get_session_scripts(profile["id"])
    prompt_engine = PromptEngine(cfg)
    for s in scripts:
        prompt_engine.add_script(str(s.id), s.content)

    hints = []
    prompt_engine.set_callback(lambda h: hints.append(h))

    question = AsrFinal(text="расскажите про опыт с Go и highload проектами", timestamp=time.time(), speaker="interviewer")
    prompt_engine.process_question(question)

    assert len(hints) == 1
    assert hints[0].confidence > 0.3
    assert "Go" in hints[0].hint or "highload" in hints[0].hint
