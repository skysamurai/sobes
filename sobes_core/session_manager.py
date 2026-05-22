# sobes_core/session_manager.py
import zmq
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
