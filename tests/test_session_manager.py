# tests/test_session_manager.py
import time
import threading
import zmq
import pytest
from sobes_core.session_manager import SessionManager
from sobes_core.messages import serialize, deserialize, SessionEvent, AsrFinal


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
