"""Config flow for TvOverlay Pro."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TvOverlayApiClient
from .const import CONF_DEVICE_IDENTIFIER, CONF_HOST, CONF_NAME, CONF_PORT, DEFAULT_NAME, DEFAULT_PORT, DOMAIN


def sanitize_identifier(name: str) -> str:
    """Create a valid device identifier from a name."""
    identifier = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
    return identifier or "tvoverlay"


class TvOverlayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            name = user_input.get(CONF_NAME, DEFAULT_NAME)
            device_identifier = user_input.get(CONF_DEVICE_IDENTIFIER, "").strip()
            if not device_identifier:
                device_identifier = sanitize_identifier(name)

            unique_id = f"{host}:{port}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = TvOverlayApiClient(host, port, session)
            if await client.test_connection():
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_NAME: name,
                        CONF_DEVICE_IDENTIFIER: device_identifier,
                    },
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_DEVICE_IDENTIFIER, default=""): str,
            }),
            errors=errors,
        )
