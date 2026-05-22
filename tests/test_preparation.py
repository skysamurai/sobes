# tests/test_preparation.py
from sobes_modules.preparation.service import PreparationService
from sobes_core.config import Config
from sobes_core.storage import SqliteStore


def test_preparation_create_session_profile(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(
        company="Яндекс",
        role="Backend Developer",
        interview_type="technical",
    )
    assert profile["company"] == "Яндекс"
    assert profile["role"] == "Backend Developer"
    assert profile["interview_type"] == "technical"
    assert "id" in profile


def test_preparation_add_script(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(company="Яндекс", role="dev", interview_type="tech")
    script_id = svc.add_script(
        session_id=profile["id"],
        title="почему ушёл",
        content="Ушёл из-за стагнации 2 года.",
        tags=["уход", "мотивация"],
    )
    assert script_id > 0

    scripts = svc.get_session_scripts(profile["id"])
    assert len(scripts) == 1
    assert scripts[0].title == "почему ушёл"


def test_preparation_index_scripts(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(company="Яндекс", role="dev", interview_type="tech")
    svc.add_script(session_id=profile["id"], title="s1", content="опыт с Go", tags=["go"])
    svc.add_script(session_id=profile["id"], title="s2", content="опыт с Python", tags=["python"])

    result = svc.index_scripts(profile["id"])
    assert result["indexed_count"] == 2
    assert result["status"] == "ok"


def test_preparation_get_readiness_report(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(company="Яндекс", role="dev", interview_type="tech")
    svc.add_script(session_id=profile["id"], title="s1", content="опыт с Go", tags=["go"])
    svc.index_scripts(profile["id"])

    report = svc.get_readiness_report(profile["id"])
    assert report["scripts_count"] == 1
    assert report["indexed"] is True
    assert report["status"] == "ready"
