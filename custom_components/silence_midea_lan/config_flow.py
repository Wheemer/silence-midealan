"""Config flow for Silence MideaLAN."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from . import (
    CONF_CLIMATE_ENTITY,
    CONF_DEVICE_IDS,
    CONF_QUIET_WHEN,
    CONF_SILENT_FAN_GUARDS,
    DOMAIN,
)

DEFAULT_DEVICE_IDS: list[int] = []
DEFAULT_QUIET_WHEN: list[str] = []


def _device_ids_to_text(device_ids: list[int] | None) -> str:
    return ", ".join(str(device_id) for device_id in (device_ids or DEFAULT_DEVICE_IDS))


def _device_ids_from_input(value: Any) -> list[int]:
    if isinstance(value, list):
        values = value
    else:
        values = str(value).replace(",", " ").split()
    return [int(device_id) for device_id in values]


def _guard_from_config(data: dict[str, Any]) -> tuple[str, list[str]]:
    guards = data.get(CONF_SILENT_FAN_GUARDS) or []
    if not guards:
        return "", DEFAULT_QUIET_WHEN
    guard = guards[0]
    return guard.get(CONF_CLIMATE_ENTITY, ""), list(
        guard.get(CONF_QUIET_WHEN, DEFAULT_QUIET_WHEN)
    )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_DEVICE_IDS: _device_ids_from_input(user_input[CONF_DEVICE_IDS]),
        CONF_SILENT_FAN_GUARDS: [
            {
                CONF_CLIMATE_ENTITY: user_input[CONF_CLIMATE_ENTITY],
                CONF_QUIET_WHEN: list(user_input[CONF_QUIET_WHEN]),
            }
        ],
    }


def _normalize_import_config(import_config: dict[str, Any]) -> dict[str, Any]:
    climate_entity, quiet_when = _guard_from_config(import_config)
    return {
        CONF_DEVICE_IDS: list(import_config.get(CONF_DEVICE_IDS, DEFAULT_DEVICE_IDS)),
        CONF_SILENT_FAN_GUARDS: [
            {
                CONF_CLIMATE_ENTITY: climate_entity,
                CONF_QUIET_WHEN: quiet_when,
            }
        ],
    }


def _schema(data: dict[str, Any] | None = None) -> vol.Schema:
    data = data or {}
    climate_entity, quiet_when = _guard_from_config(data)
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_DEVICE_IDS,
            default=_device_ids_to_text(data.get(CONF_DEVICE_IDS, DEFAULT_DEVICE_IDS)),
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    }
    climate_key = (
        vol.Required(CONF_CLIMATE_ENTITY, default=climate_entity)
        if climate_entity
        else vol.Required(CONF_CLIMATE_ENTITY)
    )
    fields[climate_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="climate")
    )
    fields[
        vol.Required(CONF_QUIET_WHEN, default=quiet_when)
    ] = selector.EntitySelector(selector.EntitySelectorConfig(multiple=True))
    return vol.Schema(
        fields
    )


class SilenceMideaLANConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Silence MideaLAN."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup flow."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Silence MideaLAN",
                data=_normalize_user_input(user_input),
            )

        return self.async_show_form(step_id="user", data_schema=_schema())

    async def async_step_import(
        self,
        import_config: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Import YAML config into a config entry."""
        import_config = _normalize_import_config(import_config)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured(updates=import_config)
        return self.async_create_entry(title="Silence MideaLAN", data=import_config)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SilenceMideaLANOptionsFlow:
        """Create the options flow."""
        return SilenceMideaLANOptionsFlow(config_entry)


class SilenceMideaLANOptionsFlow(config_entries.OptionsFlow):
    """Handle Silence MideaLAN options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage Silence MideaLAN options."""
        current = {**self._config_entry.data, **self._config_entry.options}
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=_normalize_user_input(user_input),
            )

        return self.async_show_form(step_id="init", data_schema=_schema(current))
