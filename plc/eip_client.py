import contextlib
from typing import Any, Dict, List, Optional

try:
    from pycomm3 import LogixDriver  # preferred EtherNet/IP client
except ImportError:  # pragma: no cover - optional dep
    LogixDriver = None


class EIPClient:
    """Thin wrapper over pycomm3 LogixDriver for basic read/write."""

    def __init__(self, ip: str, slot: int = 0, timeout: float = 1.0):
        self.ip = ip
        self.slot = slot
        self.timeout = timeout
        self._driver: Optional[Any] = None

    def connect(self):
        if LogixDriver is None:
            raise RuntimeError("pycomm3 not installed")
        path = f"{self.ip}/{self.slot}"
        self._driver = LogixDriver(path, timeout=self.timeout)
        self._driver.open()

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

