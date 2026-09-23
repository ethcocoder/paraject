"""Local-network discovery advertisement for the desktop receiver."""
from __future__ import annotations

import socket
from dataclasses import dataclass

SERVICE_TYPE = "_projected-ai._tcp.local."


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


@dataclass
class DiscoveryAdvertisement:
    """Advertise a desktop frame receiver using mDNS/DNS-SD."""

    port: int = 8765
    name: str = "Projected AI Desktop"
    address: str | None = None
    _zeroconf: object | None = None
    _service: object | None = None

    def start(self) -> None:
        try:
            from zeroconf import ServiceInfo, Zeroconf
        except ImportError as exc:
            raise RuntimeError("Discovery requires zeroconf; install with `pip install -e '.[discovery]'`") from exc
        address = self.address or local_ip()
        self._zeroconf = Zeroconf()
        self._service = ServiceInfo(
            SERVICE_TYPE,
            f"{self.name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(address)],
            port=self.port,
            properties={"transport": "websocket", "path": "/frames", "version": "1"},
        )
        self._zeroconf.register_service(self._service)

    def stop(self) -> None:
        if self._zeroconf is not None and self._service is not None:
            self._zeroconf.unregister_service(self._service)
            self._zeroconf.close()
        self._zeroconf = None
        self._service = None
