"""Deprecated wrapper for Garmin client. Use src.integrations.garmin.client instead."""

from src.integrations.garmin import client as _garmin_client

GarminClient = _garmin_client.GarminClient
get_settings = _garmin_client.get_settings
socket = _garmin_client.socket

__all__ = ["GarminClient", "get_settings", "socket"]
