# tests/test_post_analyzer.py
import json
from sobes_modules.post.analyzer import PostAnalyzer, SessionReport


def test_generate_report_from_transcript():
    transcript = [
        {"timestamp": "12:30:00", "speaker": "interviewer", "text": "Расскажите о себе"},
        {"timestamp": "12:30:15", "speaker": "candidate", "text": "Я backend-разработчик, 5 лет опыта"},
        {"timestamp": "12:32:00", "speaker": "interviewer", "text": "Почему ушли из компании?"},
        {"timestamp": "12:32:10", "speaker": "candidate", "text": "Искал рост и новые вызовы"},
        {"timestamp": "12:35:00", "speaker": "interviewer", "text": "Какой у вас опыт с Go?"},
        {"timestamp": "12:35:30", "speaker": "candidate", "text": "Работал с Go 3 года, писал микросервисы"},
    ]
    analyzer = PostAnalyzer()
    report = analyzer.generate_report(
        transcript=transcript,
        company="Яндекс",
        role="Backend Developer",
        interview_type="technical",
        started_at="2026-05-22T12:30:00",
        ended_at="2026-05-22T12:40:00",
    )
    assert isinstance(report, SessionReport)
    assert report.company == "Яндекс"
    assert report.total_questions == 3
    assert report.stats["candidate_words"] > 0
    assert report.stats["interviewer_words"] > 0


def test_generate_report_stats():
    transcript = [
        {"timestamp": "12:30:00", "speaker": "interviewer", "text": "Расскажите о вашем опыте"},
        {"timestamp": "12:30:15", "speaker": "candidate", "text": "Пять лет в разработке, Go и Python, много проектов"},
    ]
    analyzer = PostAnalyzer()
    report = analyzer.generate_report(
        transcript=transcript,
        company="Ozon",
        role="Senior Dev",
        interview_type="technical",
        started_at="2026-05-22T10:00:00",
        ended_at="2026-05-22T10:01:00",
    )
    stats = report.stats
    assert stats["total_duration_seconds"] > 0
    assert stats["total_questions"] == 1
    assert stats["candidate_words"] > stats["interviewer_words"]


def test_report_to_json():
    transcript = [
        {"timestamp": "12:30:00", "speaker": "interviewer", "text": "Расскажите о себе"},
        {"timestamp": "12:30:15", "speaker": "candidate", "text": "backend-разработчик"},
    ]
    analyzer = PostAnalyzer()
    report = analyzer.generate_report(
        transcript=transcript,
        company="Яндекс",
        role="dev",
        interview_type="hr",
        started_at="2026-05-22T12:30:00",
        ended_at="2026-05-22T12:31:00",
    )
    json_str = json.dumps(report.to_dict(), ensure_ascii=False)
    data = json.loads(json_str)
    assert data["company"] == "Яндекс"
    assert "stats" in data
    assert data["stats"]["total_questions"] == 1


def test_empty_transcript():
    analyzer = PostAnalyzer()
    report = analyzer.generate_report(
        transcript=[],
        company="Test",
        role="dev",
        interview_type="tech",
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:30:00",
    )
    assert report.stats["total_questions"] == 0
    assert report.transcript == ""
