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


def test_serialize_unknown_type_raises():
    class NotAMessage:
        pass
    with pytest.raises(ValueError, match="Unknown message class"):
        serialize(NotAMessage())
