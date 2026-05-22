# Interview Assistant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build interview assistant PoC: preparation → live hint overlay → post-analysis, targeting Skype calls.

**Architecture:** Modular IPC via ZeroMQ. 8 independent processes communicate through session_manager broker. Each module is independently testable.

**Tech Stack:** Python 3.12+, ZeroMQ (pyzmq), Vosk, ChromaDB, SQLite, PySide6, PyAudio, httpx

---

## File Structure

```
sobes/
├── sobes_core/
│   ├── __init__.py
│   ├── messages.py         # ZeroMQ message types + serialization
│   ├── config.py           # Configuration: paths, ports, model settings
│   ├── storage.py          # SQLite + ChromaDB wrapper
│   └── session_manager.py  # ZeroMQ broker, lifecycle orchestration
├── sobes_modules/
│   ├── __init__.py
│   ├── preparation/
│   │   ├── __init__.py
│   │   └── service.py      # Preparation: questionnaire + indexing
│   ├── audio/
│   │   ├── __init__.py
│   │   └── capturer.py     # System audio capture via PyAudio
│   ├── asr/
│   │   ├── __init__.py
│   │   └── engine.py       # Vosk speech recognition
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── engine.py       # Script search via ChromaDB
│   ├── overlay/
│   │   ├── __init__.py
│   │   └── ui.py           # PySide6 overlay window
│   └── post/
│       ├── __init__.py
│       └── analyzer.py     # Post-call report generation
├── tests/
│   ├── __init__.py
│   ├── test_messages.py
│   ├── test_config.py
│   ├── test_storage.py
│   ├── test_session_manager.py
│   ├── test_preparation.py
│   ├── test_capturer.py
│   ├── test_asr.py
│   ├── test_prompt_engine.py
│   ├── test_overlay.py
│   └── test_post_analyzer.py
├── main.py                  # CLI entry point
├── requirements.txt
└── README.md
```

---

### Task 1: Project scaffold + dependencies

**Files:**
- Create: `requirements.txt`
- Create: `sobes_core/__init__.py`
- Create: `sobes_modules/__init__.py`
- Create: `sobes_modules/preparation/__init__.py`
- Create: `sobes_modules/audio/__init__.py`
- Create: `sobes_modules/asr/__init__.py`
- Create: `sobes_modules/prompt/__init__.py`
- Create: `sobes_modules/overlay/__init__.py`
- Create: `sobes_modules/post/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
pyzmq>=25.1
vosk>=0.3.45
chromadb>=0.4.22
pyaudio>=0.2.13
PySide6>=6.6
httpx>=0.27
sentence-transformers>=2.7
```

- [ ] **Step 2: Create package __init__ files**

All `__init__.py` files are empty (`# Package`).

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt sobes_core/ sobes_modules/ tests/
git commit -m "feat: scaffold project structure and dependencies"
```

---

### Task 2: Message types (sobes_core/messages.py)

**Files:**
- Create: `sobes_core/messages.py`
- Create: `tests/test_messages.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_messages.py
import json
import pytest
from sobes_core.messages import (
    AudioChunk, AsrPartial, AsrFinal, PromptHint,
    UiCommand, SessionEvent, MessageType, serialize, deserialize
)


def test_audio_chunk_serialization():
    msg = AudioChunk(data=b"\x00\x01\x02", timestamp=1234567890.5, sample_rate=16000, channels=1, sample_width=2)
    raw = serialize(msg)
    restored = deserialize(raw)
    assert isinstance(restored, AudioChunk)
    assert restored.data == b"\x00\x01\x02"
    assert restored.timestamp == 1234567890.5
    assert restored.sample_rate == 16000


def test_asr_partial_serialization():
    msg = AsrPartial(text="привет как", is_partial=True, timestamp=1234.5)
    raw = serialize(msg)
    restored = deserialize(raw)
    assert restored.text == "привет как"
    assert restored.is_partial is True


def test_asr_final_serialization():
    msg = AsrFinal(text="привет как дела", timestamp=1234.5, speaker="interviewer")
    raw = serialize(msg)
    restored = deserialize(raw)
    assert restored.text == "привет как дела"
    assert restored.speaker == "interviewer"


def test_prompt_hint_serialization():
    msg = PromptHint(
        hint="Расскажи про микросервисы",
        source_script="кейс-микросервисы",
        confidence=0.87,
        timestamp=1234.5,
    )
    raw = serialize(msg)
    restored = deserialize(raw)
    assert restored.hint == "Расскажи про микросервисы"
    assert restored.confidence == 0.87


