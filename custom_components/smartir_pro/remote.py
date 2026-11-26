import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.persistent_notification import async_create
from homeassistant.components.remote import (
    ATTR_COMMAND,
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_NUM_REPEATS,
    ATTR_TIMEOUT,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import Event, HomeAssistant
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

    async def async_learn_command(self, **kwargs: Any) -> None:
        device = kwargs.get(ATTR_DEVICE, "unknown")
        timeout = float(kwargs.get(ATTR_TIMEOUT, 30))
        commands = kwargs.get(ATTR_COMMAND, ["command"])
        if isinstance(commands, str):
            commands = [commands]

        for cmd_name in commands:
            async_create(
                self.hass,
                f"Нажмите кнопку «{cmd_name}» (устройство: {device}) на физическом пульте в течение {int(timeout)} сек...",
                title="SmartIR Pro: Обучение ИК-команде",
                notification_id="smartir_pro_learn",
            )

            future: asyncio.Future[str] = self.hass.loop.create_future()

            def _on_event(event: Event) -> None:
                code = event.data.get("code")
                if code and not future.done():
                    future.set_result(code)

            unsub = self.hass.bus.async_listen("esphome.smartir_pro_learned", _on_event)

            try:
                learned_code = await asyncio.wait_for(future, timeout=timeout)
                async_create(
                    self.hass,
                    f"Команда **{cmd_name}** ({device}) записана:\n\n`b64:{learned_code}`",
                    title="SmartIR Pro: Команда изучена",
                    notification_id=f"smartir_pro_learned_{cmd_name}",
                )
            except TimeoutError:
                async_create(
                    self.hass,
                    f"Время ожидания ({int(timeout)} сек) нажатия кнопки «{cmd_name}» истекло.",
                    title="SmartIR Pro: Таймаут обучения",
                    notification_id="smartir_pro_learn",
                )
            finally:
                unsub()
