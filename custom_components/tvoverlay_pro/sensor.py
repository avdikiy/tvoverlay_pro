"""Sensor entities for TvOverlay Pro."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlaySensorEntityDescription(SensorEntityDescription):
    data_path: tuple = ()


SENSORS: tuple[TvOverlaySensorEntityDescription, ...] = (
    TvOverlaySensorEntityDescription(
        key="hostname",
        name="Hostname",
        icon="mdi:dns",
        data_path=("settings", "deviceName"),
    ),
    TvOverlaySensorEntityDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip-network",
        data_path=("settings", "remotePort"),
    ),
    TvOverlaySensorEntityDescription(
        key="active_fixed_notifications",
        name="Active Fixed Notifications",
        icon="mdi:identifier",
        data_path=("notifications", "fixedNotifications"),
    ),
)


class TvOverlaySensor(TvOverlayEntity, SensorEntity):
    """Sensor."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: TvOverlaySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        val = data
        for key in self.entity_description.data_path:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return None
        if val is None:
            return None
        if isinstance(val, list):
            return str(len(val))
        return str(val) if val is not None else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TvOverlayCoordinator = data["coordinator"]
    device_name = data["name"]
    entities = [
        TvOverlaySensor(coordinator, entry.entry_id, device_name, desc)
        for desc in SENSORS
    ]
    async_add_entities(entities)
