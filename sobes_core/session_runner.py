# sobes_core/session_runner.py
import logging
import time
import threading
import json
from datetime import datetime

from sobes_core.config import Config
from sobes_core.storage import SqliteStore, InterviewSession
from sobes_core.messages import AsrPartial, AsrFinal, PromptHint
from sobes_modules.audio.capturer import AudioCapturer
from sobes_modules.asr.engine import AsrEngine
from sobes_modules.prompt.engine import PromptEngine
from sobes_modules.overlay.ui import OverlayUI
from sobes_modules.post.analyzer import PostAnalyzer
from sobes_modules.preparation.service import PreparationService

logger = logging.getLogger(__name__)


class SessionRunner:
    def __init__(self, config: Config, store: SqliteStore, prep_service: PreparationService | None = None):
        self.cfg = config
        self.store = store
        self.prep = prep_service or PreparationService(config, store)

        self.capturer = AudioCapturer(config)
        self.asr = AsrEngine(config, model_path=config.vosk_model_path)
        self.prompt = PromptEngine(config)
        self.overlay = OverlayUI(test_mode=False)
        self.analyzer = PostAnalyzer()

        self._running = False
        self._transcript: list[dict] = []
        self._hints_used: list[str] = []
        self._started_at = ""
        self._session_id: str | None = None
        self._company = ""
        self._role = ""
        self._interview_type = ""

        self._status_callback = None

    def set_status_callback(self, cb):
        self._status_callback = cb

    def _emit_status(self, msg: str):
        if self._status_callback:
            self._status_callback(msg)

    def load_session(self, session_id: str):
        profile = self.prep._sessions.get(session_id)
        if not profile:
            logger.error(f"Session profile {session_id} not found in prep service")
            return
        self._session_id = session_id
        self._company = profile.get("company", "")
        self._role = profile.get("role", "")
        self._interview_type = profile.get("interview_type", "")

        # Load scripts into prompt engine
        self.prompt.clear_scripts()
        scripts = self.prep.get_session_scripts(session_id)
        for s in scripts:
            self.prompt.add_script(str(s.id), s.content)
        logger.info(f"Loaded {len(scripts)} scripts for session {session_id}")

    def initialize_modules(self):
        self._emit_status("Initializing ASR engine...")
        self.asr.initialize()
        self._emit_status("ASR ready")

        # Wire ASR → Prompt
        def on_asr_result(msg):
            if isinstance(msg, AsrFinal):
                self._transcript.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "speaker": msg.speaker,
                    "text": msg.text,
                })
                self.prompt.process_question(msg)
            elif isinstance(msg, AsrPartial):
                self.overlay.display_asr_result(msg)

        self.asr.set_callback(on_asr_result)

        # Wire Prompt → Overlay
        def on_hint(hint: PromptHint):
            self._hints_used.append(hint.source_script)
            self.overlay.display_hint(hint)
            self._emit_status(f"Hint: {hint.source_script} ({hint.confidence:.0%})")

        self.prompt.set_callback(on_hint)

        # Wire Capturer → ASR
        def on_audio(data: bytes, ts: float):
            self.asr.process_chunk(data, ts)

        self.capturer.set_callback(on_audio)

    def start(self):
        if self._running:
            return
        self._running = True
        self._started_at = datetime.now().isoformat()
        self._transcript = []
        self._hints_used = []

        self._emit_status("Starting audio capture...")
        self.capturer.start()

        self.overlay.show()
        self.overlay.start_qt_ui()

        self._emit_status("Session running")

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.capturer.stop()
        self.overlay.hide()
        self._emit_status("Session stopped")
        self._save_report()

    def is_running(self) -> bool:
        return self._running

    def _save_report(self):
        ended_at = datetime.now().isoformat()
        report = self.analyzer.generate_report(
            transcript=self._transcript,
            company=self._company,
            role=self._role,
            interview_type=self._interview_type,
            started_at=self._started_at,
            ended_at=ended_at,
        )
        report.stats["scripts_used"] = len(set(self._hints_used))

        session = InterviewSession(
            id=None,
            company=self._company,
            role=self._role,
            interview_type=self._interview_type,
            started_at=self._started_at,
            ended_at=ended_at,
            transcript=report.transcript,
            stats=json.dumps(report.stats, ensure_ascii=False),
        )
        self.store.save_session(session)
        logger.info(f"Report saved for {self._company} — {self._role}")
        self._emit_status(f"Report saved: {report.stats['total_questions']} questions, "
                          f"{report.stats['total_words']} words, "
                          f"{report.stats['scripts_used']} hints used")
