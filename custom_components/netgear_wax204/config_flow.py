"""Config flow for Netgear WAX204 Router integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import (
    WAX204Api,
    WAX204ApiConcurrentUsersError,
    WAX204ApiError,
    WAX204ApiInvalidPasswordError,
    WAX204ApiLoginError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.1.1"): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    password = data[CONF_PASSWORD]

    api = WAX204Api(hass, host)

    try:
        if not await api.is_wax_router():
            raise CannotConnect("Not a WAX204 device")
        await api.sign_out_other_users()
        await api.sign_in(password)
    except WAX204ApiInvalidPasswordError as e:
        raise InvalidAuth("Invalid password provided") from e
    except WAX204ApiConcurrentUsersError as e:
        raise InvalidAuth("Another user is already logged in") from e
    except WAX204ApiLoginError as e:
        raise InvalidAuth(f"Login failed: {str(e)}") from e
    except WAX204ApiError as e:
        raise CannotConnect("Failed to connect to WAX204 router") from e

    # If the connection is successful, return a title for the entry.
    return {"title": f"WAX204 Router at {host}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netgear WAX204 Router."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Here you handle the updated user inputs.
            return self.async_create_entry(title="", data=user_input)

        # Set up the form for re-authentication (or other options).
        # This example only includes re-authentication for simplicity.
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_PASSWORD, default=self.config_entry.data.get(
                        CONF_PASSWORD)
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
