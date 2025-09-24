"""Tests for Garmin client behaviour"""

from unittest.mock import MagicMock

import pytest


class StubSettings:
    def __init__(self, email=None, password=None, username=None):
        self.garmin_email = email
        self.garmin_password = password
        self.garmin_username = username


def create_client(monkeypatch: pytest.MonkeyPatch):
    from src.garmin import client as client_module

    monkeypatch.setattr(client_module, "get_settings", lambda: StubSettings())

    return client_module.GarminClient()


def test_backoff_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client(monkeypatch)

    # Enter backoff three times to trigger lockout
    client._enter_backoff_period()
    client._enter_backoff_period()
    client._enter_backoff_period()

    assert client._consecutive_failures == 3
    assert client._backoff_until is not None
    assert client._is_in_backoff_period() is True

    client._reset_failure_count()
    assert client._consecutive_failures == 0
    assert client._backoff_until is None


def test_network_connectivity_check(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client(monkeypatch)

    calls = {"count": 0}

    def fake_connection(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("network down")
        return MagicMock()

    monkeypatch.setattr("src.garmin.client.socket.create_connection", fake_connection)

    assert client._check_network_connectivity() is False
    assert client._check_network_connectivity() is True
