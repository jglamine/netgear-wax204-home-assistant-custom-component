
from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.netgear_wax204.api import ConnectedDevice

from .const import DOMAIN
from .coordinator import Wax204DataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: Wax204DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    seen_macs = set()

    @callback
    def on_coordinator_update() -> None:
        if not coordinator.data:
            return

        new_entities = []
        for mac, device in coordinator.data.devices.items():
            if mac not in seen_macs:
                new_entities.append(
                    NetgearWax204DeviceEntity(coordinator, device))
                seen_macs.add(mac)

        async_add_entities(new_entities)

    entry.async_on_unload(
        coordinator.async_add_listener(on_coordinator_update))


class NetgearWax204DeviceEntity(CoordinatorEntity, ScannerEntity):

    def __init__(self, coordinator: Wax204DataUpdateCoordinator, device: ConnectedDevice) -> None:
        super().__init__(coordinator)
        self._device = device
        self._coordinator = coordinator

    @property
    def name(self) -> str:
        return self._device.hostname

    @property
    def unique_id(self) -> str:
        return self._device.mac

    @property
    def ip_address(self) -> str:
        return self._device.ip

    @property
    def mac_address(self) -> str:
        return self._device.mac

    @property
    def hostname(self) -> str:
        return self._device.hostname

    @property
    def source_type(self) -> SourceType:
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        return self._coordinator.is_active(self._device.mac)
