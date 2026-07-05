"""Silence MideaLAN integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "silence_midea_lan"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_DEVICE_IDS = "device_ids"
CONF_QUIET_WHEN = "quiet_when"
CONF_SILENT_FAN_GUARDS = "silent_fan_guards"

DEFAULT_FAN_MODE = "silent"
SILENT_SWITCH_SUFFIXES = ("prompt_tone", "screen_display")

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_DEVICE_IDS, default=[]): vol.All(
                    cv.ensure_list,
                    [vol.Coerce(int)],
                ),
                vol.Optional(CONF_SILENT_FAN_GUARDS, default=[]): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(CONF_CLIMATE_ENTITY): cv.entity_id,
                                vol.Required(CONF_QUIET_WHEN): vol.All(
                                    cv.ensure_list,
                                    [cv.entity_id],
                                ),
                            },
                            extra=vol.ALLOW_EXTRA,
                        ),
                    ],
                ),
            },
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

SILENCED_AC_DEVICE_IDS: set[int] = set()
_PATCHED = False


def _install_silence_policy(device_ids: set[int]) -> bool:
    """Patch midea-local AC commands so selected devices cannot re-enable sound."""
    global _PATCHED  # noqa: PLW0603
    SILENCED_AC_DEVICE_IDS.clear()
    SILENCED_AC_DEVICE_IDS.update(device_ids)
    if _PATCHED:
        return True

    try:
        from midealocal.devices.ac import DeviceAttributes, MideaACDevice
        from midealocal.devices.ac.message import MessageNewProtocolSet
    except ImportError:
        _LOGGER.warning("midea-local is not available; silence guard is inactive")
        return False

    _PATCHED = True
    original_process_message = MideaACDevice.process_message
    original_make_message_set = MideaACDevice.make_message_set
    original_make_newprotocol_message_set = MideaACDevice.make_newprotocol_message_set
    original_make_subprotocol_message_set = MideaACDevice.make_subprotocol_message_set
    original_set_attribute = MideaACDevice.set_attribute

    def is_silenced_ac(device: Any) -> bool:
        return getattr(device, "device_id", None) in SILENCED_AC_DEVICE_IDS

    def set_silent_attributes(device: Any) -> None:
        attributes = getattr(device, "_attributes", {})
        for attr in (
            DeviceAttributes.prompt_tone,
            DeviceAttributes.screen_display,
            DeviceAttributes.screen_display_alternate,
            DeviceAttributes.sound,
        ):
            if attr in attributes:
                attributes[attr] = False

    def silence_message(message: Any) -> Any:
        if hasattr(message, "prompt_tone"):
            message.prompt_tone = False
        if hasattr(message, "sound"):
            message.sound = False
        if hasattr(message, "screen_display_alternate"):
            message.screen_display_alternate = False
        return message

    def process_message(self: Any, msg: bytes) -> dict[str, Any]:
        status = original_process_message(self, msg)
        if not is_silenced_ac(self):
            return status

        for attr in (
            DeviceAttributes.prompt_tone,
            DeviceAttributes.screen_display_alternate,
            DeviceAttributes.sound,
        ):
            if status.get(attr.value) is True:
                try:
                    message = MessageNewProtocolSet(self._message_protocol_version)
                    setattr(message, attr.value, False)
                    silence_message(message)
                    self.build_send(message)
                except Exception:  # noqa: BLE001
                    _LOGGER.debug(
                        "[%s] Failed to send silent AC correction for %s",
                        self.device_id,
                        attr.value,
                        exc_info=True,
                    )
        return status

    def make_message_set(self: Any) -> Any:
        if is_silenced_ac(self):
            set_silent_attributes(self)
        message = original_make_message_set(self)
        if is_silenced_ac(self):
            silence_message(message)
        return message

    def make_newprotocol_message_set(
        self: Any,
        attr: str,
        value: bool | int | str,
    ) -> Any:
        if is_silenced_ac(self):
            set_silent_attributes(self)
            if attr in (
                DeviceAttributes.prompt_tone,
                DeviceAttributes.screen_display_alternate,
                DeviceAttributes.sound,
            ):
                value = False
        message = original_make_newprotocol_message_set(self, attr, value)
        if is_silenced_ac(self):
            silence_message(message)
        return message

    def make_subprotocol_message_set(self: Any) -> Any:
        if is_silenced_ac(self):
            set_silent_attributes(self)
        message = original_make_subprotocol_message_set(self)
        if is_silenced_ac(self):
            silence_message(message)
        return message

    def set_attribute(self: Any, attr: str, value: bool | int | str) -> None:
        if not is_silenced_ac(self):
            original_set_attribute(self, attr, value)
            return

        if attr == DeviceAttributes.prompt_tone:
            self._attributes[attr] = False
            self.update_all({str(attr): False})
            try:
                message = MessageNewProtocolSet(self._message_protocol_version)
                message.prompt_tone = False
                silence_message(message)
                self.build_send(message)
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "[%s] Failed to send prompt tone correction",
                    self.device_id,
                    exc_info=True,
                )
            return

        if attr == DeviceAttributes.screen_display:
            self._attributes[attr] = False
            self.update_all({str(attr): False})
            return

        if attr in (DeviceAttributes.screen_display_alternate, DeviceAttributes.sound):
            value = False

        set_silent_attributes(self)
        original_set_attribute(self, attr, value)
        set_silent_attributes(self)

    MideaACDevice.process_message = process_message
    MideaACDevice.make_message_set = make_message_set
    MideaACDevice.make_newprotocol_message_set = make_newprotocol_message_set
    MideaACDevice.make_subprotocol_message_set = make_subprotocol_message_set
    MideaACDevice.set_attribute = set_attribute
    _LOGGER.info("Installed Midea silence guard for AC device ids: %s", SILENCED_AC_DEVICE_IDS)
    return True


def _entry_config(entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Return current config entry data with options layered on top."""
    return {**entry.data, **entry.options}


