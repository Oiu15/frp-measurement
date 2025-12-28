import threading
import time
from queue import Queue, Empty
from typing import Any, Dict, Optional

from infra.logger import get_logger
from .eip_client import EIPClient, DummyClient
from .state_model import PlcState
from . import tag_map, command_service

_POLL_INTERVAL = 0.2


class PlcService:
    """Background PLC service with non-blocking UI access."""

    def __init__(
        self, ip: str, slot: int = 0, timeout: float = 1.0, use_dummy: bool = False
    ):
        self.ip = ip
        self.slot = slot
        self.timeout = timeout
        self._client = DummyClient(ip) if use_dummy else EIPClient(ip, slot, timeout)
        self._cmd_q: Queue[Dict[str, Any]] = Queue()
        self._state = PlcState()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._seq = 1
        self._log = get_logger("plc.service")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="plc-service", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._client.close()

    def enqueue_command(self, cmd_code: int, payload: Dict[str, Any] | None = None):
        seq = self._next_seq()
        cmd = command_service.build_command(cmd_code, seq, payload)
        self._cmd_q.put(cmd)
        return seq

    def get_latest_state(self) -> PlcState:
        return self._state

    def reconfigure(self, ip: str, slot: int = 0, timeout: float = 1.0):
        self.stop()
        self.ip, self.slot, self.timeout = ip, slot, timeout
        self._client = EIPClient(ip, slot, timeout)
        self.start()

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) % 32767 or 1
        return self._seq

    def _loop(self):
        while not self._stop.is_set():
            connected = self._ensure_connection()
            try:
                self._drain_commands(connected)
                raw = self._read_status(connected)
                self._state = PlcState.from_raw(raw, connected=connected)
            except Exception as exc:  # pragma: no cover - background guard
                self._log.exception("PLC loop error: %s", exc)
            time.sleep(_POLL_INTERVAL)

    def _ensure_connection(self) -> bool:
        try:
            if not getattr(self._client, "_driver", None):
                self._client.connect()
            return True
        except Exception as exc:
            self._log.debug("PLC connect failed: %s", exc)
            return False

    def _drain_commands(self, connected: bool):
        if not connected:
            self._clear_queue()
            return
        try:
            cmd = self._cmd_q.get_nowait()
        except Empty:
            return
        try:
            self._client.write_tags(cmd)
        except Exception as exc:
            self._log.warning("PLC write failed: %s", exc)

    def _read_status(self, connected: bool) -> Dict[str, Any]:
        if not connected:
            return {}
        tags = tag_map.status_tags() + tag_map.command_tags()
        try:
            return self._client.read_tags(tags)
        except Exception as exc:
            self._log.warning("PLC read failed: %s", exc)
            return {}

    def _clear_queue(self):
        while True:
            try:
                self._cmd_q.get_nowait()
            except Empty:
                return


_plc_service = None


def get_plc_service(config) -> PlcService:
    global _plc_service
    if _plc_service is None:
        _plc_service = PlcService(
            ip=config.get("plc_ip", "192.168.0.10"),
            slot=0,
            timeout=1.0,
            use_dummy=False,
        )
    return _plc_service
