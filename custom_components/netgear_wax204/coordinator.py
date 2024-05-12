"""DataUpdateCoordinator for integration_blueprint."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

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
        password: str
    ) -> None:
        """Initialize."""
        self.api = api
        self.password = password
        self.is_paused: bool = False
        self.resume_after: Optional[datetime] = None
        self.refresh_cookie_after: datetime = datetime.now() + cookie_refresh_interval
        self.cookie_refresh_interval = cookie_refresh_interval
        self.pause_interval = timedelta(minutes=10)
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _refresh_login_cookie(self):
        """Sign out other users and sign in again."""
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
            raise UpdateFailed(
                f"Error communicating with API when refreshing login cookie") from e

    async def _async_update_data(self):
        """Update data via API."""
        if self.is_paused:
            if datetime.now() <= self.resume_after:
                LOGGER.info("Updates paused until %s", self.resume_after)
                # Updates are paused, so do nothing until the timer expires
                if self.data is not None:
                    return self.data
                return Wax204DataModel(devices=[])
            else:
                self.is_paused = False
                self.resume_after = None
                await self._refresh_login_cookie()

        if self.refresh_cookie_after < datetime.now():
            await self._refresh_login_cookie()

        try:
            data = await self.api.get_connected_devices()
            LOGGER.debug("Found %s connected devices", len(data))
            return Wax204DataModel(devices=data)
        except WAX204ApiExpireCookieError as e:
            # Login expired. Most likely because another user is logged in.
            # The router can only support one user at a time.
            # We don't want to lock other users out of the router's web UI, so pause updates
            # for a few minutes before forcing the other user to sign out.
            self.is_paused = True
            self.resume_after = datetime.now() + self.pause_interval

            LOGGER.warning("Invalid login cookie. Most likely another user is signed in. Pausing updates until %s",
                           self.resume_after, exc_info=True)

            if self.data is not None:
                return self.data
            return Wax204DataModel(devices=[])


class Wax204DataModel:
    def __init__(
            self,
            devices: list[ConnectedDevice]
    ) -> None:
        self.devices = {}
        for d in devices:
            self.devices[d.mac] = d
