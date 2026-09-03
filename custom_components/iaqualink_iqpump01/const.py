DOMAIN = "iaqualink_iqpump01"
OPMODE_SERVICE = "7"
SERVICE_MODE_REMOTE_CONTROL_ERROR = (
    "Remote control not authorized: pump is in service mode."
)

CONF_SERIAL = "serial"
CONF_CUSTOM_SPEED_TIMER_SECONDS = "custom_speed_timer_seconds"
CONF_UPDATE_INTERVAL_SECONDS = "update_interval_seconds"
CONF_FAST_UPDATE_INTERVAL_SECONDS = "fast_update_interval_seconds"
CONF_FAST_REFRESH_DURATION_SECONDS = "fast_refresh_duration_seconds"

DEFAULT_CUSTOM_SPEED_TIMER_SECONDS = 6 * 60 * 60
DEFAULT_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_FAST_UPDATE_INTERVAL_SECONDS = 10
DEFAULT_FAST_REFRESH_DURATION_SECONDS = 3 * 60

CUSTOM_SPEED_TIMER_OPTIONS = {
    30 * 60: "30 min",
    60 * 60: "1 h",
    6 * 60 * 60: "6 h",
    12 * 60 * 60: "12 h",
    (23 * 60 + 59) * 60: "23 h 59",
}
MAX_CUSTOM_SPEED_TIMER_SECONDS = max(CUSTOM_SPEED_TIMER_OPTIONS)

SERVICE_SET_CUSTOM_SPEED = "set_custom_speed"

DEFAULT_RPM_MIN = 1000
DEFAULT_RPM_MAX = 3450


def option_int(options, key, default):
    """Return an integer option while tolerating legacy/string values."""
    try:
        return int(options.get(key, default))
    except (TypeError, ValueError):
        return default


def rpm_limits(data):
    """Return (rpm_min, rpm_max) from device data, with fallback defaults."""
    data = data or {}
    return (
        int(data.get("globalrpmmin", DEFAULT_RPM_MIN)),
        int(data.get("globalrpmmax", DEFAULT_RPM_MAX)),
    )
