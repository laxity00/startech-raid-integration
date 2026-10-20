"""UI setup and reconfiguration for the internal app API."""
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from .api import Client, InvalidAuth
from .const import CONF_TOKEN, DEFAULT_HOST, DEFAULT_PORT, DOMAIN


def schema(defaults):
    return vol.Schema({vol.Required("host", default=defaults.get("host", DEFAULT_HOST)): str,
                       vol.Required("port", default=defaults.get("port", DEFAULT_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                       vol.Required(CONF_TOKEN): selector.TextSelector({"type": "password"})})


class StartechFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def attempt(self, user_input, step):
        errors = {}
        if user_input is not None:
            try:
                client = Client(async_get_clientsession(self.hass), user_input["host"], user_input["port"], user_input[CONF_TOKEN])
                data = await client.status()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ValueError:
                errors["base"] = "invalid_response"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if step == "user":
                    await self.async_set_unique_id(data["instance_id"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="StarTech RAID Monitor", data=user_input)
                entry = self._get_reconfigure_entry() if step == "reconfigure" else self._get_reauth_entry()
                if entry.unique_id != data["instance_id"]:
                    errors["base"] = "identity_changed"
                else:
                    return self.async_update_reload_and_abort(entry, data_updates=user_input)
        entry = self._get_reconfigure_entry() if step == "reconfigure" else self._get_reauth_entry() if step == "reauth_confirm" else None
        return self.async_show_form(step_id=step, data_schema=schema(user_input or (entry.data if entry else {})), errors=errors)

    async def async_step_user(self, user_input=None):
        return await self.attempt(user_input, "user")

    async def async_step_reconfigure(self, user_input=None):
        return await self.attempt(user_input, "reconfigure")

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self.attempt(user_input, "reauth_confirm")
