# sobes_modules/post/analyzer.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionReport:
    company: str
    role: str
    interview_type: str
    started_at: str
    ended_at: str
    transcript: str
    stats: dict
    topics: list[dict] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    risk_zones: list[str] = field(default_factory=list)

    @property
    def total_questions(self) -> int:
        return self.stats.get("total_questions", 0)

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "role": self.role,
            "interview_type": self.interview_type,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "transcript": self.transcript,
            "stats": self.stats,
            "topics": self.topics,
            "action_items": self.action_items,
            "risk_zones": self.risk_zones,
        }


class PostAnalyzer:
    def generate_report(
        self,
        transcript: list[dict],
        company: str,
        role: str,
        interview_type: str,
        started_at: str,
        ended_at: str,
    ) -> SessionReport:
        interview_words = 0
        candidate_words = 0
        questions = 0
        question_markers = ["?", "расскажите", "почему", "какой", "как вы", "что вы"]

        for entry in transcript:
            words = len(entry["text"].split())
            if entry["speaker"] == "candidate":
                candidate_words += words
            else:
                interview_words += words
                text_lower = entry["text"].lower()
                if any(marker in text_lower for marker in question_markers):
                    questions += 1

        duration = 0
        if transcript:
            try:
                start_dt = datetime.fromisoformat(started_at)
                end_dt = datetime.fromisoformat(ended_at)
                duration = (end_dt - start_dt).total_seconds()
            except (ValueError, TypeError):
                duration = 0

        total_words = candidate_words + interview_words
        candidate_pct = round(candidate_words / total_words * 100) if total_words > 0 else 0
        interviewer_pct = 100 - candidate_pct

        raw_transcript = "\n".join(
            f"[{e['timestamp']}] {e['speaker']}: {e['text']}" for e in transcript
        )

        return SessionReport(
            company=company,
            role=role,
            interview_type=interview_type,
            started_at=started_at,
            ended_at=ended_at,
            transcript=raw_transcript,
            stats={
                "total_duration_seconds": int(duration),
                "total_words": total_words,
                "candidate_words": candidate_words,
                "interviewer_words": interview_words,
                "candidate_speech_pct": candidate_pct,
                "interviewer_speech_pct": interviewer_pct,
                "total_questions": questions,
                "scripts_used": 0,
            },
        )
