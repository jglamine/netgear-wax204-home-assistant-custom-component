"""DataUpdateCoordinator for integration_blueprint."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    ConnectedDevice,
    WAX204Api,
    WAX204ApiError,
    WAX204ApiLoginError,
    WAX204ApiConcurrentUsersError,
    WAX204ApiInvalidPasswordError,
    WAX204ApiExpireCookieError
)
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class Wax204DataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: WAX204Api,
        update_interval: timedelta,
        cookie_refresh_interval: timedelta,
        consider_home: timedelta,
        password: str
    ) -> None:
        """Initialize."""
        self.api = api
        self.password = password
        self.is_paused: bool = False
        self.resume_after: datetime | None = None
        self.refresh_cookie_after: datetime = datetime.now() + cookie_refresh_interval
        self.cookie_refresh_interval = cookie_refresh_interval
        self.pause_interval = timedelta(minutes=10)
        self._consider_home = consider_home
        self._last_seen: dict[str, datetime] = {}
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    def is_active(self, mac: str) -> bool:
        last_seen = self._last_seen.get(mac)
        if last_seen is None:
            return False

        time_since_last_seen = datetime.now() - last_seen
        return time_since_last_seen <= self._consider_home

    def _update_last_seen(self, devices: list[ConnectedDevice]):
        now = datetime.now()
        for d in devices:
            self._last_seen[d.mac] = now

    async def _refresh_login_cookie(self):
        """Sign out other users and sign in again."""
        LOGGER.info("Refreshing login cookie")
        try:
            LOGGER.info("Signing out other users")
            await self.api.sign_out_other_users()
            LOGGER.info("Signing in again")
            await self.api.sign_in(password=self.password)
            self.refresh_cookie_after = datetime.now() + self.cookie_refresh_interval
            LOGGER.info("Sign in succeeded")
        except WAX204ApiConcurrentUsersError as e:
            self.is_paused = True
            self.resume_after = datetime.now() + self.pause_interval
            LOGGER.exception(
                "Another user is already logged in and signing them out didn't work")
            raise UpdateFailed(
                "Another user is already logged in and signing them out didn't work") from e
        except WAX204ApiInvalidPasswordError as e:
            raise ConfigEntryAuthFailed("Invalid password") from e
        except WAX204ApiLoginError as e:
            raise ConfigEntryAuthFailed(f"Login failed: {e}") from e
        except WAX204ApiError as e:
            raise e

    def _cached_data(self):
        if self.data is None:
            return Wax204DataModel(devices=[])
        return self.data

    async def _async_update_data(self):
        """Update data via API."""
        try:
            if self.is_paused:
                if datetime.now() <= self.resume_after:
                    LOGGER.info("Updates paused until %s", self.resume_after)
                    # Updates are paused, so do nothing until the timer expires
                    # But update the last_seen of the cached data so that we don't
                    # mark them as away
                    if self.data is not None:
                        self._update_last_seen(self.data.devices)
                    return self._cached_data()
                else:
                    self.is_paused = False
                    self.resume_after = None
                    await self._refresh_login_cookie()

            if self.refresh_cookie_after < datetime.now():
                await self._refresh_login_cookie()

            try:
                data = await self.api.get_connected_devices()
                LOGGER.debug("Found %s connected devices", len(data))
                self._update_last_seen(data)
                return Wax204DataModel(devices=data)
            except WAX204ApiExpireCookieError:
                # Login expired. Most likely because another user is logged in.
                # The router can only support one user at a time.
                # We don't want to lock other users out of the router's web UI, so pause updates
                # for a few minutes before forcing the other user to sign out.
                self.is_paused = True
                self.resume_after = datetime.now() + self.pause_interval

                LOGGER.warning("Invalid login cookie. Most likely another user is signed in. Pausing updates until %s",
                               self.resume_after, exc_info=True)

                return self._cached_data()
        except WAX204ApiError:
            LOGGER.exception("Error fetching connected devices. Using cached data instead")
            return self._cached_data()


class Wax204DataModel:
    def __init__(
            self,
            devices: list[ConnectedDevice]
    ) -> None:
        self.devices = {}
        for d in devices:
            self.devices[d.mac] = d
