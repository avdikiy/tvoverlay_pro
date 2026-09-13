"""HTTP API client for TvOverlay."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import (
    ENDPOINT_GET,
    ENDPOINT_NOTIFY,
    ENDPOINT_NOTIFY_FIXED,
    ENDPOINT_RESTART_SERVICE,
    ENDPOINT_SET_NOTIFICATIONS,
    ENDPOINT_SET_OVERLAY,
    ENDPOINT_SET_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class TvOverlayConnectionError(Exception):
    """Connection error."""


class TvOverlayApiClient:
    """TvOverlay HTTP API client."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._session = session

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    async def _make_request(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> tuple[bool, dict[str, Any] | None]:
        url = f"{self._base_url}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
        try:
            if self._session is None or self._session.closed:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    return await self._execute_request(session, method, url, data)
            else:
                return await self._execute_request(self._session, method, url, data)
        except aiohttp.ClientConnectorError as err:
            _LOGGER.error("Connection error to %s: %s", url, err)
            raise TvOverlayConnectionError(f"Cannot connect to {url}") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error to %s: %s", url, err)
            raise TvOverlayConnectionError(f"Client error: {err}") from err
        except TimeoutError as err:
            _LOGGER.error("Timeout connecting to %s: %s", url, err)
            raise TvOverlayConnectionError(f"Timeout connecting to {url}") from err

    async def _execute_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        data: dict | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        if method == "GET":
            async with session.get(url) as response:
                return await self._handle_response(response)
        else:
            async with session.post(url, json=data or {}) as response:
                return await self._handle_response(response)

    async def _handle_response(
        self, response: aiohttp.ClientResponse
    ) -> tuple[bool, dict[str, Any] | None]:
        if response.status >= 400:
            _LOGGER.error("HTTP error %s from %s", response.status, response.url)
            return False, None
        try:
            result = await response.json()
            success = result.get("success", False)
            return success, result
        except aiohttp.ContentTypeError:
            return False, None

    async def test_connection(self) -> bool:
        """Test connection by sending empty POST /notify."""
        try:
            success, _ = await self._make_request("POST", ENDPOINT_NOTIFY, {})
            return success
        except TvOverlayConnectionError:
            return False

    async def get_config(self) -> dict[str, Any] | None:
        """GET /get — fetch all settings."""
        success, result = await self._make_request("GET", ENDPOINT_GET)
        if success:
            return result
        return None

    async def send_notification(self, data: dict) -> bool:
        """POST /notify — send a notification."""
        success, _ = await self._make_request("POST", ENDPOINT_NOTIFY, data)
        return success

    async def send_fixed_notification(self, data: dict) -> bool:
        """POST /notify_fixed — send a fixed notification."""
        success, _ = await self._make_request("POST", ENDPOINT_NOTIFY_FIXED, data)
        return success

    async def clear_fixed_notification(self, notification_id: str) -> bool:
        """POST /notify_fixed with visible=false — clear a fixed notification."""
        success, _ = await self._make_request(
            "POST",
            ENDPOINT_NOTIFY_FIXED,
            {"id": notification_id, "visible": False},
        )
        return success

    async def restart_service(self) -> bool:
        """POST /set/restart_service — restart the overlay service."""
        success, _ = await self._make_request("POST", ENDPOINT_RESTART_SERVICE, {})
        return success

    async def wait_for_api(self, timeout: float = 15.0, interval: float = 1.0) -> bool:
        """Poll GET /get until the API responds.

        Used after restart_service: the overlay service restarts and may
        briefly be unavailable. Returns True once responsive, False on timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                success, _ = await self._make_request("GET", ENDPOINT_GET)
                if success:
                    return True
            except TvOverlayConnectionError:
                pass
            await asyncio.sleep(interval)
        return False

    async def set_notifications(self, data: dict) -> bool:
        """POST /set/notifications — set notification settings."""
        success, _ = await self._make_request("POST", ENDPOINT_SET_NOTIFICATIONS, data)
        return success

    async def set_overlay(self, data: dict) -> bool:
        """POST /set/overlay — set overlay settings."""
        success, _ = await self._make_request("POST", ENDPOINT_SET_OVERLAY, data)
        return success

    async def set_settings(self, data: dict) -> bool:
        """POST /set/settings — set device settings."""
        success, _ = await self._make_request("POST", ENDPOINT_SET_SETTINGS, data)
        return success