async def _async_setup_guard(hass: HomeAssistant, conf: dict[str, Any]) -> None:
    """Set up command and fan-mode guards."""
    device_ids = set(conf.get(CONF_DEVICE_IDS, []))
    _install_silence_policy(device_ids)

    unload_callbacks = []
    silent_switches = [
        f"switch.{device_id}_{suffix}"
        for device_id in device_ids
        for suffix in SILENT_SWITCH_SUFFIXES
    ]

    async def enforce_silent_switches(*_: Any) -> None:
        for entity_id in silent_switches:
            if not hass.states.is_state(entity_id, "on"):
                continue
            await hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": entity_id},
                blocking=False,
            )

    async def enforce_silent_switches_with_retries() -> None:
        for delay in (0, 5, 15, 30, 60, 120):
            if delay:
                await asyncio.sleep(delay)
            await enforce_silent_switches()

    if silent_switches:
        hass.async_create_task(enforce_silent_switches_with_retries())
        unload_callbacks.append(
            async_track_time_interval(
                hass,
                enforce_silent_switches,
                timedelta(minutes=5),
            )
        )
        unload_callbacks.append(
            async_track_state_change_event(hass, silent_switches, enforce_silent_switches)
        )

    for guard in conf.get(CONF_SILENT_FAN_GUARDS, []):
        climate_entity = guard[CONF_CLIMATE_ENTITY]
        quiet_when = guard[CONF_QUIET_WHEN]

        async def enforce_silent_fan(
            *_: Any,
            climate_entity: str = climate_entity,
            quiet_when: list[str] = quiet_when,
        ) -> None:
            climate_state = hass.states.get(climate_entity)
            if climate_state is None or climate_state.state in ("off", "unavailable", "unknown"):
                return
            if climate_state.attributes.get("fan_mode") == DEFAULT_FAN_MODE:
                return
            if not any(hass.states.is_state(entity_id, "on") for entity_id in quiet_when):
                return
            await hass.services.async_call(
                "climate",
                "set_fan_mode",
                {"entity_id": climate_entity, "fan_mode": DEFAULT_FAN_MODE},
                blocking=False,
            )

        tracked_entities = [climate_entity, *quiet_when]
        hass.async_create_task(enforce_silent_fan())
        unload_callbacks.append(
            async_track_state_change_event(hass, tracked_entities, enforce_silent_fan)
        )

    hass.data.setdefault(DOMAIN, {})["unload_callbacks"] = unload_callbacks


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Silence MideaLAN from YAML import."""
    conf = config.get(DOMAIN)
    if conf:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=conf,
            )
        )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
) -> bool:
    """Set up Silence MideaLAN from a config entry."""
    await _async_setup_guard(hass, _entry_config(entry))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,  # noqa: ARG001
) -> bool:
    """Unload Silence MideaLAN config entry listeners."""
    for unload_callback in hass.data.get(DOMAIN, {}).pop("unload_callbacks", []):
        unload_callback()
    SILENCED_AC_DEVICE_IDS.clear()
    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
