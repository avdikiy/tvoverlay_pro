"""Base entity for TvOverlay Pro."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator


class TvOverlayEntity(CoordinatorEntity):
    """Base entity."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_name = device_name
        self._client = coordinator.client
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_identifier)},
            name=device_name,
            manufacturer="TvOverlay",
            model="Android TV Overlay",
            sw_version=coordinator.device_version,
        )
