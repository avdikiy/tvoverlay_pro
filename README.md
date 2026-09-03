# TvOverlay Pro

Custom Home Assistant integration for [TvOverlay](https://github.com/gugutab/TvOverlay) Android TV app.

## What's different from the original `tvoverlay_ui` integration?

This is a **fixed and enhanced** fork of `manjotsc/ha-tvoverlay_ui` with three critical fixes:

### 1. Fixed `duration` → `seconds` bug
The original integration sends `duration` field to the TvOverlay API, but the API expects `seconds`. This means duration was **silently ignored** and defaulted to 5 seconds.

**TvOverlay Pro sends `seconds` correctly.**

### 2. Duration max increased to 86400 (24h)
The original integration caps duration at 300 seconds (5 min). For camera PiP overlays you need 86400 seconds (24h).

**TvOverlay Pro allows up to 86400 seconds.**

### 3. Added `restart_service` endpoint
The TvOverlay API has `POST /set/restart_service` which restarts the overlay service and **stops all active video playback**. This is the only reliable way to stop RTSP video streams via HTTP API (no ADB needed).

**TvOverlay Pro exposes this as:**
- Service: `tvoverlay_pro.restart_service`
- Button entity: `button.<device>_restart_service`

## Installation

### Via HACS

1. In HACS → Integrations → ⋮ → Custom repositories
2. Add this repository URL as type **Integration**
3. Search for "TvOverlay Pro" and install
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → "TvOverlay Pro"
6. Enter host (e.g., `100.64.88.46`), port (`5001`), and device name

## Services

### `tvoverlay_pro.notify`
Send a notification with video/image/text.

| Field | Type | Description |
|-------|------|-------------|
| `host` | string | Manual host:port (e.g., `100.64.88.46:5001`) |
| `target` | string | Device identifier (e.g., `living_room_tv`) |
| `device_id` | device | Device from dropdown |
| `id` | string | Notification ID (for updates) |
| `title` | string | Title text |
| `message` | string | Message text |
| `media_type` | select | `none` / `image` / `video` |
| `media_url` | string | RTSP URL, .m3u8, .mpd, or image URL |
| `duration` | number | Seconds (1–86400), default 5 |
| `corner` | select | Screen corner |

### `tvoverlay_pro.restart_service`
Restart the TvOverlay service. **Stops all active video/notifications.**

### `tvoverlay_pro.notify_fixed`
Send a persistent fixed notification.

### `tvoverlay_pro.clear_fixed`
Clear a fixed notification by ID.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `switch.<device>_display_notifications` | switch | Show/hide notifications |
| `switch.<device>_display_clock` | switch | Show/hide clock |
| `switch.<device>_display_fixed_notifications` | switch | Show/hide fixed notifications |
| `switch.<device>_pixel_shift` | switch | Pixel shift |
| `switch.<device>_debug_mode` | switch | Debug mode |
| `button.<device>_restart_service` | button | Restart service (stops video) |
| `number.<device>_clock_visibility` | number | Clock visibility (0-95%) |
| `number.<device>_overlay_visibility` | number | Overlay visibility (0-95%) |
| `number.<device>_fixed_notifications_visibility` | number | Fixed notifications visibility |
| `number.<device>_notification_duration` | number | Default notification duration (1-300s) |
| `select.<device>_hot_corner` | select | Hot corner position |
| `select.<device>_default_shape` | select | Default notification shape |
| `sensor.<device>_hostname` | sensor | Device hostname |
| `sensor.<device>_ip_address` | sensor | Device IP address |
| `sensor.<device>_active_fixed_notifications` | sensor | Active fixed notifications count |
| `binary_sensor.<device>_connectivity` | binary_sensor | Connection status |

## Camera PiP Automation Example

```yaml
# Turn ON camera PiP
- service: tvoverlay_pro.notify
  data:
    host: 100.64.88.46:5001
    id: cam_pip
    media_type: video
    media_url: rtsp://user:pass@192.168.1.100:554
    duration: 86400

# Turn OFF camera PiP (stops video)
- service: tvoverlay_pro.restart_service
  data:
    host: 100.64.88.46:5001
```
