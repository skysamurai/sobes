# tests/test_storage.py
import os
from sobes_core.storage import SqliteStore, Script, InterviewSession
from sobes_core.config import Config


def test_sqlite_store_init_creates_tables(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    tables = store.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_names = [r[0] for r in tables]
    assert "scripts" in table_names
    assert "sessions" in table_names
    assert "session_transcript" in table_names


def test_sqlite_store_save_and_get_script(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    script = Script(
        id=None,
        title="почему ушёл",
        content="Ушёл из-за отсутствия роста 2 года.",
        tags=["уход", "мотивация"],
        company=None,
        role=None,
    )
    script_id = store.save_script(script)
    assert script_id is not None
    retrieved = store.get_script(script_id)
    assert retrieved.title == "почему ушёл"
    assert retrieved.content == "Ушёл из-за отсутствия роста 2 года."
    assert retrieved.tags == ["уход", "мотивация"]


def test_sqlite_store_list_scripts_by_tag(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    store.save_script(Script(id=None, title="s1", content="c1", tags=["техника", "go"], company=None, role=None))
    store.save_script(Script(id=None, title="s2", content="c2", tags=["hr", "уход"], company=None, role=None))
    results = store.list_scripts(tag="техника")
    assert len(results) == 1
    assert results[0].title == "s1"


def test_sqlite_store_save_session(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    session = InterviewSession(
        id=None,
        company="Яндекс",
        role="Backend Developer",
        interview_type="technical",
        started_at="2026-05-22T12:30:00",
        ended_at="2026-05-22T13:12:00",
        transcript="[12:30] Иван: Расскажите о себе...\n[12:32] Я: Я backend-разработчик...",
        stats='{"your_speech_pct": 58, "questions_asked": 14, "scripts_used": 4}',
    )
    session_id = store.save_session(session)
    assert session_id is not None
    retrieved = store.get_session(session_id)
    assert retrieved.company == "Яндекс"
    assert retrieved.role == "Backend Developer"


def test_sqlite_store_list_sessions_by_company(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    store.save_session(InterviewSession(id=None, company="Яндекс", role="dev", interview_type="tech",
                                         started_at="2026-01-01T10:00:00", ended_at="2026-01-01T11:00:00",
                                         transcript="", stats="{}"))
    store.save_session(InterviewSession(id=None, company="Ozon", role="dev", interview_type="tech",
                                         started_at="2026-02-01T10:00:00", ended_at="2026-02-01T11:00:00",
                                         transcript="", stats="{}"))
    results = store.list_sessions(company="Яндекс")
    assert len(results) == 1
    assert results[0].company == "Яндекс"
