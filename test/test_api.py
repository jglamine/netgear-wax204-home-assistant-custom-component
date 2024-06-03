import pytest

from custom_components.netgear_wax204.api import (
    WAX204Api,
    WAX204ApiInvalidPasswordError,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

HOST = "192.168.1.1"
# TODO: Delete password
PASSWORD = "appleorangepear"

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_wax_router_no_sign_in(hass: HomeAssistant) -> None:
    host = HOST
    wax204_api = WAX204Api(hass, host)

    assert await wax204_api.is_wax_router()

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_not_wax_router(hass: HomeAssistant) -> None:
    host = "192.168.1.2"
    wax204_api = WAX204Api(hass, host)

    assert not await wax204_api.is_wax_router()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_is_wax_router_after_sign_in(hass: HomeAssistant) -> None:

    host = HOST
    wax204_api = WAX204Api(hass, host)

    await wax204_api.sign_in(PASSWORD)
    assert await wax204_api.is_wax_router()

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_in(hass: HomeAssistant) -> None:
    wax204_api = WAX204Api(hass, HOST)
    await wax204_api.sign_in(PASSWORD)

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_in_invalid_password(hass: HomeAssistant) -> None:
    wax204_api = WAX204Api(hass, HOST)
    try:
        await wax204_api.sign_in("worngpassword")
    except WAX204ApiInvalidPasswordError:
        return
    assert False, "Should have raised WAX204ApiInvalidPasswordError on invalid password"

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sign_out_other_users(hass: HomeAssistant) -> None:
    wax204_api = WAX204Api(hass, HOST)
    await wax204_api.sign_out_other_users()

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_get_connected_devices(hass: HomeAssistant) -> None:
    wax204_api = WAX204Api(hass, HOST)
    await wax204_api.sign_in(PASSWORD)
    devices = await wax204_api.get_connected_devices()
    assert len(devices) > 0
    fennels = list(
        filter(lambda device: device.hostname == "FENNEL", devices))
    assert len(fennels) == 1
    fennel = fennels[0]
    assert fennel is not None
    assert fennel.mac == "70:85:C2:98:3C:23"
    assert fennel.ip == "192.168.1.225"
    assert fennel.hostname == "FENNEL"

@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_all_apis_after_sign_in(hass: HomeAssistant) -> None:
    wax204_api = WAX204Api(hass, HOST)
    await wax204_api.sign_in(PASSWORD)
    assert await wax204_api.is_wax_router()
    await wax204_api.sign_out_other_users()
    await wax204_api.get_connected_devices()
