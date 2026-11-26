import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERVICE_NAME


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            SmartIRProRemote(
                entry.entry_id,
                entry.data[CONF_NAME],
                entry.data[CONF_SERVICE_NAME],
            )
        ]
    )


class SmartIRProRemote(RemoteEntity):
    def __init__(self, entry_id: str, name: str, esphome_service: str) -> None:
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_remote"
        self._attr_is_on = True
        self._esphome_service = esphome_service

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        for _ in range(repeats):
            for cmd in command:
                clean_code = cmd[4:] if cmd.startswith("b64:") else cmd
                await self.hass.services.async_call(
                    "esphome",
                    self._esphome_service,
                    {"code": clean_code},
                    blocking=True,
                )
                if delay > 0:
                    await asyncio.sleep(delay)
