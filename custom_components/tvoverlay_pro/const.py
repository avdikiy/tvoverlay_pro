"""Constants for TvOverlay Pro integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "tvoverlay_pro"

# Config
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_NAME: Final = "name"
CONF_DEVICE_IDENTIFIER: Final = "device_identifier"

DEFAULT_PORT = 5001
DEFAULT_NAME = "TvOverlay"

# API endpoints
ENDPOINT_NOTIFY: Final = "/notify"
ENDPOINT_NOTIFY_FIXED: Final = "/notify_fixed"
ENDPOINT_GET: Final = "/get"
ENDPOINT_SET_OVERLAY: Final = "/set/overlay"
ENDPOINT_SET_NOTIFICATIONS: Final = "/set/notifications"
ENDPOINT_SET_SETTINGS: Final = "/set/settings"
ENDPOINT_RESTART_SERVICE: Final = "/set/restart_service"

# Service names
SERVICE_NOTIFY: Final = "notify"
SERVICE_NOTIFY_FIXED: Final = "notify_fixed"
SERVICE_CLEAR_FIXED: Final = "clear_fixed"
SERVICE_RESTART: Final = "restart_service"
SERVICE_STOP_ALL: Final = "stop_all"
SERVICE_START_VIDEO: Final = "start_video"

# Notification attributes
ATTR_ID: Final = "id"
ATTR_TITLE: Final = "title"
ATTR_MESSAGE: Final = "message"
ATTR_SOURCE: Final = "source"
ATTR_DURATION: Final = "duration"
ATTR_MEDIA_TYPE: Final = "media_type"
ATTR_MEDIA_URL: Final = "media_url"
ATTR_IMAGE: Final = "image"
ATTR_VIDEO: Final = "video"
ATTR_CORNER: Final = "corner"
ATTR_SMALL_ICON: Final = "small_icon"
ATTR_SMALL_ICON_COLOR: Final = "small_icon_color"
ATTR_LARGE_ICON: Final = "large_icon"

# Fixed notification attributes
ATTR_VISIBLE: Final = "visible"
ATTR_ICON: Final = "icon"
ATTR_MESSAGE_COLOR: Final = "message_color"
ATTR_ICON_COLOR: Final = "icon_color"
ATTR_BORDER_COLOR: Final = "border_color"
ATTR_BACKGROUND_COLOR: Final = "background_color"
ATTR_BACKGROUND_OPACITY: Final = "background_opacity"
ATTR_SHAPE: Final = "shape"
ATTR_EXPIRATION: Final = "expiration"

# Targeting
ATTR_DEVICE_ID: Final = "device_id"
ATTR_TARGET: Final = "target"
ATTR_HOST: Final = "host"

# Platforms
PLATFORMS: Final = [
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "switch",
]