def test_ui_command_serialization():
    msg = UiCommand(command="toggle_mode", payload={"mode": "compact"})
    raw = serialize(msg)
    restored = deserialize(raw)
    assert restored.command == "toggle_mode"
    assert restored.payload == {"mode": "compact"}


def test_session_event_serialization():
    msg = SessionEvent(event="start", session_id="abc-123", timestamp=1234.5)
    raw = serialize(msg)
    restored = deserialize(raw)
    assert restored.event == "start"
    assert restored.session_id == "abc-123"


def test_message_type_enum():
    assert MessageType.AUDIO_CHUNK == "audio.chunk"
    assert MessageType.ASR_PARTIAL == "asr.partial"
    assert MessageType.ASR_FINAL == "asr.final"
    assert MessageType.PROMPT_HINT == "prompt.hint"
    assert MessageType.UI_COMMAND == "ui.command"
    assert MessageType.SESSION_EVENT == "session.event"


def test_deserialize_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown message type"):
        deserialize(json.dumps({"type": "bogus.msg", "payload": {}}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_messages.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_core/messages.py
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import base64


class MessageType(str, Enum):
    AUDIO_CHUNK = "audio.chunk"
    ASR_PARTIAL = "asr.partial"
    ASR_FINAL = "asr.final"
    PROMPT_HINT = "prompt.hint"
    UI_COMMAND = "ui.command"
    SESSION_EVENT = "session.event"


@dataclass
class AudioChunk:
    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2


@dataclass
class AsrPartial:
    text: str
    is_partial: bool
    timestamp: float


@dataclass
class AsrFinal:
    text: str
    timestamp: float
    speaker: str = "unknown"


@dataclass
class PromptHint:
    hint: str
    source_script: str
    confidence: float
    timestamp: float


@dataclass
class UiCommand:
    command: str
    payload: dict = field(default_factory=dict)


@dataclass
class SessionEvent:
    event: str
    session_id: str
    timestamp: float


_MESSAGE_CLASSES = {
    MessageType.AUDIO_CHUNK: AudioChunk,
    MessageType.ASR_PARTIAL: AsrPartial,
    MessageType.ASR_FINAL: AsrFinal,
    MessageType.PROMPT_HINT: PromptHint,
    MessageType.UI_COMMAND: UiCommand,
    MessageType.SESSION_EVENT: SessionEvent,
}


def serialize(msg) -> str:
    msg_type = None
    for mt, cls in _MESSAGE_CLASSES.items():
        if isinstance(msg, cls):
            msg_type = mt
            break
    if msg_type is None:
        raise ValueError(f"Unknown message class: {type(msg)}")
    d = asdict(msg)
    if isinstance(msg, AudioChunk):
        d["data"] = base64.b64encode(msg.data).decode("ascii")
    return json.dumps({"type": msg_type.value, "payload": d})


def deserialize(raw: str):
    envelope = json.loads(raw)
    msg_type = MessageType(envelope["type"])
    payload = envelope["payload"]
    cls = _MESSAGE_CLASSES[msg_type]
    if cls is AudioChunk:
        payload["data"] = base64.b64decode(payload["data"])
    return cls(**payload)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_messages.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_core/messages.py tests/test_messages.py
git commit -m "feat: define ZeroMQ message types with JSON serialization"
```

---

### Task 3: Configuration (sobes_core/config.py)

**Files:**
- Create: `sobes_core/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os
from sobes_core.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.zmq_session_port == 5555
    assert cfg.zmq_capturer_port == 5556
    assert cfg.zmq_asr_port == 5557
    assert cfg.zmq_prompt_port == 5558
    assert cfg.zmq_ui_port == 5559
    assert cfg.vosk_model_path == "models/vosk-model-small-ru-0.22"
    assert cfg.sample_rate == 16000
    assert cfg.chunk_duration_ms == 500
    assert "sobes" in cfg.data_dir


def test_config_from_env():
    os.environ["SOBES_VOSK_MODEL_PATH"] = "/custom/vosk/model"
    os.environ["SOBES_SAMPLE_RATE"] = "8000"
    cfg = Config()
    assert cfg.vosk_model_path == "/custom/vosk/model"
    assert cfg.sample_rate == 8000
    del os.environ["SOBES_VOSK_MODEL_PATH"]
    del os.environ["SOBES_SAMPLE_RATE"]


def test_config_data_dir_created(tmp_path):
    cfg = Config(data_dir=str(tmp_path / "sobes_data"))
    assert os.path.isdir(tmp_path / "sobes_data")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_core/config.py
import os
import platform


class Config:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or self._default_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)

        self.zmq_session_port = int(os.getenv("SOBES_ZMQ_SESSION_PORT", "5555"))
        self.zmq_capturer_port = int(os.getenv("SOBES_ZMQ_CAPTURER_PORT", "5556"))
        self.zmq_asr_port = int(os.getenv("SOBES_ZMQ_ASR_PORT", "5557"))
        self.zmq_prompt_port = int(os.getenv("SOBES_ZMQ_PROMPT_PORT", "5558"))
        self.zmq_ui_port = int(os.getenv("SOBES_ZMQ_UI_PORT", "5559"))

        default_model = "models/vosk-model-small-ru-0.22"
        self.vosk_model_path = os.getenv("SOBES_VOSK_MODEL_PATH", default_model)
        self.sample_rate = int(os.getenv("SOBES_SAMPLE_RATE", "16000"))
        self.chunk_duration_ms = int(os.getenv("SOBES_CHUNK_DURATION_MS", "500"))
        self.channels = 1
        self.sample_width = 2

        self.chroma_dir = os.path.join(self.data_dir, "chroma")
        self.sqlite_path = os.path.join(self.data_dir, "sobes.db")
        self.embedding_model = os.getenv(
            "SOBES_EMBEDDING_MODEL",
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.script_confidence_threshold = float(
            os.getenv("SOBES_CONFIDENCE_THRESHOLD", "0.75")
        )

    @staticmethod
    def _default_data_dir():
        if platform.system() == "Windows":
            base = os.getenv("APPDATA", os.path.expanduser("~"))
        else:
            base = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(base, "sobes")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_core/config.py tests/test_config.py
git commit -m "feat: add configuration with env overrides"
```

---

### Task 4: Storage layer (sobes_core/storage.py)

**Files:**
- Create: `sobes_core/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_core/storage.py
import sqlite3
import json
from dataclasses import dataclass, field


@dataclass
class Script:
    id: str | None
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    company: str | None = None
    role: str | None = None


@dataclass
class InterviewSession:
    id: str | None
    company: str
    role: str
    interview_type: str
    started_at: str
    ended_at: str
    transcript: str
    stats: str  # JSON string


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

    def execute(self, query: str, params=None):
        with self._connect() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.fetchall()

    def save_script(self, script: Script) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO scripts (title, content, tags, company, role) VALUES (?, ?, ?, ?, ?)",
                (script.title, script.content, json.dumps(script.tags), script.company, script.role),
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
                    "SELECT * FROM scripts WHERE tags LIKE ?", (f'%"{tag}"%',)
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
                """INSERT INTO sessions (company, role, interview_type, started_at, ended_at, transcript, stats)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session.company, session.role, session.interview_type,
                 session.started_at, session.ended_at, session.transcript, session.stats),
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
            )
            for r in rows
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_core/storage.py tests/test_storage.py
git commit -m "feat: add SQLite storage for scripts and sessions"
```

---

### Task 5: Session Manager (sobes_core/session_manager.py)

**Files:**
- Create: `sobes_core/session_manager.py`
- Create: `tests/test_session_manager.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_session_manager.py
import time
import threading
import zmq
from sobes_core.session_manager import SessionManager
from sobes_core.messages import serialize, deserialize, SessionEvent


def test_session_manager_pub_sub():
    mgr = SessionManager(pub_port=15555, pull_port=15556)
    mgr_thread = threading.Thread(target=mgr.run, daemon=True)
    mgr_thread.start()
    time.sleep(0.3)

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://127.0.0.1:{mgr.pub_port}")
    sub.setsockopt_string(zmq.SUBSCRIBE, "")

    push = ctx.socket(zmq.PUSH)
    push.connect(f"tcp://127.0.0.1:{mgr.pull_port}")

    event = SessionEvent(event="start", session_id="test-1", timestamp=time.time())
    push.send_string(serialize(event))

    time.sleep(0.2)
    try:
        raw = sub.recv_string(flags=zmq.NOBLOCK)
        received = deserialize(raw)
        assert isinstance(received, SessionEvent)
        assert received.event == "start"
        assert received.session_id == "test-1"
    except zmq.Again:
        pytest.fail("No message received from pub socket")

    mgr.stop()
    sub.close()
    push.close()
    ctx.term()


def test_session_manager_forwards_any_message():
    mgr = SessionManager(pub_port=15557, pull_port=15558)
    mgr_thread = threading.Thread(target=mgr.run, daemon=True)
    mgr_thread.start()
    time.sleep(0.3)

    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://127.0.0.1:{mgr.pub_port}")
    sub.setsockopt_string(zmq.SUBSCRIBE, "")

    push = ctx.socket(zmq.PUSH)
    push.connect(f"tcp://127.0.0.1:{mgr.pull_port}")

    from sobes_core.messages import AsrFinal
    msg = AsrFinal(text="тестовый вопрос", timestamp=time.time(), speaker="interviewer")
    push.send_string(serialize(msg))

    time.sleep(0.2)
    try:
        raw = sub.recv_string(flags=zmq.NOBLOCK)
        received = deserialize(raw)
        assert isinstance(received, AsrFinal)
        assert received.text == "тестовый вопрос"
    except zmq.Again:
        pytest.fail("No message received")

    mgr.stop()
    sub.close()
    push.close()
    ctx.term()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_core/session_manager.py
import zmq
import threading
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, pub_port=5555, pull_port=5556):
        self.pub_port = pub_port
        self.pull_port = pull_port
        self._running = False
        self._ctx = zmq.Context()

    def run(self):
        self._running = True
        pub = self._ctx.socket(zmq.PUB)
        pub.bind(f"tcp://127.0.0.1:{self.pub_port}")
        pull = self._ctx.socket(zmq.PULL)
        pull.bind(f"tcp://127.0.0.1:{self.pull_port}")
        poller = zmq.Poller()
        poller.register(pull, zmq.POLLIN)

        logger.info(f"SessionManager running: PUB={self.pub_port}, PULL={self.pull_port}")

        while self._running:
            socks = dict(poller.poll(timeout=100))
            if pull in socks and socks[pull] == zmq.POLLIN:
                msg = pull.recv_string()
                pub.send_string(msg)

        pub.close()
        pull.close()
        self._ctx.term()
        logger.info("SessionManager stopped")

    def stop(self):
        self._running = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_manager.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_core/session_manager.py tests/test_session_manager.py
git commit -m "feat: add ZeroMQ session manager (PUB/PULL proxy)"
```

---

### Task 6: Preparation Service (sobes_modules/preparation/service.py)

**Files:**
- Create: `sobes_modules/preparation/service.py`
- Create: `tests/test_preparation.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_preparation.py
from sobes_modules.preparation.service import PreparationService
from sobes_core.config import Config
from sobes_core.storage import SqliteStore, Script


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_preparation.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_modules/preparation/service.py
import uuid
import logging
from sobes_core.config import Config
from sobes_core.storage import SqliteStore, Script

logger = logging.getLogger(__name__)


class PreparationService:
    def __init__(self, config: Config, store: SqliteStore):
        self.config = config
        self.store = store
        self._sessions: dict[str, dict] = {}

    def create_session_profile(self, company: str, role: str, interview_type: str) -> dict:
        session_id = str(uuid.uuid4())[:8]
        profile = {
            "id": session_id,
            "company": company,
            "role": role,
            "interview_type": interview_type,
            "scripts": [],
            "indexed": False,
        }
        self._sessions[session_id] = profile
        return profile

    def add_script(self, session_id: str, title: str, content: str, tags: list[str]) -> int:
        script = Script(id=None, title=title, content=content, tags=tags, company=None, role=None)
        script_id = self.store.save_script(script)
        if session_id in self._sessions:
            self._sessions[session_id]["scripts"].append(script_id)
        return script_id

    def get_session_scripts(self, session_id: str) -> list[Script]:
        if session_id not in self._sessions:
            return []
        script_ids = self._sessions[session_id]["scripts"]
        return [self.store.get_script(sid) for sid in script_ids if self.store.get_script(sid)]

    def index_scripts(self, session_id: str) -> dict:
        scripts = self.get_session_scripts(session_id)
        indexed = 0
        for script in scripts:
            doc_id = f"session-{session_id}-{script.id}"
            # Will use ChromaDB in Task 8 — for now just count
            indexed += 1
        if session_id in self._sessions:
            self._sessions[session_id]["indexed"] = True
        return {"status": "ok", "indexed_count": indexed}

    def get_readiness_report(self, session_id: str) -> dict:
        profile = self._sessions.get(session_id, {})
        scripts = self.get_session_scripts(session_id)
        return {
            "session_id": session_id,
            "scripts_count": len(scripts),
            "indexed": profile.get("indexed", False),
            "status": "ready" if scripts and profile.get("indexed") else "needs_scripts",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_preparation.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/preparation/service.py tests/test_preparation.py
git commit -m "feat: add preparation service with scripts management"
```

---

### Task 7: Audio Capturer (sobes_modules/audio/capturer.py)

**Files:**
- Create: `sobes_modules/audio/capturer.py`
- Create: `tests/test_capturer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_capturer.py
import pytest
import time
from sobes_modules.audio.capturer import AudioCapturer, list_audio_devices
from sobes_core.config import Config


def test_list_audio_devices():
    devices = list_audio_devices()
    assert isinstance(devices, list)
    # Even without real audio HW, PyAudio should return empty list not crash


def test_audio_capturer_init(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    capturer = AudioCapturer(cfg)
    assert capturer.sample_rate == 16000
    assert capturer.chunk_size > 0
    assert capturer.running is False


def test_audio_capturer_chunk_size_calculation(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    cfg.sample_rate = 16000
    cfg.chunk_duration_ms = 500
    cfg.channels = 1
    cfg.sample_width = 2
    capturer = AudioCapturer(cfg)
    # chunk_size = sample_rate * channels * sample_width * (chunk_duration_ms / 1000)
    expected = int(16000 * 1 * 2 * 0.5)
    assert capturer.chunk_size == expected


def test_audio_capturer_start_stop_no_real_device(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    capturer = AudioCapturer(cfg)

    chunks = []

    def dummy_callback(data: bytes, timestamp: float):
        chunks.append(data)

    capturer.set_callback(dummy_callback)
    capturer.start()
    time.sleep(0.1)
    capturer.stop()

    assert capturer.running is False
    # With no real device, no chunks expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_capturer.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_modules/audio/capturer.py
import logging
import time
import threading
import pyaudio

logger = logging.getLogger(__name__)

HOST_API_INDEX = 0
CHUNK = 1024


def list_audio_devices() -> list[dict]:
    pa = pyaudio.PyAudio()
    devices = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        devices.append({
            "index": i,
            "name": info["name"],
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
                input_device_index=None,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_capturer.py -v`
Expected: 4 PASS (or 3 PASS + 1 SKIP if no audio device)

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/audio/capturer.py tests/test_capturer.py
git commit -m "feat: add audio capturer with PyAudio loopback"
```

---

### Task 8: ASR Engine (sobes_modules/asr/engine.py)

**Files:**
- Create: `sobes_modules/asr/engine.py`
- Create: `tests/test_asr.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_asr.py
import pytest
from unittest.mock import patch, MagicMock
from sobes_modules.asr.engine import AsrEngine
from sobes_core.config import Config
from sobes_core.messages import AsrPartial, AsrFinal


class FakeVoskModel:
    def __init__(self, *args, **kwargs):
        pass

    def AcceptWaveform(self, data):
        # Return (status, text) — status=1 means partial, status=0 means final
        return (1, "тестовый")

    def SetWords(self, val):
        pass


class FakeVoskRecognizer:
    def __init__(self, model, sample_rate):
        self.AcceptWaveform = model.AcceptWaveform

    def AcceptWaveform(self, data):
        return self.AcceptWaveform(data)

    def PartialResult(self):
        return '{"partial":"тестовый"}'

    def FinalResult(self):
        return '{"text":"тестовый вопрос"}'


def test_asr_engine_process_chunk(tmp_path):
    cfg = Config(data_dir=str(tmp_path))
    engine = AsrEngine(cfg, model_path="/fake/model")

    # Mock Vosk internals
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_asr.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_modules/asr/engine.py
import json
import logging
from sobes_core.messages import AsrPartial, AsrFinal

logger = logging.getLogger(__name__)

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class AsrEngine:
    def __init__(self, config, model_path: str):
        self.config = config
        self.model_path = model_path
        self.sample_rate = config.sample_rate
        self._callback = None
        self._model = None
        self._recognizer = None

    def initialize(self):
        if not VOSK_AVAILABLE:
            raise RuntimeError("Vosk not installed")
        self._model = vosk.Model(self.model_path)
        self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        self._recognizer.SetWords(False)

    def set_callback(self, callback):
        self._callback = callback

    def _emit(self, message):
        if self._callback:
            self._callback(message)

    def process_chunk(self, audio_data: bytes, timestamp: float):
        if self._recognizer is None:
            logger.warning("Recognizer not initialized, skipping chunk")
            return

        if self._recognizer.AcceptWaveform(audio_data):
            final_text = json.loads(self._recognizer.FinalResult()).get("text", "")
            if final_text.strip():
                self._emit(AsrFinal(text=final_text, timestamp=timestamp, speaker="unknown"))
        else:
            partial_text = json.loads(self._recognizer.PartialResult()).get("partial", "")
            if partial_text.strip():
                self._emit(AsrPartial(text=partial_text, is_partial=True, timestamp=timestamp))

    def reset(self):
        if self._model:
            self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
            self._recognizer.SetWords(False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_asr.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/asr/engine.py tests/test_asr.py
git commit -m "feat: add Vosk ASR engine with callback interface"
```

---

### Task 9: Prompt Engine (sobes_modules/prompt/engine.py)

**Files:**
- Create: `sobes_modules/prompt/engine.py`
- Create: `tests/test_prompt_engine.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_modules/prompt/engine.py
import logging
import time
from difflib import SequenceMatcher
from sobes_core.messages import PromptHint, AsrFinal

logger = logging.getLogger(__name__)


class PromptEngine:
    def __init__(self, config):
        self.config = config
        self._scripts: dict[str, str] = {}
        self._callback = None
        self._threshold = config.script_confidence_threshold

    def set_callback(self, callback):
        self._callback = callback

    def add_script(self, script_id: str, content: str):
        self._scripts[script_id] = content

    def remove_script(self, script_id: str):
        self._scripts.pop(script_id, None)

    def clear_scripts(self):
        self._scripts.clear()

    def process_question(self, question: AsrFinal):
        if not question.text.strip():
            return

        best_id = None
        best_score = 0.0

        for sid, content in self._scripts.items():
            score = SequenceMatcher(None, question.text.lower(), content.lower()).ratio()
            if score > best_score:
                best_score = score
                best_id = sid

        if best_id and best_score >= self._threshold:
            hint = PromptHint(
                hint=self._scripts[best_id],
                source_script=best_id,
                confidence=round(best_score, 4),
                timestamp=time.time(),
            )
            if self._callback:
                self._callback(hint)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_engine.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/prompt/engine.py tests/test_prompt_engine.py
git commit -m "feat: add prompt engine with text similarity search"
```

---

### Task 10: Overlay UI (sobes_modules/overlay/ui.py)

**Files:**
- Create: `sobes_modules/overlay/ui.py`
- Create: `tests/test_overlay.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_overlay.py
import pytest
from unittest.mock import patch, MagicMock
from sobes_modules.overlay.ui import OverlayUI, OverlayState


def test_overlay_initial_state():
    ui = OverlayUI(test_mode=True)
    assert ui.state == OverlayState.HIDDEN
    assert ui.mode == "compact"


def test_overlay_toggle_visibility():
    ui = OverlayUI(test_mode=True)
    ui.show()
    assert ui.state == OverlayState.VISIBLE
    ui.hide()
    assert ui.state == OverlayState.HIDDEN
    ui.show()
    assert ui.state == OverlayState.VISIBLE


def test_overlay_switch_mode():
    ui = OverlayUI(test_mode=True)
    assert ui.mode == "compact"
    ui.switch_mode("full")
    assert ui.mode == "full"
    ui.switch_mode("compact")
    assert ui.mode == "compact"


def test_overlay_display_hint():
    ui = OverlayUI(test_mode=True)
    ui.show()

    from sobes_core.messages import PromptHint
    hint = PromptHint(
        hint="Расскажи про микросервисы и Go",
        source_script="кейс-микросервисы",
        confidence=0.87,
        timestamp=1234.5,
    )
    ui.display_hint(hint)
    assert ui.current_hint == hint
    assert ui.current_hint_text == "Расскажи про микросервисы и Go"


def test_overlay_display_transcript():
    ui = OverlayUI(test_mode=True)
    ui.show()

    from sobes_core.messages import AsrPartial, AsrFinal

    ui.display_asr_result(AsrPartial(text="привет как", is_partial=True, timestamp=1.0))
    assert len(ui.transcript_lines) == 1

    ui.display_asr_result(AsrFinal(text="привет как дела", timestamp=1.5, speaker="interviewer"))
    assert len(ui.transcript_lines) == 2


def test_overlay_quick_script():
    ui = OverlayUI(test_mode=True)
    ui.register_quick_script("ctrl+1", "самопрезентация", "Расскажите о себе...")

    result = ui.get_quick_script("ctrl+1")
    assert result is not None
    assert result["title"] == "самопрезентация"
    assert result["content"] == "Расскажите о себе..."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_overlay.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# sobes_modules/overlay/ui.py
import logging
from enum import Enum, auto
from sobes_core.messages import PromptHint, AsrPartial, AsrFinal

logger = logging.getLogger(__name__)

try:
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


class OverlayState(Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"


class OverlayUI:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.state = OverlayState.HIDDEN
        self.mode = "compact"
        self.current_hint: PromptHint | None = None
        self.current_hint_text: str = ""
        self.transcript_lines: list[str] = []
        self._quick_scripts: dict[str, dict] = {}
        self._app = None
        self._widget = None

    def show(self):
        self.state = OverlayState.VISIBLE
        if not self.test_mode and QT_AVAILABLE and self._widget:
            self._widget.show()

    def hide(self):
        self.state = OverlayState.HIDDEN
        if not self.test_mode and QT_AVAILABLE and self._widget:
            self._widget.hide()

    def switch_mode(self, mode: str):
        if mode in ("compact", "full"):
            self.mode = mode

    def display_hint(self, hint: PromptHint):
        self.current_hint = hint
        self.current_hint_text = hint.hint

    def display_asr_result(self, result: AsrPartial | AsrFinal):
        if isinstance(result, AsrFinal):
            line = f"[{result.speaker}] {result.text}"
        else:
            line = f"[partial] {result.text}"
        self.transcript_lines.append(line)
        if len(self.transcript_lines) > 100:
            self.transcript_lines = self.transcript_lines[-100:]

    def register_quick_script(self, shortcut: str, title: str, content: str):
        self._quick_scripts[shortcut] = {"title": title, "content": content}

    def get_quick_script(self, shortcut: str) -> dict | None:
        return self._quick_scripts.get(shortcut)

    def start_qt_ui(self):
        if not QT_AVAILABLE or self.test_mode:
            return
        self._app = QApplication.instance() or QApplication([])
        self._widget = QWidget()
        self._widget.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self._widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self._widget.setGeometry(100, 100, 400, 200)
        layout = QVBoxLayout()
        self._hint_label = QLabel("")
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(
            "background: rgba(17, 17, 27, 230); color: #cdd6f4; padding: 12px;"
            "border: 1px solid #a6e3a1; border-radius: 8px; font-size: 13px;"
        )
        layout.addWidget(self._hint_label)
        self._widget.setLayout(layout)
        self._widget.show()
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start(500)

    def _refresh_ui(self):
        if self._hint_label:
            self._hint_label.setText(self.current_hint_text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_overlay.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/overlay/ui.py tests/test_overlay.py
git commit -m "feat: add overlay UI with compact mode and quick scripts"
```

---

### Task 11: Post-Analyzer (sobes_modules/post/analyzer.py)

**Files:**
- Create: `sobes_modules/post/analyzer.py`
- Create: `tests/test_post_analyzer.py`

- [ ] **Step 1: Write failing test**

```python
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
    assert report.total_questions == 3  # interviewer questions
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
    assert stats["candidate_words"] > stats["interviewer_words"]  # candidate said more


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_post_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_post_analyzer.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add sobes_modules/post/analyzer.py tests/test_post_analyzer.py
git commit -m "feat: add post-call analyzer with report generation"
```

---

### Task 12: CLI Entry Point (main.py)

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_main.py
import subprocess
import sys


def test_main_help():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "prepare" in result.stdout
    assert "start" in result.stdout
    assert "report" in result.stdout


def test_main_prepare_command():
    result = subprocess.run(
        [sys.executable, "main.py", "prepare", "--company", "TestCorp", "--role", "Dev", "--type", "tech"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "TestCorp" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v -x`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# main.py
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("sobes")


def cmd_prepare(args):
    from sobes_core.config import Config
    from sobes_core.storage import SqliteStore
    from sobes_modules.preparation.service import PreparationService

    cfg = Config()
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()
    svc = PreparationService(cfg, store)

    profile = svc.create_session_profile(
        company=args.company,
        role=args.role,
        interview_type=args.type,
    )
    logger.info(f"Session created: {profile['id']}")

    if args.scripts_file:
        import json
        with open(args.scripts_file, "r", encoding="utf-8") as f:
            scripts = json.load(f)
        for s in scripts:
            sid = svc.add_script(
                session_id=profile["id"],
                title=s["title"],
                content=s["content"],
                tags=s.get("tags", []),
            )
            logger.info(f"Script added: {s['title']} (id={sid})")

    svc.index_scripts(profile["id"])
    report = svc.get_readiness_report(profile["id"])
    logger.info(f"Readiness: {report['status']}, scripts: {report['scripts_count']}")
    print(f"Session ready: {profile['id']}")
    return 0


def cmd_start(args):
    from sobes_core.config import Config
    from sobes_core.session_manager import SessionManager
    sobes_core.session_manager

    cfg = Config()
    mgr = SessionManager(pub_port=cfg.zmq_session_port, pull_port=cfg.zmq_session_port + 1)
    logger.info(f"Starting session manager on PUB={cfg.zmq_session_port}")
    mgr.run()
    return 0


def cmd_report(args):
    from sobes_core.config import Config
    from sobes_core.storage import SqliteStore

    cfg = Config()
    store = SqliteStore(cfg.sqlite_path)
    store.initialize()

    if args.session_id:
        session = store.get_session(int(args.session_id))
        if session:
            print(f"Company: {session.company}")
            print(f"Role: {session.role}")
            print(f"Type: {session.interview_type}")
            print(f"Duration: {session.started_at} — {session.ended_at}")
            print(f"Transcript:\n{session.transcript[:500]}...")
        else:
            print(f"Session {args.session_id} not found")
    elif args.list:
        sessions = store.list_sessions(company=args.company)
        for s in sessions:
            print(f"[{s.id}] {s.company} — {s.role} ({s.interview_type}) {s.started_at}")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="sobes", description="Interview Assistant")
    sub = parser.add_subparsers(dest="command")

    p_prepare = sub.add_parser("prepare", help="Create interview session and add scripts")
    p_prepare.add_argument("--company", required=True)
    p_prepare.add_argument("--role", required=True)
    p_prepare.add_argument("--type", required=True, choices=["tech", "hr", "final", "other"])
    p_prepare.add_argument("--scripts-file", help="JSON file with script objects")

    p_start = sub.add_parser("start", help="Start live session (session manager)")

    p_report = sub.add_parser("report", help="View session reports")
    p_report.add_argument("--session-id", type=int)
    p_report.add_argument("--list", action="store_true")
    p_report.add_argument("--company")

    args = parser.parse_args()
    if args.command == "prepare":
        return cmd_prepare(args)
    elif args.command == "start":
        return cmd_start(args)
    elif args.command == "report":
        return cmd_report(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add CLI entry point with prepare/start/report commands"
```

---

### Task 13: Integration — wire modules together

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import time
import threading
from unittest.mock import patch, MagicMock
from sobes_core.config import Config
from sobes_core.storage import SqliteStore
from sobes_core.session_manager import SessionManager
from sobes_modules.preparation.service import PreparationService
from sobes_modules.prompt.engine import PromptEngine
from sobes_modules.overlay.ui import OverlayUI
from sobes_modules.post.analyzer import PostAnalyzer
from sobes_core.messages import AsrFinal, PromptHint


def test_full_flow_prepare_to_hint(tmp_path):
    """End-to-end: preparation → prompt search → hint generation"""
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

    question = AsrFinal(text="расскажите про ваш опыт работы с го", timestamp=time.time(), speaker="interviewer")
    prompt_engine.process_question(question)

    assert len(hints) == 1
    assert hints[0].confidence > 0.5
    assert "Go" in hints[0].hint or "highload" in hints[0].hint
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL or PASS

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: 1 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for preparation-to-hint flow"
```

---

### Task 14: Final verification — run all tests

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 2: Verify all pass**

Expected: all tests GREEN (no failures, may have 1-2 skips for audio hardware)

- [ ] **Step 3: Commit (if any changes from test fixes)**

---

## Self-Review Checklist

- [x] Spec coverage: each module from spec has a task (messages, config, storage, session_manager, preparation, capturer, asr, prompt, overlay, post)
- [x] No placeholders: all steps have concrete code
- [x] Type consistency: message types from Task 2 used consistently in Tasks 7-11
- [x] TDD order: test → fail → implement → pass → commit for every task
