from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

from .api import WAX204Api, WAX204ApiError, WAX204ApiInvalidPasswordError
from .const import DOMAIN
from .coordinator import Wax204DataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]
SCAN_INTERVAL = timedelta(seconds=30)
COOKIE_REFRESH_INTERVAL = timedelta(hours=1)

_LOGGER = logging.getLogger(__name__)


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Netgear WAX204 Router from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data.get(CONF_HOST)
    password = entry.data.get(CONF_PASSWORD)
    if host is None:
        _LOGGER.error("Missing host in config entry")
        return False
    if password is None:
        _LOGGER.error("Missing password in config entry")
        return False

    api = WAX204Api(hass, host)

    # Validate the API connection (and authentication)
    try:
        if not await api.is_wax_router():
            _LOGGER.error("Device at %s is not a WAX204 router", host)
            raise ConfigEntryNotReady(
                f"Device at {host} is not a WAX204 router")
        await api.sign_out_other_users()
        await api.sign_in(password)
    except WAX204ApiInvalidPasswordError as e:
        _LOGGER.exception("Invalid password for WAX204 router at %s", host)
        raise ConfigEntryAuthFailed(
            f"Invalid password for WAX204 router at {host}") from e
    except WAX204ApiError as e:
        _LOGGER.exception("Failed to connect to WAX204 router at %s", host)
        raise ConfigEntryNotReady(
            f"Failed to connect to WAX204 router at {host}") from e

    coordinator = Wax204DataUpdateCoordinator(
        hass,
        api=api,
        update_interval=SCAN_INTERVAL,
        cookie_refresh_interval=COOKIE_REFRESH_INTERVAL,
        password=password,
    )

    # Store objects for this platform to access
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "update_listener": entry.add_update_listener(update_listener),
        "coordinator": coordinator,
    }

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        entry_data["update_listener"]()  # Remove the update listener

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
