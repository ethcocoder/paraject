import pytest

from projected_ai_interface.discovery import SERVICE_TYPE, DiscoveryAdvertisement, local_ip


def test_discovery_service_metadata():
    assert SERVICE_TYPE == "_projected-ai._tcp.local."
    assert local_ip()


def test_advertisement_registers_and_stops():
    pytest.importorskip("zeroconf")
    advertisement = DiscoveryAdvertisement(port=18765, name="Test Projected Desktop", address="127.0.0.1")
    advertisement.start()
    assert advertisement._service is not None
    advertisement.stop()
    assert advertisement._service is None
