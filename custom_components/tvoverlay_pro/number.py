"""Number entities for TvOverlay Pro."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlayNumberEntityDescription(NumberEntityDescription):
    api_key: str = ""
    endpoint: str = "notifications"
    data_key: str = ""
    multiply: float = 1.0


NUMBERS: tuple[TvOverlayNumberEntityDescription, ...] = (
    TvOverlayNumberEntityDescription(
        key="clock_visibility",
        name="Clock Visibility",
        icon="mdi:clock-outline",
        api_key="clockOverlayVisibility",
        endpoint="overlay",
        data_key="clockOverlayVisibility",
        min_value=0,
        max_value=95,
        step=1,
        mode=NumberMode.SLIDER,
        unit_of_measurement="%",
    ),
    TvOverlayNumberEntityDescription(
        key="overlay_visibility",
        name="Overlay Visibility",
        icon="mdi:opacity",
        api_key="overlayVisibility",
        endpoint="overlay",
        data_key="overlayVisibility",
        min_value=0,
        max_value=95,
        step=1,
        mode=NumberMode.SLIDER,
        unit_of_measurement="%",
    ),
    TvOverlayNumberEntityDescription(
        key="fixed_notifications_visibility",
        name="Fixed Notifications Visibility",
        icon="mdi:pin-outline",
        api_key="fixedNotificationsVisibility",
        endpoint="notifications",
        data_key="fixedNotificationsVisibility",
        min_value=-1,
        max_value=95,
        step=1,
        mode=NumberMode.SLIDER,
        unit_of_measurement="%",
    ),
    TvOverlayNumberEntityDescription(
        key="notification_duration",
        name="Notification Duration",
        icon="mdi:timer-outline",
        api_key="notificationDuration",
        endpoint="notifications",
        data_key="notificationDuration",
        min_value=1,
        max_value=300,
        step=1,
        mode=NumberMode.SLIDER,
        unit_of_measurement="s",
    ),
)


class TvOverlayNumber(TvOverlayEntity, NumberEntity):
    """Number."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: TvOverlayNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        section = data.get(self.entity_description.endpoint, {})
        val = section.get(self.entity_description.data_key)
        if val is not None:
            return float(val)
        return None

    async def async_set_native_value(self, value: float) -> None:
        data = {self.entity_description.api_key: int(value)}
        if self.entity_description.endpoint == "notifications":
            success = await self._client.set_notifications(data)
        elif self.entity_description.endpoint == "overlay":
            success = await self._client.set_overlay(data)
        else:
            success = await self._client.set_settings(data)
        if success:
            await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TvOverlayCoordinator = data["coordinator"]
    device_name = data["name"]
    entities = [
        TvOverlayNumber(coordinator, entry.entry_id, device_name, desc)
        for desc in NUMBERS
    ]
    async_add_entities(entities)
