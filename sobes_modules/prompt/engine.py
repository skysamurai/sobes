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
