# sobes_modules/overlay/ui.py
import logging
from enum import Enum
from sobes_core.messages import PromptHint, AsrPartial, AsrFinal

logger = logging.getLogger(__name__)

try:
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
    from PySide6.QtCore import Qt, QTimer
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
