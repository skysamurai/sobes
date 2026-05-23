# tests/test_analyzer.py
import json
from sobes_modules.preparation.analyzer import (
    AnalysisResult, TemplateAnalysisBackend,
)


def test_analysis_result_roundtrip():
    result = AnalysisResult(
        self_presentation="Hello world",
        anticipated_questions=[{"question": "Q1", "suggested_answer": "A1"}],
        salary_recommendation="500k",
        employer_questions=["What about WLB?"],
        raw={"backend": "test"},
        created_at="2026-05-23T00:00:00",
    )
    d = result.to_dict()
    restored = AnalysisResult.from_dict(d)
    assert restored.self_presentation == "Hello world"
    assert restored.anticipated_questions == [{"question": "Q1", "suggested_answer": "A1"}]
    assert restored.salary_recommendation == "500k"
    assert restored.employer_questions == ["What about WLB?"]


def test_analysis_result_defaults():
    result = AnalysisResult()
    d = result.to_dict()
    assert d["self_presentation"] == ""
    assert d["anticipated_questions"] == []
    assert d["salary_recommendation"] == ""
    assert d["employer_questions"] == []
    assert d["created_at"]  # populated with current time


def test_analyze_all_sections_populated():
    backend = TemplateAnalysisBackend()
    vacancy = """
    Компания Яндекс ищет Senior Python Developer.
    Требования: Python, Django, PostgreSQL, Docker, Kubernetes.
    Опыт от 5 лет.
    Зарплата: 300 000 – 450 000 ₽.
    """
    resume = """
    Опыт работы: 7 лет Python разработки.
    Технологии: Python, Django, FastAPI, PostgreSQL, Docker, Redis, AWS.
    Образование: МГУ, факультет ВМК.
    Достижения: увеличил производительность API на 300%.
    """
    result = backend.analyze(
        vacancy_text=vacancy,
        resume_text=resume,
        company="Яндекс",
        role="Senior Python Developer",
        gathered_info="Крутая команда",
        interview_type="tech",
    )

    assert result.self_presentation
    assert "Яндекс" in result.self_presentation
    assert len(result.anticipated_questions) >= 3
    assert result.salary_recommendation
    assert len(result.employer_questions) >= 3
    assert result.created_at


def test_analyze_empty_inputs():
    backend = TemplateAnalysisBackend()
    result = backend.analyze()
    # With empty inputs, we get generic templates, not empty strings
    assert result.salary_recommendation  # has generic recommendation
    assert result.created_at
    # Result is serializable even with empty inputs
    d = result.to_dict()
    assert json.dumps(d, ensure_ascii=False)


def test_analyze_hr_type():
    backend = TemplateAnalysisBackend()
    result = backend.analyze(
        vacancy_text="HR-менеджер в банк. Опыт от 2 лет.",
        resume_text="HR с опытом 3 года. Образование: психфак МГУ.",
        interview_type="hr",
    )
    assert result.self_presentation
    assert len(result.anticipated_questions) >= 2
    # HR role should have different questions than tech
    has_hr_specific = any(
        "конфликт" in q.get("question", "").lower()
        for q in result.anticipated_questions
    )
    assert has_hr_specific


def test_serializable_to_json():
    backend = TemplateAnalysisBackend()
    result = backend.analyze(
        vacancy_text="Python dev", resume_text="Python dev 5 years"
    )
    d = result.to_dict()
    assert json.dumps(d, ensure_ascii=False)  # no serialization error


def test_extract_technologies():
    backend = TemplateAnalysisBackend()
    tech = backend._extract_technologies(
        "Требования: Python, Django, PostgreSQL, Docker, Kubernetes и опыт с AWS."
    )
    assert "Python" in tech
    assert "Django" in tech
    assert "PostgreSQL" in tech
    assert "Docker" in tech
    assert "Kubernetes" in tech
    assert "AWS" in tech


def test_extract_experience_years():
    backend = TemplateAnalysisBackend()
    assert backend._extract_experience_years("Опыт работы: 5 лет в разработке") == 5
    assert backend._extract_experience_years("7 years of experience in Python") == 7
    assert backend._extract_experience_years("Нет опыта") == 0


def test_detect_role_level():
    backend = TemplateAnalysisBackend()
    assert backend._detect_role_level("Senior Python Developer") == "senior"
    assert backend._detect_role_level("Middle Java Developer") == "middle"
    assert backend._detect_role_level("Junior Frontend") == "junior"
    assert backend._detect_role_level("Team Lead") == "lead"


def test_detect_red_flags():
    backend = TemplateAnalysisBackend()
    flags = backend._detect_red_flags(
        "Требуется стрессоустойчивость, ненормированный рабочий день, режим стартапа."
    )
    assert "переработки" in flags
    assert "режим стартапа" in flags
    assert "стрессоустойчивость" in flags
