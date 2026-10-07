"""Verbinding met een Tuya-warmtepomp, lokaal (LAN) of via de Tuya-cloud."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import tinytuya

from .config import Config


class HeatPumpError(RuntimeError):
    pass


@dataclass
class Status:
    power: bool | None
    target_temp: float | None
    current_temp: float | None
    mode: str | None
    fault: Any
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "power": self.power,
            "target_temp": self.target_temp,
            "current_temp": self.current_temp,
            "mode": self.mode,
            "fault": self.fault,
        }


class HeatPump:
    """Leest en stuurt de warmtepomp aan. Kiest lokaal als dat kan, anders cloud."""

    def __init__(self, config: Config, prefer: str = "auto"):
        self.config = config
        if prefer == "local" or (prefer == "auto" and config.has_local):
            if not config.has_local:
                raise HeatPumpError("Lokale verbinding vereist device_id, ip en local_key.")
            self.mode = "local"
            self._dev = tinytuya.Device(config.device_id, config.ip, config.local_key, version=config.version)
            self._dev.set_socketTimeout(5)
        elif prefer in ("cloud", "auto") and config.has_cloud:
            self.mode = "cloud"
            self._cloud = tinytuya.Cloud(
                apiRegion=config.api_region,
                apiKey=config.api_key,
                apiSecret=config.api_secret,
                apiDeviceID=config.device_id,
            )
        else:
            raise HeatPumpError(
                "Geen bruikbare verbinding: vul device_id + ip + local_key (lokaal) "
                "of device_id + api_key + api_secret (cloud) in."
            )

    # ---- ruwe datapoints -------------------------------------------------

    def raw_dps(self) -> dict[str, Any]:
        if self.mode == "local":
            result = self._dev.status()
            if not result or "Error" in result:
                raise HeatPumpError(f"Lokale status mislukt: {result}")
            return {str(k): v for k, v in result.get("dps", {}).items()}

        result = self._cloud.getstatus(self.config.device_id)
        if not result or not result.get("success"):
            raise HeatPumpError(f"Cloud-status mislukt: {result}")
        # De cloud geeft 'codes' (bijv. "switch") i.p.v. DP-nummers; beide zijn bruikbaar in dp_map.
        return {item["code"]: item["value"] for item in result.get("result", [])}

    def set_dp(self, key: str, value: Any) -> None:
        if self.mode == "local":
            result = self._dev.set_value(int(key) if key.isdigit() else key, value)
            if result and "Error" in result:
                raise HeatPumpError(f"Instellen mislukt: {result}")
            return

        result = self._cloud.sendcommand(self.config.device_id, {"commands": [{"code": key, "value": value}]})
        if not result or not result.get("success"):
            raise HeatPumpError(f"Cloud-commando mislukt: {result}")

    # ---- handige functies ------------------------------------------------

    def _temp_in(self, value: Any) -> float | None:
        if value is None:
            return None
        return round(float(value) / self.config.temp_scale, 1)

    def status(self) -> Status:
        dps = self.raw_dps()
        m = self.config.dp_map
        power = dps.get(m["power"])
        return Status(
            power=bool(power) if power is not None else None,
            target_temp=self._temp_in(dps.get(m["target_temp"])),
            current_temp=self._temp_in(dps.get(m["current_temp"])),
            mode=dps.get(m["mode"]),
            fault=dps.get(m["fault"]),
            raw=dps,
        )

    def set_power(self, on: bool) -> None:
        self.set_dp(self.config.dp_map["power"], bool(on))

    def set_target_temp(self, celsius: float) -> None:
        if not 5 <= celsius <= 60:
            raise HeatPumpError("Doeltemperatuur moet tussen 5 en 60 °C liggen.")
        self.set_dp(self.config.dp_map["target_temp"], int(round(celsius * self.config.temp_scale)))

    def set_mode(self, mode: str) -> None:
        self.set_dp(self.config.dp_map["mode"], mode)
