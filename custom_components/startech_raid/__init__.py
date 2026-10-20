"""Private StarTech RAID companion integration."""
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import Client
from .const import CONF_TOKEN
from .coordinator import StartechCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass, entry):
    client = Client(async_get_clientsession(hass), entry.data["host"], entry.data["port"], entry.data[CONF_TOKEN])
    coordinator = StartechCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
