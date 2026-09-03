"""Switch entities for TvOverlay Pro."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlaySwitchEntityDescription(SwitchEntityDescription):
    api_key: str = ""
    endpoint: str = "notifications"
    data_key: str = ""


SWITCHES: tuple[TvOverlaySwitchEntityDescription, ...] = (
    TvOverlaySwitchEntityDescription(
        key="display_notifications",
        name="Display Notifications",
        icon="mdi:message-badge-outline",
        api_key="displayNotifications",
        endpoint="notifications",
        data_key="displayNotifications",
    ),
    TvOverlaySwitchEntityDescription(
        key="display_clock",
        name="Display Clock",
        icon="mdi:clock-outline",
        api_key="clockOverlayVisibility",
        endpoint="overlay",
        data_key="clockOverlayVisibility",
    ),
    TvOverlaySwitchEntityDescription(
        key="display_fixed_notifications",
        name="Display Fixed Notifications",
        icon="mdi:pin-outline",
        api_key="displayFixedNotifications",
        endpoint="notifications",
        data_key="displayFixedNotifications",
    ),
    TvOverlaySwitchEntityDescription(
        key="pixel_shift",
        name="Pixel Shift",
        icon="mdi:television-shimmer",
        api_key="pixelShift",
        endpoint="settings",
        data_key="pixelShift",
    ),
    TvOverlaySwitchEntityDescription(
        key="debug_mode",
        name="Debug Mode",
        icon="mdi:bug-outline",
        api_key="displayDebug",
        endpoint="settings",
        data_key="displayDebug",
    ),
)


class TvOverlaySwitch(TvOverlayEntity, SwitchEntity):
    """Switch."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: TvOverlaySwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        section = data.get(self.entity_description.endpoint, {})
        val = section.get(self.entity_description.data_key)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val > 0
        return None

    async def async_turn_on(self) -> None:
        await self._set_state(True)

    async def async_turn_off(self) -> None:
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        data = {self.entity_description.api_key: state}
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
        TvOverlaySwitch(coordinator, entry.entry_id, device_name, desc)
        for desc in SWITCHES
    ]
    async_add_entities(entities)
