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
