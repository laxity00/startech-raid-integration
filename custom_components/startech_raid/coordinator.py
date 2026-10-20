"""One cached HTTP refresh shared by all RAID and SSD entities."""
from datetime import timedelta
import logging
import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import InvalidAuth
from .const import DOMAIN, UPDATE_SECONDS

_LOGGER = logging.getLogger(__name__)


class StartechCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=UPDATE_SECONDS))
        self.client = client
        self.entry = entry

    async def _async_update_data(self):
        try:
            data = await self.client.status()
            if data["instance_id"] != self.entry.unique_id:
                raise ValueError("App identity changed; restore app data or add the new installation")
            return data
        except InvalidAuth as exc:
            raise ConfigEntryAuthFailed("App token rejected; reconfigure the integration") from exc
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError) as exc:
            raise UpdateFailed("Cannot read valid cached monitor data") from exc
