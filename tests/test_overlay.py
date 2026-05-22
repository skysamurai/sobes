# tests/test_overlay.py
from sobes_modules.overlay.ui import OverlayUI, OverlayState
from sobes_core.messages import PromptHint, AsrPartial, AsrFinal


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
