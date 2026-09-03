"""Binary sensor entities for TvOverlay Pro."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlayBinarySensorEntityDescription(BinarySensorEntityDescription):
    pass


BINARY_SENSORS: tuple[TvOverlayBinarySensorEntityDescription, ...] = (
    TvOverlayBinarySensorEntityDescription(
        key="connectivity",
        name="Connectivity",
        icon="mdi:connection",
        device_class="connectivity",
    ),
)


class TvOverlayBinarySensor(TvOverlayEntity, BinarySensorEntity):
    """Binary sensor."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: TvOverlayBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return True if coordinator last update succeeded."""
        return bool(self.coordinator.last_update_success)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TvOverlayCoordinator = data["coordinator"]
    device_name = data["name"]
    entities = [
        TvOverlayBinarySensor(coordinator, entry.entry_id, device_name, desc)
        for desc in BINARY_SENSORS
    ]
    async_add_entities(entities)
