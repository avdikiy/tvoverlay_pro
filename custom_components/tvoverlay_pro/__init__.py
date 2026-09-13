"""TvOverlay Pro integration — fixed seconds field + restart_service."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TvOverlayApiClient, TvOverlayConnectionError
from .config_flow import sanitize_identifier
from .const import (
    ATTR_BACKGROUND_COLOR,
    ATTR_BACKGROUND_OPACITY,
    ATTR_BORDER_COLOR,
    ATTR_CORNER,
    ATTR_DEVICE_ID,
    ATTR_DURATION,
    ATTR_EXPIRATION,
    ATTR_HOST,
    ATTR_ICON,
    ATTR_ICON_COLOR,
    ATTR_ID,
    ATTR_IMAGE,
    ATTR_LARGE_ICON,
    ATTR_MEDIA_TYPE,
    ATTR_MEDIA_URL,
    ATTR_MESSAGE,
    ATTR_MESSAGE_COLOR,
    ATTR_SHAPE,
    ATTR_SMALL_ICON,
    ATTR_SMALL_ICON_COLOR,
    ATTR_SOURCE,
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_VIDEO,
    ATTR_VISIBLE,
    CONF_DEVICE_IDENTIFIER,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_FIXED,
    SERVICE_NOTIFY,
    SERVICE_NOTIFY_FIXED,
    SERVICE_RESTART,
    SERVICE_START_VIDEO,
    SERVICE_STOP_ALL,
)

_LOGGER = logging.getLogger(__name__)

# --- go2rtc stream warmer -------------------------------------------------
# The TV player (media3 RtspClient) hangs forever ("loading") when it
# attaches to a COLD go2rtc producer; attaching to an already-producing
# stream works reliably. A held-open consumer keeps the producer alive
# until the TV's own consumer attaches (~seconds after notify).
GO2RTC_RTSP_PORT = 8554
GO2RTC_API_PORT = 1984
GO2RTC_WARMER_HOLD = 12  # seconds to keep the warmer attached after the stream is producing
GO2RTC_WARMER_SOCK_READ = 30  # per-read timeout while waiting for stream data

_GO2RTC_RTSP_RE = re.compile(r"^rtsp://([^/:@]+):(\d+)/([^/?#]+)")


def _go2rtc_warmer_url(video_url: str) -> str | None:
    """Return the go2rtc warmer URL for a go2rtc RTSP video URL, else None.

    Only matches plain rtsp://host:8554/<stream> URLs (go2rtc RTSP source).
    Direct camera URLs (credentials, other ports) are not warmed.
    """
    match = _GO2RTC_RTSP_RE.match(video_url or "")
    if not match:
        return None
    host, port, stream_name = match.groups()
    if int(port) != GO2RTC_RTSP_PORT:
        return None
    return f"http://{host}:{GO2RTC_API_PORT}/api/stream.mp4?src={stream_name}"


async def _go2rtc_warmer_task(
    hass: HomeAssistant, warmer_url: str, ready: asyncio.Event
) -> None:
    """Hold a consumer open on a go2rtc stream until the TV has attached.

    1. GET /api/stream.mp4?src=<name> — attaches a consumer; the producer
       (re)starts.
    2. Wait for the first bytes — the producer is now producing; set ready.
    3. Keep draining the response for GO2RTC_WARMER_HOLD seconds so the
       consumer is not flagged as stalled; the TV attaches within seconds
       after notify and its own consumer keeps the producer alive.
    4. Close — the warmer detaches, the TV consumer alone sustains the stream.
    """
    session = async_get_clientsession(hass)
    response: aiohttp.ClientResponse | None = None
    try:
        try:
            response = await session.get(
                warmer_url,
                timeout=aiohttp.ClientTimeout(
                    total=None, connect=5, sock_read=GO2RTC_WARMER_SOCK_READ
                ),
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("go2rtc warmer: connect failed (%s): %s", warmer_url, err)
            return
        if response.status != 200:
            _LOGGER.warning("go2rtc warmer: HTTP %s from %s", response.status, warmer_url)
            return
        try:
            first = await response.content.readany()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("go2rtc warmer: no stream data (%s): %s", warmer_url, err)
            return
        if not first:
            _LOGGER.warning("go2rtc warmer: closed without data: %s", warmer_url)
            return
        _LOGGER.info("go2rtc warmer: stream is producing (%s)", warmer_url)
        ready.set()
        deadline = time.monotonic() + GO2RTC_WARMER_HOLD
        try:
            while time.monotonic() < deadline:
                chunk = await response.content.read(65536)
                if not chunk:
                    break
        except (aiohttp.ClientError, asyncio.TimeoutError):
            _LOGGER.debug("go2rtc warmer: stream ended during hold")
    finally:
        if response is not None:
            response.close()
        _LOGGER.debug("go2rtc warmer: detached")


def _build_notification_data(data: dict, defaults: dict | None = None) -> dict:
    """Build notification payload for POST /notify.

    KEY FIX: sends "seconds" field (not "duration") to TvOverlay API.
    """
    payload: dict[str, Any] = {}

    simple_fields = {
        ATTR_ID: "id",
        ATTR_TITLE: "title",
        ATTR_MESSAGE: "message",
        ATTR_SOURCE: "source",
        ATTR_DURATION: "seconds",  # FIX: "seconds" not "duration"
    }
    for attr, api_key in simple_fields.items():
        val = data.get(attr)
        if val is not None:
            payload[api_key] = val

    # Media handling
    media_type = data.get(ATTR_MEDIA_TYPE)
    media_url = data.get(ATTR_MEDIA_URL)

    if media_type == "video" and media_url:
        payload["video"] = media_url
    elif media_type == "image" and media_url:
        payload["image"] = media_url
    elif media_url:
        # Auto-detect from URL
        if media_url.startswith("rtsp://") or media_url.endswith(".m3u8") or media_url.endswith(".mpd"):
            payload["video"] = media_url
        else:
            payload["image"] = media_url

    # Direct video/image fields
    if ATTR_VIDEO in data and data[ATTR_VIDEO]:
        payload["video"] = data[ATTR_VIDEO]
    if ATTR_IMAGE in data and data[ATTR_IMAGE]:
        payload["image"] = data[ATTR_IMAGE]

    # Optional fields
    optional_fields = {
        ATTR_CORNER: "corner",
        ATTR_SMALL_ICON: "smallIcon",
        ATTR_SMALL_ICON_COLOR: "smallIconColor",
        ATTR_LARGE_ICON: "largeIcon",
    }
    for attr, api_key in optional_fields.items():
        val = data.get(attr)
        if val is not None:
            payload[api_key] = val

    # Apply defaults
    if defaults:
        for key, val in defaults.items():
            if key not in payload:
                payload[key] = val

    return payload


def _build_fixed_notification_data(data: dict) -> dict:
    """Build fixed notification payload for POST /notify_fixed."""
    payload: dict[str, Any] = {}

    simple_fields = {
        ATTR_ID: "id",
        ATTR_MESSAGE: "message",
        ATTR_ICON: "icon",
        ATTR_MESSAGE_COLOR: "messageColor",
        ATTR_ICON_COLOR: "iconColor",
        ATTR_BORDER_COLOR: "borderColor",
        ATTR_BACKGROUND_COLOR: "backgroundColor",
        ATTR_SHAPE: "shape",
        ATTR_EXPIRATION: "expiration",
    }
    for attr, api_key in simple_fields.items():
        val = data.get(attr)
        if val is not None:
            payload[api_key] = val

    if ATTR_VISIBLE in data:
        payload["visible"] = data[ATTR_VISIBLE]

    if ATTR_BACKGROUND_OPACITY in data and data[ATTR_BACKGROUND_OPACITY] is not None:
        opacity = data[ATTR_BACKGROUND_OPACITY]
        if isinstance(opacity, (int, float)) and 0 <= opacity <= 100:
            bg = payload.get("backgroundColor", "#000000")
            # Convert opacity to hex alpha
            alpha = int(opacity * 2.55)
            if not bg.startswith("#") or len(bg) == 7:
                payload["backgroundColor"] = f"#{alpha:02x}{bg.lstrip('#')}"
            elif len(bg) == 9:
                payload["backgroundColor"] = f"#{alpha:02x}{bg[3:]}"

    return payload


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration — register services."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_identifier = entry.data.get(CONF_DEVICE_IDENTIFIER, sanitize_identifier(name))

    session = async_get_clientsession(hass)
    client = TvOverlayApiClient(host, port, session)

    from .coordinator import TvOverlayCoordinator

    coordinator = TvOverlayCoordinator(hass, client, name, device_identifier)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "name": name,
        "host": host,
        "port": port,
        "device_identifier": device_identifier,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register all services."""

    def _get_client(call: ServiceCall) -> TvOverlayApiClient | None:
        """Resolve client from device_id, target, or host."""
        data = call.data
        entry_id = None

        if ATTR_DEVICE_ID in data:
            dev_reg = dr.async_get(hass)
            device = dev_reg.async_get_device({(DOMAIN, data[ATTR_DEVICE_ID])})
            if device:
                for config_entry_id in device.config_entries:
                    entry = hass.config_entries.async_get_entry(config_entry_id)
                    if entry and entry.domain == DOMAIN:
                        entry_id = entry.entry_id
                        break

        if entry_id is None and ATTR_TARGET in data:
            target = data[ATTR_TARGET]
            for eid, edata in hass.data.get(DOMAIN, {}).items():
                if edata.get("device_identifier") == target:
                    entry_id = eid
                    break

        if entry_id is None and ATTR_HOST in data:
            host_str = data[ATTR_HOST]
            if ":" in host_str:
                h, p = host_str.rsplit(":", 1)
            else:
                h, p = host_str, str(DEFAULT_PORT)
            session = async_get_clientsession(hass)
            return TvOverlayApiClient(h, int(p), session)

        if entry_id and entry_id in hass.data.get(DOMAIN, {}):
            return hass.data[DOMAIN][entry_id]["client"]

        _LOGGER.warning("No TvOverlay device found for service call data: %s", dict(data))
        return None

    async def handle_notify(call: ServiceCall) -> None:
        """Send notification."""
        client = _get_client(call)
        if client is None:
            return
        payload = _build_notification_data(call.data)
        _LOGGER.debug("Notify payload: %s", payload)
        try:
            await client.send_notification(payload)
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to send notification: %s", err)

    async def handle_notify_fixed(call: ServiceCall) -> None:
        """Send fixed notification."""
        client = _get_client(call)
        if client is None:
            return
        payload = _build_fixed_notification_data(call.data)
        _LOGGER.debug("Fixed notify payload: %s", payload)
        try:
            await client.send_fixed_notification(payload)
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to send fixed notification: %s", err)

    async def handle_clear_fixed(call: ServiceCall) -> None:
        """Clear fixed notification."""
        client = _get_client(call)
        if client is None:
            return
        notification_id = call.data.get(ATTR_ID)
        if not notification_id:
            _LOGGER.error("clear_fixed requires 'id' field")
            return
        try:
            await client.clear_fixed_notification(notification_id)
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to clear fixed notification: %s", err)

    async def handle_restart(call: ServiceCall) -> None:
        """Restart TvOverlay service — stops all video/notifications."""
        client = _get_client(call)
        if client is None:
            return
        _LOGGER.info("Restarting TvOverlay service at %s:%s", client.host, client.port)
        try:
            await client.restart_service()
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to restart service: %s", err)

    async def handle_stop_all(call: ServiceCall) -> None:
        """Stop all video and notifications — full OFF sequence.

        1. restart_service (stops video)
        2. set displayNotifications: false, displayFixedNotifications: false (hides text/icon)
        No sleep — delays handled by automation if needed.
        """
        client = _get_client(call)
        if client is None:
            return
        _LOGGER.info("Stop all at %s:%s", client.host, client.port)
        try:
            await client.restart_service()
            await client.set_notifications({
                "displayNotifications": False,
                "displayFixedNotifications": False,
            })
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to stop all: %s", err)

    async def handle_start_video(call: ServiceCall) -> None:
        """Start video — full ON sequence.

        1. restart_service — clears the current notification and player
           state. REQUIRED: TvOverlay does not re-initialize the video
           player on same-id notification updates, so without this,
           switching cameras while PiP is active shows the old stream.
        2. wait for API to come back after restart
        3. set displayNotifications: true, displayFixedNotifications: true
        4. wait 1s
        5. send notification with video (becomes current → player starts)

        go2rtc streams are warmed in parallel: the TV player hangs forever
        on a cold go2rtc producer, so a held-open consumer is attached
        before notify and detached after the TV's own consumer attaches.
        """
        client = _get_client(call)
        if client is None:
            return
        _LOGGER.info("Start video at %s:%s", client.host, client.port)
        payload = _build_notification_data(call.data)
        warmer_task: asyncio.Task | None = None
        ready: asyncio.Event = asyncio.Event()
        warmer_url = _go2rtc_warmer_url(payload.get("video", ""))
        if warmer_url is not None:
            warmer_task = hass.async_create_task(
                _go2rtc_warmer_task(hass, warmer_url, ready)
            )
        try:
            await client.restart_service()
            await asyncio.sleep(3)
            if not await client.wait_for_api(timeout=15):
                _LOGGER.warning(
                    "TvOverlay API at %s:%s not responsive after restart, "
                    "trying to continue",
                    client.host,
                    client.port,
                )
            await client.set_notifications({
                "displayNotifications": True,
                "displayFixedNotifications": True,
            })
            await asyncio.sleep(1)
            if warmer_task is not None:
                try:
                    await asyncio.wait_for(
                        ready.wait(), timeout=GO2RTC_WARMER_SOCK_READ + 5
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        "go2rtc warmer not ready in time, notifying TV anyway"
                    )
            _LOGGER.debug("Start video payload: %s", payload)
            await client.send_notification(payload)
        except TvOverlayConnectionError as err:
            _LOGGER.error("Failed to start video: %s", err)

    hass.services.async_register(DOMAIN, SERVICE_NOTIFY, handle_notify)
    hass.services.async_register(DOMAIN, SERVICE_NOTIFY_FIXED, handle_notify_fixed)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_FIXED, handle_clear_fixed)
    hass.services.async_register(DOMAIN, SERVICE_RESTART, handle_restart)
    hass.services.async_register(DOMAIN, SERVICE_STOP_ALL, handle_stop_all)
    hass.services.async_register(DOMAIN, SERVICE_START_VIDEO, handle_start_video)
