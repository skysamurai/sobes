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
    if "type" not in envelope:
        raise ValueError("Missing 'type' in message envelope")
    if "payload" not in envelope:
        raise ValueError("Missing 'payload' in message envelope")
    try:
        msg_type = MessageType(envelope["type"])
    except ValueError:
        raise ValueError(f"Unknown message type: {envelope['type']}")
    payload = envelope["payload"]
    cls = _MESSAGE_CLASSES[msg_type]
    if cls is AudioChunk:
        payload["data"] = base64.b64decode(payload["data"])
    return cls(**payload)
