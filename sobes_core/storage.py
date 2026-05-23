# sobes_core/storage.py
import sqlite3
import json
from dataclasses import dataclass, field


@dataclass
class Script:
    id: int | None
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    company: str | None = None
    role: str | None = None


@dataclass
class InterviewSession:
    id: int | None
    company: str
    role: str
    interview_type: str
    started_at: str
    ended_at: str
    transcript: str
    stats: str  # JSON string
    analysis: str = "{}"  # JSON string — vacancy+resume analysis result


class SqliteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    company TEXT,
                    role TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    interview_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    transcript TEXT DEFAULT '',
                    stats TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS session_transcript (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES sessions(id),
                    timestamp TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL
                );
            """)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN analysis TEXT DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass  # column already exists

    def execute(self, query: str, params=None):
        with self._connect() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.fetchall()

    def save_script(self, script: Script) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO scripts (title, content, tags, company, role) VALUES (?, ?, ?, ?, ?)",
                (script.title, script.content, json.dumps(script.tags, ensure_ascii=False), script.company, script.role),
            )
            return cursor.lastrowid

    def get_script(self, script_id: int) -> Script | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if row is None:
            return None
        return Script(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            company=row["company"],
            role=row["role"],
        )

    def list_scripts(self, tag: str | None = None) -> list[Script]:
        with self._connect() as conn:
            if tag:
                rows = conn.execute(
                    "SELECT s.* FROM scripts s, json_each(s.tags) WHERE json_each.value = ?",
                    (tag,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM scripts ORDER BY created_at DESC").fetchall()
        return [
            Script(
                id=r["id"], title=r["title"], content=r["content"],
                tags=json.loads(r["tags"]), company=r["company"], role=r["role"],
            )
            for r in rows
        ]

    def save_session(self, session: InterviewSession) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO sessions (company, role, interview_type, started_at, ended_at, transcript, stats, analysis)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session.company, session.role, session.interview_type,
                 session.started_at, session.ended_at, session.transcript, session.stats, session.analysis),
            )
            return cursor.lastrowid

    def get_session(self, session_id: int) -> InterviewSession | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return InterviewSession(
            id=row["id"], company=row["company"], role=row["role"],
            interview_type=row["interview_type"], started_at=row["started_at"],
            ended_at=row["ended_at"], transcript=row["transcript"], stats=row["stats"],
            analysis=row["analysis"] if "analysis" in row.keys() else "{}",
        )

    def list_sessions(self, company: str | None = None) -> list[InterviewSession]:
        with self._connect() as conn:
            if company:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE company = ? ORDER BY created_at DESC", (company,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [
            InterviewSession(
                id=r["id"], company=r["company"], role=r["role"],
                interview_type=r["interview_type"], started_at=r["started_at"],
                ended_at=r["ended_at"], transcript=r["transcript"], stats=r["stats"],
                analysis=r["analysis"] if "analysis" in r.keys() else "{}",
            )
            for r in rows
        ]
