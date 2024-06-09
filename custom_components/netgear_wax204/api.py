from dataclasses import dataclass
import logging
import datetime

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

_LOGGER = logging.getLogger(__name__)


@dataclass
class ConnectedDevice:
    """Connected device data."""

    hostname: str | None
    ip: str
    mac: str


class WAX204Api:
    """WAX204 API wrapper."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        self.host = f"https://{host}"

        # Create our own client session so that we can use a cookie jar with unsafe=True.
        # Why do we need unsafe?
        # By default, aiohttp will not save cookies with the `Secure` attribute set if the
        # server is an ip address instead of a DNS name. But many routers use ip addresses (like 192.168.1.1)
        # The jtw_token has `Secure` set, so without this, it wouldn't be saved on the session.
        self._session = async_create_clientsession(
            hass, verify_ssl=False, cookie_jar=aiohttp.CookieJar(unsafe=True))

    async def is_wax_router(self):
        try:
            async with self._session.get(
                f"{self.host}/day_after_login.html"
            ) as response:
                if response.status != 200:
                    return False
                text = await response.text()
                return "NETGEAR WAX204" in text
        except aiohttp.ClientError as e:
            _LOGGER.warning(
                "Request failed when checking if router is WAX204", exc_info=True
            )
            raise WAX204ApiError("Error checking if router is WAX204") from e

    async def sign_out_other_users(self):
        try:
            async with self._session.get(f"{self.host}/change_user.html") as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        f"Error signing out other users, status code: {
                            response.status}"
                    )
        except aiohttp.ClientError as e:
            raise WAX204ApiError("Error signing out other users") from e

    async def sign_in(self, password):
        data = {
            "submit_flag": "sso_login",
            "localPasswd": password,
            "sso_login_type": "0",
        }

        try:
            async with self._session.post(
                f"{self.host}/sso_login.cgi", data=data
            ) as response:
                response.raise_for_status()
                json_response = await response.json(content_type=None)
                status = json_response.get("status")
                if status == "1":
                    raise WAX204ApiConcurrentUsersError(
                        "Another user is already signed in. Router only supports one user at a time"
                    )
                if status == "2":
                    raise WAX204ApiInvalidPasswordError("Invalid password")
                if status == "3":
                    raise WAX204ApiLoginRateLimitError(
                        "Invalid password.Too many login failures - rate limited")
                if status != "0":
                    raise WAX204ApiLoginError(
                        f"Login failed, router response: {json_response}"
                    )
                jwt = response.cookies.get("jwt_local")
                if jwt is None:
                    raise WAX204ApiLoginError(
                        "Login failed, server didn't return a jwt_local cookie")
        except aiohttp.ClientError as e:
            raise WAX204ApiError("Error signing in") from e

    async def get_connected_devices(self):
        timestamp_ms = int(datetime.datetime.now().timestamp() * 1000)
        try:
            async with self._session.get(f"{self.host}/refresh_dev.htm", params={"ts": timestamp_ms}) as response:
                response.raise_for_status()
                if await self._is_signed_out(response):
                    raise WAX204ApiExpireCookieError(
                        "Auth cookie expired. Sign in again."
                    )
                json_response = await response.json(content_type=None)
                json_devices = json_response.get("devices", [])
                devices = []
                for d in json_devices:
                    devices.append(
                        ConnectedDevice(
                            hostname=d.get("deviceName"),
                            ip=d.get("ip"),
                            mac=d.get("mac"),
                        )
                    )
                return devices
        except aiohttp.ClientError as e:
            raise WAX204ApiError("Error getting connected devices") from e

    async def _is_signed_out(self, response: aiohttp.ClientResponse) -> bool:
        if response.status != 200:
            return False
        text = await response.text()
        return "day_after_login.html" in text and "top.location.href=" in text


class WAX204ApiError(Exception):
    """WAX204 API error."""


class WAX204ApiLoginError(WAX204ApiError):
    pass


class WAX204ApiConcurrentUsersError(WAX204ApiLoginError):
    pass


class WAX204ApiInvalidPasswordError(WAX204ApiError):
    pass


class WAX204ApiLoginRateLimitError(WAX204ApiInvalidPasswordError):
    pass


class WAX204ApiExpireCookieError(WAX204ApiError):
    pass
