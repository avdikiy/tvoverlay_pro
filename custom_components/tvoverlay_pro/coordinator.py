"""DataUpdateCoordinator for TvOverlay Pro."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TvOverlayApiClient, TvOverlayConnectionError

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class TvOverlayCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for TvOverlay."""

    def __init__(
        self,
        hass,
        client: TvOverlayApiClient,
        device_name: str,
        device_identifier: str | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"TvOverlay {device_name}",
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._device_identifier = device_identifier or f"{client.host}:{client.port}"
        self._device_version: str | None = None

    @property
    def device_identifier(self) -> str:
        return self._device_identifier

    @property
    def device_version(self) -> str | None:
        return self._device_version

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            config = await self.client.get_config()
            if config is None:
                raise UpdateFailed("Failed to fetch config")
            result = config.get("result", config)
            status = result.get("status", {})
            if "version" in status:
                self._device_version = str(status["version"])
            return {
                "overlay": result.get("overlay", {}),
                "settings": result.get("settings", {}),
                "notifications": result.get("notifications", {}),
                "status": status,
            }
        except TvOverlayConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
