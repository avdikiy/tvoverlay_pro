"""Select entities for TvOverlay Pro."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlaySelectEntityDescription(SelectEntityDescription):
    api_key: str = ""
    endpoint: str = "overlay"
    data_key: str = ""
    options_map: dict = None


HOT_CORNERS = {
    "top_start": "Top Left",
    "top_end": "Top Right",
    "bottom_start": "Bottom Left",
    "bottom_end": "Bottom Right",
}

SHAPES = {
    "circle": "Circle",
    "rounded": "Rounded",
    "rectangular": "Rectangular",
}


SELECTS: tuple[TvOverlaySelectEntityDescription, ...] = (
    TvOverlaySelectEntityDescription(
        key="hot_corner",
        name="Hot Corner",
        icon="mdi:arrow-top-right",
        api_key="hotCorner",
        endpoint="overlay",
        data_key="hotCorner",
        options_map=HOT_CORNERS,
    ),
    TvOverlaySelectEntityDescription(
        key="default_shape",
        name="Default Shape",
        icon="mdi:shape-outline",
        api_key="notificationLayoutName",
        endpoint="notifications",
        data_key="notificationLayoutName",
        options_map=SHAPES,
    ),
)


class TvOverlaySelect(TvOverlayEntity, SelectEntity):
    """Select."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: TvOverlaySelectEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._options_map = description.options_map or {}
        self._attr_options = list(self._options_map.keys())

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        section = data.get(self.entity_description.endpoint, {})
        val = section.get(self.entity_description.data_key)
        if val and val in self._options_map:
            return val
        return None

    async def async_select_option(self, option: str) -> None:
        data = {self.entity_description.api_key: option}
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
        TvOverlaySelect(coordinator, entry.entry_id, device_name, desc)
        for desc in SELECTS
    ]
    async_add_entities(entities)
