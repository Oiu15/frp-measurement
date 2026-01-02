import contextlib
from typing import Any, Dict, List, Optional

import time
import socket
import threading
from pycomm3 import LogixDriver

from infra.logger import get_logger


def _tcp_probe(host: str, port: int = 44818, timeout: float = 1.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


class EIPClient:
    """Thin wrapper over pycomm3 LogixDriver for basic read/write."""

    def __init__(self, ip: str, slot: int = 0, timeout: float = 1.0):
        self.ip = ip
        self.slot = slot
        self.timeout = timeout
        self._driver: Optional[Any] = None
        self._log = get_logger("plc.service")

    def connect(self):
        path = f"{self.ip}/{self.slot}"
        self._log.debug(
            "Opening connection to PLC at %s (thread=%s)",
            path,
            threading.current_thread().name,
        )

        if not _tcp_probe(self.ip, 44818, timeout=min(1.0, self.timeout)):
            raise TimeoutError(f"TCP probe failed: {self.ip}:44818 unreachable")

        self._driver = LogixDriver(path, timeout=self.timeout)

        t0 = time.time()
        self._log.debug("Driver.open() stat (timeout=%s)", self.timeout)
        try:
            self._driver.open()
            self._log.debug("Drive.open() ok in %.3f sec", time.time() - t0)

            self._driver.read("PLC_CYCLE_CNT")  # test read
            self._log.debug("Handshake read ok in %.3f sec", time.time() - t0)
        except Exception as e:
            self._log.warning(
                "Driver.open/handshake failed in %.3f sec: %s", time.time() - t0, e
            )
            self.close()
            raise

    def close(self):
        with contextlib.suppress(Exception):
            if self._driver:
                self._driver.close()
        self._driver = None

    def ping(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.get_plc_time()
            return True
        except Exception:
            return False

    def read_tags(self, tags: List[str]) -> Dict[str, Any]:
        if not self._driver:
            raise RuntimeError("driver not connected")
        res = self._driver.read(*tags)  # returns list of Response
        return {r.tag: r.value for r in res if not r.error}

    def write_tags(self, writes: Dict[str, Any]):
        if not self._driver:
            raise RuntimeError("driver not connected")
        payload = [(k, v) for k, v in writes.items()]
        self._driver.write(*payload)


class DummyClient(EIPClient):
    """Fallback placeholder when pycomm3 unavailable."""

    def connect(self):
        self._driver = True

    def close(self):
        self._driver = None

    def ping(self) -> bool:
        return True

    def read_tags(self, tags: List[str]) -> Dict[str, Any]:
        return {}

    def write_tags(self, writes: Dict[str, Any]):
        return
