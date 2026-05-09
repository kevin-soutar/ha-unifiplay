"""Config flow for UniFi Play integration using static device IPs."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_DEVICES, DOMAIN

_LOGGER = logging.getLogger(__name__)

MAC_RE = re.compile(r"^[0-9a-fA-F]{2}([:-]?[0-9a-fA-F]{2}){5}$")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_DEVICES,
            description={"suggested_value": "Living Room,192.168.1.50,AA:BB:CC:DD:EE:FF"},
        ): str,
    }
)


def _normalize_mac(mac: str) -> str:
    """Return MAC address as uppercase colon-separated text."""
    raw = mac.strip().replace(":", "").replace("-", "").upper()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))


def parse_static_devices(value: str) -> list[dict[str, str]]:
    """Parse static devices from lines: name,ip,mac."""
    devices: list[dict[str, str]] = []
    seen_macs: set[str] = set()

    for line_no, line in enumerate(value.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            raise vol.Invalid(f"Line {line_no} must be: name,ip,mac")

        name, ip, mac = parts
        if not name or not ip or not mac:
            raise vol.Invalid(f"Line {line_no} has an empty name, ip, or mac")
        if not MAC_RE.match(mac):
            raise vol.Invalid(f"Line {line_no} has an invalid MAC address")

        mac = _normalize_mac(mac)
        if mac in seen_macs:
            raise vol.Invalid(f"Line {line_no} duplicates MAC {mac}")
        seen_macs.add(mac)

        devices.append(
            {
                "id": mac.replace(":", "").lower(),
                "name": name,
                "deviceName": name,
                "mac": mac,
                "ip": ip,
                "platform": "UniFi Play",
                "firmware": "",
            }
        )

    if not devices:
        raise vol.Invalid("Add at least one device")
    return devices


class UnifiPlayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Play."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                devices = parse_static_devices(user_input[CONF_DEVICES])
            except vol.Invalid:
                errors[CONF_DEVICES] = "invalid_devices"
            except Exception:
                _LOGGER.exception("Unexpected error during config")
                errors["base"] = "unknown"
            else:
                unique_id = ",".join(sorted(device["id"] for device in devices))
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="UniFi Play",
                    data={CONF_DEVICES: devices},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
