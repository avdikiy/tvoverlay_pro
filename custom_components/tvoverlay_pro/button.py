"""Button entities for TvOverlay Pro — includes restart service button."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TvOverlayCoordinator
from .entity import TvOverlayEntity

_LOGGER = logging.getLogger(__name__)


BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="restart_service",
        name="Restart Service",
        icon="mdi:restart",
    ),
)


class TvOverlayButton(TvOverlayEntity, ButtonEntity):
    """Button."""

    def __init__(
        self,
        coordinator: TvOverlayCoordinator,
        entry_id: str,
        device_name: str,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, device_name)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    async def async_press(self) -> None:
        """Press the button."""
        if self.entity_description.key == "restart_service":
            _LOGGER.info("Restarting TvOverlay service at %s:%s", self._client.host, self._client.port)
            try:
                await self._client.restart_service()
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to restart service: %s", err)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TvOverlayCoordinator = data["coordinator"]
    device_name = data["name"]
    entities = [
        TvOverlayButton(coordinator, entry.entry_id, device_name, desc)
        for desc in BUTTONS
    ]
    async_add_entities(entities)
