import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import CONF_SERVICE_NAME, DOMAIN


class SmartIRProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        all_esphome = self.hass.services.async_services().get("esphome", {})
        b64_services = [srv for srv in all_esphome if srv.endswith("_send_b64")]
        available_services = b64_services if b64_services else list(all_esphome.keys())

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERVICE_NAME])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Pro Пульт"): str,
                vol.Required(CONF_SERVICE_NAME): (
                    vol.In(available_services) if available_services else str
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
