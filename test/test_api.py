import pytest
import re

from custom_components.netgear_wax204.api import (
    WAX204Api,
    WAX204ApiInvalidPasswordError,
)
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_wax_router_no_sign_in(hass: HomeAssistant, router_host) -> None:
    wax204_api = WAX204Api(hass, router_host)

    assert await wax204_api.is_wax_router()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_not_wax_router(hass: HomeAssistant) -> None:
    host = "example.com"
    wax204_api = WAX204Api(hass, host)

    assert not await wax204_api.is_wax_router()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_wax_router_after_sign_in(hass: HomeAssistant, router_host, router_password) -> None:
    wax204_api = WAX204Api(hass, router_host)

    await wax204_api.sign_in(router_password)
    assert await wax204_api.is_wax_router()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_in(hass: HomeAssistant, router_host, router_password) -> None:
    wax204_api = WAX204Api(hass, router_host)
    await wax204_api.sign_in(router_password)


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_in_invalid_password(hass: HomeAssistant, router_host) -> None:
    wax204_api = WAX204Api(hass, router_host)
    try:
        await wax204_api.sign_in("worngpassword")
    except WAX204ApiInvalidPasswordError:
        return
    assert False, "Should have raised WAX204ApiInvalidPasswordError on invalid password"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_out_other_users(hass: HomeAssistant, router_host) -> None:
    wax204_api = WAX204Api(hass, router_host)
    await wax204_api.sign_out_other_users()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_get_connected_devices(hass: HomeAssistant, router_host, router_password) -> None:
    ipv4_pattern = re.compile(r'^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$')
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
    hostname_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')

    wax204_api = WAX204Api(hass, router_host)
    await wax204_api.sign_in(router_password)
    devices = await wax204_api.get_connected_devices()
    assert len(devices) > 0
    for device in devices:
        assert ipv4_pattern.match(device.ip)
        assert mac_pattern.match(device.mac)
        assert hostname_pattern.match(device.hostname)


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_all_apis_after_sign_in(hass: HomeAssistant, router_host, router_password) -> None:
    wax204_api = WAX204Api(hass, router_host)
    await wax204_api.sign_in(router_password)
    assert await wax204_api.is_wax_router()
    await wax204_api.sign_out_other_users()
    await wax204_api.get_connected_devices()
